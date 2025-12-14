"""Script to insert example FX operations and compute USD position.

This script uses sqlite3 to insert FX buy/sell operations described in the
specification. It creates parties as needed, inserts operations, fx_details and
journal entries, and then prints the resulting USD net position.
"""

import sqlite3
from datetime import datetime


DB_FILE = "finance.db"


def get_id(cursor, table, code_col, code_val):
    cursor.execute(f"SELECT id FROM {table} WHERE {code_col} = ?", (code_val,))
    row = cursor.fetchone()
    if row:
        return row[0]
    raise ValueError(f"Value {code_val} not found in {table}")


def get_party_id(cursor, name):
    cursor.execute("SELECT id FROM parties WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    # insert new party as client
    cursor.execute(
        "INSERT INTO parties (name, type) VALUES (?, 'client')",
        (name,),
    )
    return cursor.lastrowid


def insert_fx_operation(cursor, date_str, party_name, fx_type, usd_amount, exchange_rate):
    """Insert FX buy or sell operation with journal entries."""
    # Retrieve IDs
    op_type_code = "FX_BUY" if fx_type == "buy" else "FX_SELL"
    cursor.execute(
        "SELECT id FROM operation_types WHERE code = ?", (op_type_code,)
    )
    operation_type_id = cursor.fetchone()[0]
    usd_id = get_id(cursor, "currencies", "code", "USD")
    ars_id = get_id(cursor, "currencies", "code", "ARS")
    user_id = 1  # admin
    party_id = get_party_id(cursor, party_name)

    ars_amount = round(usd_amount * exchange_rate, 2)
    # Insert operation header; store amount as USD
    cursor.execute(
        "INSERT INTO operations (date, operation_type_id, party_id, amount, currency_id, "
        "exchange_rate, notes, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            date_str,
            operation_type_id,
            party_id,
            usd_amount,
            usd_id,
            exchange_rate,
            None,
            user_id,
        ),
    )
    operation_id = cursor.lastrowid
    # Insert fx_details
    cursor.execute(
        "INSERT INTO fx_details (operation_id, usd_amount, ars_amount, fx_type) VALUES (?, ?, ?, ?)",
        (operation_id, usd_amount, ars_amount, fx_type),
    )
    # Determine accounts
    usd_account_id = get_id(cursor, "accounts", "code", "1020")  # Caja USD
    ars_account_id = get_id(cursor, "accounts", "code", "1010")  # Caja ARS
    # Insert journal entries
    if fx_type == "buy":
        # Debit USD, credit ARS
        cursor.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) "
            "VALUES (?, ?, ?, 0, ?)",
            (operation_id, usd_account_id, usd_amount, usd_id),
        )
        cursor.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) "
            "VALUES (?, ?, 0, ?, ?)",
            (operation_id, ars_account_id, ars_amount, ars_id),
        )
    else:
        # sell: debit ARS, credit USD
        cursor.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) "
            "VALUES (?, ?, ?, 0, ?)",
            (operation_id, ars_account_id, ars_amount, ars_id),
        )
        cursor.execute(
            "INSERT INTO journal_entries (operation_id, account_id, debit, credit, currency_id) "
            "VALUES (?, ?, 0, ?, ?)",
            (operation_id, usd_account_id, usd_amount, usd_id),
        )


def compute_usd_position(cursor):
    """Compute net USD position: debits minus credits for USD cash account."""
    usd_account_id = get_id(cursor, "accounts", "code", "1020")
    cursor.execute(
        "SELECT SUM(debit) - SUM(credit) FROM journal_entries "
        "WHERE account_id = ? AND currency_id = (SELECT id FROM currencies WHERE code = 'USD')",
        (usd_account_id,),
    )
    result = cursor.fetchone()[0]
    return result or 0


def main():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # FX operations sample: day 1 and day 2
    day1 = "2025-12-01"
    day2 = "2025-12-02"
    # Day 1
    insert_fx_operation(cursor, day1, "magda", "buy", 1923, 1430)
    insert_fx_operation(cursor, day1, "magda", "buy", 1177, 1430)
    insert_fx_operation(cursor, day1, "Plaza", "sell", 2000, 1435)
    insert_fx_operation(cursor, day1, "MP RL", "sell", 1078, 1459)
    insert_fx_operation(cursor, day1, "pili", "sell", 300, 1440)
    insert_fx_operation(cursor, day1, "Plaza", "buy", 400, 1435)
    # Day 2
    insert_fx_operation(cursor, day2, "Plaza", "buy", 1100, 1425)
    insert_fx_operation(cursor, day2, "Rami Cocos", "sell", 1570, 1459)
    insert_fx_operation(cursor, day2, "Clavo MP", "sell", 3000, 1453)
    insert_fx_operation(cursor, day2, "Plaza", "buy", 3000, 1425)

    conn.commit()

    position = compute_usd_position(cursor)
    print(f"Net USD position: {position}")
    if position < 0:
        print(f"Short {abs(position)} USD")
    elif position > 0:
        print(f"Long {position} USD")
    else:
        print("Neutral position")

    conn.close()


if __name__ == "__main__":
    main()