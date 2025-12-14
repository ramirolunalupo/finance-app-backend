"""SQLite initialisation script.

This script creates the database tables defined in `schema.sql` and inserts
initial records for currencies, operation types, accounts and an admin user.
It uses the built‑in `sqlite3` module, so it runs in restricted environments
without external dependencies.

Note: Passwords are hashed with SHA‑256 for simplicity, but in production you
should use a stronger algorithm like bcrypt. The admin email and password can
be overridden via environment variables ADMIN_EMAIL and ADMIN_PASSWORD.
"""

import os
import sqlite3
import hashlib


DB_PATH = os.environ.get("DB_PATH", "finance.db")
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")


def run_schema(cursor):
    with open(SCHEMA_FILE, "r") as f:
        sql = f.read()
    cursor.executescript(sql)


def insert_initial_data(cursor):
    # Insert currencies
    currencies = [("ARS", "Argentine Peso"), ("USD", "US Dollar")]
    cursor.executemany("INSERT OR IGNORE INTO currencies (code, name) VALUES (?, ?)", currencies)

    # Operation types
    op_types = [
        ("FX_BUY", "Compra de USD"),
        ("FX_SELL", "Venta de USD"),
        ("PAYMENT", "Pago"),
        ("RECEIPT", "Cobro"),
        ("CHEQUE_BUY", "Compra de cheque"),
        ("CHEQUE_SELL", "Venta de cheque"),
    ]
    cursor.executemany("INSERT OR IGNORE INTO operation_types (code, description) VALUES (?, ?)", op_types)

    # Accounts
    accounts = [
        ("1010", "Caja ARS", "asset", None, 1, 0, 0, 0, 0),
        ("1020", "Caja USD", "asset", None, 1, 0, 0, 0, 0),
        ("1030", "Banco ARS", "asset", None, 1, 0, 0, 0, 0),
        ("1040", "Banco USD", "asset", None, 1, 0, 0, 0, 0),
        ("1100", "Clientes ARS", "asset", None, 0, 1, 0, 0, 0),
        ("1101", "Clientes USD", "asset", None, 0, 1, 0, 0, 0),
        ("2100", "Proveedores ARS", "liability", None, 0, 0, 0, 0, 0),
        ("2101", "Proveedores USD", "liability", None, 0, 0, 0, 0, 0),
        ("1200", "Cheques por cobrar", "asset", None, 0, 0, 0, 0, 0),
        ("5100", "Resultado por tipo de cambio", "income", None, 0, 0, 1, 0, 0),
        ("5200", "Ingresos por comisiones", "income", None, 0, 0, 0, 1, 0),
        ("5300", "Gastos/Comisiones pagadas", "expense", None, 0, 0, 0, 0, 1),
        ("5400", "Ingresos por intereses", "income", None, 0, 0, 0, 0, 0),
        ("5500", "Gastos por intereses", "expense", None, 0, 0, 0, 0, 0),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO accounts (code, name, type, parent_id, is_cash, is_client_account, "
        "is_fx_result, is_commission_income, is_commission_expense) VALUES (?,?,?,?,?,?,?,?,?)",
        accounts,
    )

    # Admin user
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin")
    hashed = hashlib.sha256(admin_password.encode()).hexdigest()
    cursor.execute(
        "INSERT OR IGNORE INTO users (email, hashed_password, is_active, is_admin) VALUES (?, ?, 1, 1)",
        (admin_email, hashed),
    )


def main():
    db_file = DB_PATH
    should_create = not os.path.exists(db_file)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    if should_create:
        print(f"Creating database {db_file}…")
        run_schema(cursor)
        insert_initial_data(cursor)
        conn.commit()
        print("Database initialised.")
    else:
        print(f"Database {db_file} already exists.")
    conn.close()


if __name__ == "__main__":
    main()