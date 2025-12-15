"""Script to initialise the database with basic data.

This script creates the tables, inserts currencies (ARS, USD), a minimal chart
of accounts, operation types and an initial admin user. It should be run once
after the database has been set up. For development purposes a default
password of 'admin' is used (hashed with bcrypt). In production, override
ADMIN_PASSWORD env var to set a secure password.
"""

import os
from getpass import getpass

from sqlalchemy.orm import Session

from app.database import Base, engine, SessionLocal
from app.models.currency import Currency
from app.models.account import Account, AccountType
from app.models.operation_type import OperationType
from app.models.user import User
from app.models.operation import Operation
from app.models.journal_entry import JournalEntry
from app.utils.security import get_password_hash


def init_db(session: Session) -> None:
    """Create tables and insert initial records."""
    Base.metadata.create_all(bind=engine)

    # Insert currencies if not already present
    if not session.query(Currency).count():
        session.add_all([
            Currency(code="ARS", name="Argentine Peso"),
            Currency(code="USD", name="US Dollar"),
        ])
        session.commit()

    # Insert operation types
    if not session.query(OperationType).count():
        operation_types = [
            OperationType(code="FX_BUY", description="Compra de USD"),
            OperationType(code="FX_SELL", description="Venta de USD"),
            OperationType(code="PAYMENT", description="Pago"),
            OperationType(code="RECEIPT", description="Cobro"),
            OperationType(code="CHEQUE_BUY", description="Compra de cheque"),
            OperationType(code="CHEQUE_SELL", description="Venta de cheque"),
        ]
        session.add_all(operation_types)
        session.commit()

    # Insert accounts if not present
    if not session.query(Account).count():
        accounts = [
            Account(code="1010", name="Caja ARS", type=AccountType.ASSET, is_cash=True),
            Account(code="1020", name="Caja USD", type=AccountType.ASSET, is_cash=True),
            Account(code="1030", name="Banco ARS", type=AccountType.ASSET, is_cash=True),
            Account(code="1040", name="Banco USD", type=AccountType.ASSET, is_cash=True),
            Account(code="1100", name="Clientes ARS", type=AccountType.ASSET, is_client_account=True),
            Account(code="1101", name="Clientes USD", type=AccountType.ASSET, is_client_account=True),
            Account(code="2100", name="Proveedores ARS", type=AccountType.LIABILITY),
            Account(code="2101", name="Proveedores USD", type=AccountType.LIABILITY),
            Account(code="1200", name="Cheques por cobrar", type=AccountType.ASSET),
            Account(code="5100", name="Resultado por tipo de cambio", type=AccountType.INCOME, is_fx_result=True),
            Account(code="5200", name="Ingresos por comisiones", type=AccountType.INCOME, is_commission_income=True),
            Account(code="5300", name="Gastos/Comisiones pagadas", type=AccountType.EXPENSE, is_commission_expense=True),
            Account(code="5400", name="Ingresos por intereses", type=AccountType.INCOME),
            Account(code="5500", name="Gastos por intereses", type=AccountType.EXPENSE),
        ]
        session.add_all(accounts)
        session.commit()

    # Insert admin user if not present
    if not session.query(User).filter_by(email="admin@example.com").first():
        password = os.environ.get("ADMIN_PASSWORD") or "admin"
        hashed_pw = get_password_hash(password)
        admin = User(email="admin@example.com", hashed_password=hashed_pw, is_admin=True)
        session.add(admin)
        session.commit()


def main():
    print("Initializing database…")
    with SessionLocal() as session:
        init_db(session)
    print("Database initialized successfully.")


if __name__ == "__main__":
    main()
