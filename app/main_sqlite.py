"""FastAPI application using sqlite3 directly.

This module provides a minimal implementation of the API using raw SQL via
sqlite3. It covers authentication, CRUD for parties, FX operations and a
position report. Tokens are generated in‑memory and are not persistent.
This is a simplified version suitable for local testing in a restricted
environment. In production you should switch to SQLAlchemy and a proper
JWT implementation.
"""

import os
import sqlite3
import hashlib
import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr


DB_FILE = os.environ.get("DB_PATH", "finance.db")

app = FastAPI(title="Finance API (sqlite)")


# In‑memory token store: token -> user email
TOKEN_STORE = {}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db_connection():
    """Provide a new sqlite3 connection for each request."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def authenticate_user(conn: sqlite3.Connection, email: str, password: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT hashed_password FROM users WHERE email = ? AND is_active = 1",
        (email,),
    )
    row = cur.fetchone()
    if not row:
        return False
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return hashed == row["hashed_password"]


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Retrieve the user email associated with the token."""
    email = TOKEN_STORE.get(token)
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return email


# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    email: str
    password: str


class PartyCreate(BaseModel):
    name: str
    type: Optional[str] = "client"
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class PartyOut(BaseModel):
    id: int
    name: str
    type: str
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]


class FXOperationCreate(BaseModel):
    date: datetime
    party_name: str
    fx_type: str  # 'buy' or 'sell'
    usd_amount: float
    exchange_rate: float
    notes: Optional[str] = None


class PositionReport(BaseModel):
    usd_position: float
    ars_balance: float


@app.post("/auth/login", response_model=Token)
def login(data: LoginRequest, db: sqlite3.Connection = Depends(get_db_connection)):
    if not authenticate_user(db, data.email, data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = secrets.token_hex(16)
    TOKEN_STORE[token] = data.email
    return {"access_token": token, "token_type": "bearer"}


@app.post("/parties", response_model=PartyOut)
def create_party(party: PartyCreate, user: str = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db_connection)):
    cur = db.cursor()
    cur.execute(
        "INSERT INTO parties (name, type, email, phone, address, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        (party.name, party.type, party.email, party.phone, party.address),
    )
    db.commit()
    party_id = cur.lastrowid
    return PartyOut(id=party_id, name=party.name, type=party.type, email=party.email, phone=party.phone, address=party.address)


@app.get("/parties", response_model=List[PartyOut])
def list_parties(user: str = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db_connection)):
    cur = db.cursor()
    cur.execute("SELECT id, name, type, email, phone, address FROM parties")
    rows = cur.fetchall()
    return [PartyOut(**row) for row in rows]


def get_id_by_code(conn: sqlite3.Connection, table: str, code: str) -> int:
    cur = conn.cursor()
    cur.execute(f"SELECT id FROM {table} WHERE code = ?", (code,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=400, detail=f"Code {code} not found in {table}")
    return row["id"]


def get_or_create_party(conn: sqlite3.Connection, name: str) -> int:
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute(
        "INSERT INTO parties (name, type, created_at, updated_at) VALUES (?, 'client', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        (name,),
    )
    conn.commit()
    return cur.lastrowid


@app.post("/operations/fx")
def create_fx(op: FXOperationCreate, user: str = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db_connection)):
    # Validate fx_type
    if op.fx_type not in {"buy", "sell"}:
        raise HTTPException(status_code=400, detail="fx_type must be 'buy' or 'sell'")
    cur = db.cursor()
    # Get or create party
    party_id = get_or_create_party(db, op.party_name)
    # Get type id
    op_type_code = "FX_BUY" if op.fx_type == "buy" else "FX_SELL"
    op_type_id = get_id_by_code(db, "operation_types", op_type_code)
    usd_id = get_id_by_code(db, "currencies", "USD")
    ars_id = get_id_by_code(db, "currencies", "ARS")
    # Insert operation
    cur.execute(
        "INSERT INTO operations (date, operation_type_id, party_id, amount, currency_id, exchange_rate, notes, user_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, (SELECT id FROM users WHERE email = ?))",
        (
            op.date.isoformat(),
            op_type_id,
            party_id,
            op.usd_amount,
            usd_id,
            op.exchange_rate,
            op.notes,
            user,
        ),
    )
    operation_id = cur.lastrowid
    # Insert fx_details
    ars_amount = round(op.usd_amount * op.exchange_rate, 2)
    cur.execute(
        "INSERT INTO fx_details (operation_id, usd_amount, ars_amount, fx_type) VALUES (?, ?, ?, ?)",
        (operation_id, op.usd_amount, ars_amount, op.fx_type),
    )
    # Journal entries
    usd_account_id = get_id_by_code(db, "accounts", "1020")
    ars_account_id = get_id_by_code(db, "accounts", "1010")
    if op.fx_type == "buy":
        # Debit USD, credit ARS
        cur.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, ?, 0, ?)",
            (operation_id, usd_account_id, op.usd_amount, usd_id),
        )
        cur.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, 0, ?, ?)",
            (operation_id, ars_account_id, ars_amount, ars_id),
        )
    else:
        # sell: debit ARS, credit USD
        cur.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, ?, 0, ?)",
            (operation_id, ars_account_id, ars_amount, ars_id),
        )
        cur.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, 0, ?, ?)",
            (operation_id, usd_account_id, op.usd_amount, usd_id),
        )
    db.commit()
    return {"operation_id": operation_id}


@app.get("/reports/position", response_model=PositionReport)
def get_position(user: str = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db_connection)):
    cur = db.cursor()
    # USD position
    usd_account_id = get_id_by_code(db, "accounts", "1020")
    cur.execute(
        "SELECT COALESCE(SUM(debit) - SUM(credit), 0) FROM journal_entries WHERE account_id = ? AND currency_id = (SELECT id FROM currencies WHERE code = 'USD')",
        (usd_account_id,),
    )
    usd_position = cur.fetchone()[0]
    # ARS cash balance (cash account only). Could extend to sum across ARS cash/bank.
    ars_account_id = get_id_by_code(db, "accounts", "1010")
    cur.execute(
        "SELECT COALESCE(SUM(debit) - SUM(credit), 0) FROM journal_entries WHERE account_id = ? AND currency_id = (SELECT id FROM currencies WHERE code = 'ARS')",
        (ars_account_id,),
    )
    ars_balance = cur.fetchone()[0]
    return PositionReport(usd_position=usd_position, ars_balance=ars_balance)


class PaymentOperationCreate(BaseModel):
    date: datetime
    party_name: str
    currency: str  # 'ARS' or 'USD'
    gross_amount: float
    commission_amount: Optional[float] = 0
    commission_percentage: Optional[float] = None
    expenses_amount: Optional[float] = 0
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class ReceiptOperationCreate(BaseModel):
    date: datetime
    party_name: str
    currency: str  # 'ARS' or 'USD'
    gross_amount: float
    commission_amount: Optional[float] = 0
    commission_percentage: Optional[float] = None
    expenses_amount: Optional[float] = 0
    payment_method: Optional[str] = None
    notes: Optional[str] = None


@app.post("/operations/payment")
def create_payment(op: PaymentOperationCreate, user: str = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db_connection)):
    # Determine amounts
    commission = op.commission_amount or 0
    if op.commission_percentage:
        commission = round(op.gross_amount * op.commission_percentage / 100, 2)
    expenses = op.expenses_amount or 0
    total_paid = op.gross_amount + commission + expenses
    # Determine currency IDs and accounts
    cur = db.cursor()
    currency_id = get_id_by_code(db, "currencies", op.currency)
    party_id = get_or_create_party(db, op.party_name)
    # Determine party account (suppliers if type is supplier, otherwise clients)
    cur.execute("SELECT type FROM parties WHERE id = ?", (party_id,))
    party_type = cur.fetchone()["type"]
    if party_type == "supplier":
        account_code = "2100" if op.currency == "ARS" else "2101"
    else:
        # paying to a client reduces our asset (accounts receivable) – unusual but allowed
        account_code = "1100" if op.currency == "ARS" else "1101"
    party_account_id = get_id_by_code(db, "accounts", account_code)
    cash_account_code = "1010" if op.currency == "ARS" else "1020"
    cash_account_id = get_id_by_code(db, "accounts", cash_account_code)
    commission_expense_id = get_id_by_code(db, "accounts", "5300")
    # Insert operation header
    op_type_id = get_id_by_code(db, "operation_types", "PAYMENT")
    cur.execute(
        "INSERT INTO operations (date, operation_type_id, party_id, amount, currency_id, exchange_rate, notes, user_id) "
        "VALUES (?, ?, ?, ?, ?, NULL, ?, (SELECT id FROM users WHERE email = ?))",
        (
            op.date.isoformat(),
            op_type_id,
            party_id,
            op.gross_amount,
            currency_id,
            op.notes,
            user,
        ),
    )
    operation_id = cur.lastrowid
    # Insert payment_details
    cur.execute(
        "INSERT INTO payment_details (operation_id, gross_amount, commission_amount, commission_percentage, expenses_amount, payment_method) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            operation_id,
            op.gross_amount,
            commission,
            op.commission_percentage,
            expenses,
            op.payment_method,
        ),
    )
    # Journal entries: debit party account (gross), debit commission expense, debit expenses, credit cash total
    # Debit party account (reduces liability)
    cur.execute(
        "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, ?, 0, ?)",
        (operation_id, party_account_id, op.gross_amount, currency_id),
    )
    if commission > 0:
        cur.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, ?, 0, ?)",
            (operation_id, commission_expense_id, commission, currency_id),
        )
    if expenses > 0:
        # Use same expense account for expenses
        cur.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, ?, 0, ?)",
            (operation_id, commission_expense_id, expenses, currency_id),
        )
    # Credit cash
    cur.execute(
        "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, 0, ?, ?)",
        (operation_id, cash_account_id, total_paid, currency_id),
    )
    db.commit()
    return {"operation_id": operation_id, "total_paid": total_paid}


@app.post("/operations/receipt")
def create_receipt(op: ReceiptOperationCreate, user: str = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db_connection)):
    # Determine amounts
    commission = op.commission_amount or 0
    if op.commission_percentage:
        commission = round(op.gross_amount * op.commission_percentage / 100, 2)
    expenses = op.expenses_amount or 0
    net_received = op.gross_amount - commission - expenses
    if net_received < 0:
        raise HTTPException(status_code=400, detail="Net amount cannot be negative")
    # Determine currency and accounts
    cur = db.cursor()
    currency_id = get_id_by_code(db, "currencies", op.currency)
    party_id = get_or_create_party(db, op.party_name)
    cur.execute("SELECT type FROM parties WHERE id = ?", (party_id,))
    party_type = cur.fetchone()["type"]
    if party_type == "client":
        account_code = "1100" if op.currency == "ARS" else "1101"
    else:
        account_code = "2100" if op.currency == "ARS" else "2101"
    party_account_id = get_id_by_code(db, "accounts", account_code)
    cash_account_code = "1010" if op.currency == "ARS" else "1020"
    cash_account_id = get_id_by_code(db, "accounts", cash_account_code)
    commission_income_id = get_id_by_code(db, "accounts", "5200")
    # Insert operation
    op_type_id = get_id_by_code(db, "operation_types", "RECEIPT")
    cur.execute(
        "INSERT INTO operations (date, operation_type_id, party_id, amount, currency_id, exchange_rate, notes, user_id) "
        "VALUES (?, ?, ?, ?, ?, NULL, ?, (SELECT id FROM users WHERE email = ?))",
        (
            op.date.isoformat(),
            op_type_id,
            party_id,
            op.gross_amount,
            currency_id,
            op.notes,
            user,
        ),
    )
    operation_id = cur.lastrowid
    # Insert receipt_details
    cur.execute(
        "INSERT INTO receipt_details (operation_id, gross_amount, commission_amount, commission_percentage, expenses_amount, payment_method) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            operation_id,
            op.gross_amount,
            commission,
            op.commission_percentage,
            expenses,
            op.payment_method,
        ),
    )
    # Journal entries
    # Credit party account (reduces receivable)
    cur.execute(
        "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, 0, ?, ?)",
        (operation_id, party_account_id, op.gross_amount, currency_id),
    )
    # Debit cash (net received)
    cur.execute(
        "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, ?, 0, ?)",
        (operation_id, cash_account_id, net_received, currency_id),
    )
    # Credit commission income
    if commission > 0:
        cur.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, 0, ?, ?)",
            (operation_id, commission_income_id, commission, currency_id),
        )
    # Expenses in receipt: treat as income (we charge them to client)
    if expenses > 0:
        cur.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, 0, ?, ?)",
            (operation_id, commission_income_id, expenses, currency_id),
        )
    db.commit()
    return {"operation_id": operation_id, "net_received": net_received}


class ChequeBuyOperationCreate(BaseModel):
    date: datetime
    party_name: str
    currency: str  # 'ARS' or 'USD'
    bank: str
    number: str
    nominal_amount: float
    due_date: datetime
    issue_date: Optional[datetime] = None
    expected_accreditation_date: Optional[datetime] = None
    interest_rate: float  # as decimal (e.g., 0.05 for 5%)
    interest_base: int = 365
    commissions_amount: Optional[float] = 0
    expenses_amount: Optional[float] = 0
    notes: Optional[str] = None


@app.post("/operations/cheque_buy")
def create_cheque_buy(op: ChequeBuyOperationCreate, user: str = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db_connection)):
    # Compute time difference in days for interest calculation
    days = (op.due_date.date() - op.date.date()).days
    # Interest amount
    interest_amount = round(op.nominal_amount * op.interest_rate * days / op.interest_base, 2)
    commissions_amount = op.commissions_amount or 0
    expenses_amount = op.expenses_amount or 0
    net_amount = op.nominal_amount - interest_amount - commissions_amount - expenses_amount
    if net_amount < 0:
        raise HTTPException(status_code=400, detail="Net amount cannot be negative")
    cur = db.cursor()
    currency_id = get_id_by_code(db, "currencies", op.currency)
    party_id = get_or_create_party(db, op.party_name)
    # Insert operation header
    op_type_id = get_id_by_code(db, "operation_types", "CHEQUE_BUY")
    cur.execute(
        "INSERT INTO operations (date, operation_type_id, party_id, amount, currency_id, exchange_rate, notes, user_id) "
        "VALUES (?, ?, ?, ?, ?, NULL, ?, (SELECT id FROM users WHERE email = ?))",
        (
            op.date.isoformat(),
            op_type_id,
            party_id,
            op.nominal_amount,
            currency_id,
            op.notes,
            user,
        ),
    )
    operation_id = cur.lastrowid
    # Insert cheque record
    cur.execute(
        "INSERT INTO cheques (operation_id, party_id, bank, number, nominal_amount, issue_date, due_date, expected_accreditation_date, interest_rate, interest_base, expenses, commissions, net_amount, status, currency_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
        (
            operation_id,
            party_id,
            op.bank,
            op.number,
            op.nominal_amount,
            op.issue_date.date().isoformat() if op.issue_date else None,
            op.due_date.date().isoformat(),
            op.expected_accreditation_date.date().isoformat() if op.expected_accreditation_date else None,
            op.interest_rate,
            op.interest_base,
            expenses_amount,
            commissions_amount,
            net_amount,
            currency_id,
        ),
    )
    # Journal entries
    cheque_account_id = get_id_by_code(db, "accounts", "1200")
    cash_account_id = get_id_by_code(db, "accounts", "1010" if op.currency == "ARS" else "1020")
    interest_income_id = get_id_by_code(db, "accounts", "5400")
    commission_income_id = get_id_by_code(db, "accounts", "5200")
    commission_expense_id = get_id_by_code(db, "accounts", "5300")
    # Debit cheque portfolio (asset)
    cur.execute(
        "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, ?, 0, ?)",
        (operation_id, cheque_account_id, op.nominal_amount, currency_id),
    )
    # Credit cash (net amount paid)
    cur.execute(
        "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, 0, ?, ?)",
        (operation_id, cash_account_id, net_amount, currency_id),
    )
    # Credit interest income
    if interest_amount > 0:
        cur.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, 0, ?, ?)",
            (operation_id, interest_income_id, interest_amount, currency_id),
        )
    # Credit commission income
    if commissions_amount > 0:
        cur.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, 0, ?, ?)",
            (operation_id, commission_income_id, commissions_amount, currency_id),
        )
    # Debit expense (if expenses)
    if expenses_amount > 0:
        cur.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) VALUES (?, ?, ?, 0, ?)",
            (operation_id, commission_expense_id, expenses_amount, currency_id),
        )
    db.commit()
    return {
        "operation_id": operation_id,
        "interest_amount": interest_amount,
        "commissions_amount": commissions_amount,
        "expenses_amount": expenses_amount,
        "net_amount": net_amount,
    }


@app.get("/reports/cheques")
def list_cheques(status: Optional[str] = None, db: sqlite3.Connection = Depends(get_db_connection), user: str = Depends(get_current_user)):
    cur = db.cursor()
    query = "SELECT id, bank, number, nominal_amount, due_date, expected_accreditation_date, net_amount, status FROM cheques"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    cur.execute(query, params)
    rows = cur.fetchall()
    return [dict(row) for row in rows]


# Client ledger report
@app.get("/reports/client_ledger")
def client_ledger(party_name: str, start_date: Optional[str] = None, end_date: Optional[str] = None, currency: Optional[str] = None, db: sqlite3.Connection = Depends(get_db_connection), user: str = Depends(get_current_user)):
    """Return ledger for a given client/supplier within a date range.

    - `party_name`: name of the client o proveedor.
    - `start_date` and `end_date`: ISO dates (yyyy-mm-dd) inclusive.
    - `currency`: 'ARS' or 'USD' (optional). If omitted, both currencies are included.
    """
    cur = db.cursor()
    # Find party
    cur.execute("SELECT id, type FROM parties WHERE name = ?", (party_name,))
    party_row = cur.fetchone()
    if not party_row:
        raise HTTPException(status_code=404, detail="Party not found")
    party_id, party_type = party_row
    # Determine account codes
    codes = []
    if currency in (None, '', 'ARS'):
        codes.append('1100' if party_type == 'client' else '2100')
    if currency in (None, '', 'USD'):
        codes.append('1101' if party_type == 'client' else '2101')
    # Build query
    placeholders = ','.join('?' * len(codes))
    query = (
        "SELECT o.date, ot.code as operation_type, o.notes, je.debit, je.credit, c.code AS currency "
        "FROM journal_entries je "
        "JOIN accounts a ON je.account_id = a.id "
        "JOIN operations o ON je.operation_id = o.id "
        "JOIN operation_types ot ON o.operation_type_id = ot.id "
        "JOIN currencies c ON je.currency_id = c.id "
        "WHERE a.code IN (" + placeholders + ") "
        "AND o.party_id = ? "
    )
    params = codes + [party_id]
    if start_date:
        query += " AND date(o.date) >= date(?)"
        params.append(start_date)
    if end_date:
        query += " AND date(o.date) <= date(?)"
        params.append(end_date)
    query += " ORDER BY o.date ASC, je.id ASC"
    cur.execute(query, params)
    rows = cur.fetchall()
    # Build running balance per currency
    ledger = []
    balances = {}
    for row in rows:
        cur_code = row[5]
        balances.setdefault(cur_code, 0)
        amount = (row[3] or 0) - (row[4] or 0)
        balances[cur_code] += amount
        ledger.append({
            'date': row[0],
            'operation_type': row[1],
            'description': row[2],
            'debit': row[3],
            'credit': row[4],
            'currency': cur_code,
            'balance': balances[cur_code]
        })
    return ledger


# Update cheque status
@app.post("/cheques/{cheque_id}/status")
def update_cheque_status(cheque_id: int, new_status: str, db: sqlite3.Connection = Depends(get_db_connection), user: str = Depends(get_current_user)):
    valid_status = {"pending", "accredited", "expired", "rejected", "cancelled"}
    if new_status not in valid_status:
        raise HTTPException(status_code=400, detail="Invalid status")
    cur = db.cursor()
    cur.execute("SELECT id FROM cheques WHERE id = ?", (cheque_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Cheque not found")
    cur.execute("UPDATE cheques SET status = ? WHERE id = ?", (new_status, cheque_id))
    db.commit()
    return {"message": "Status updated"}