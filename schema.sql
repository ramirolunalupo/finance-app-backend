-- SQL schema for the finance application

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    is_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Currencies table
CREATE TABLE IF NOT EXISTS currencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

-- Parties (clients/suppliers)
CREATE TABLE IF NOT EXISTS parties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT CHECK(type IN ('client','supplier')) DEFAULT 'client',
    email TEXT,
    phone TEXT,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chart of accounts
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    type TEXT CHECK(type IN ('asset','liability','equity','income','expense')) NOT NULL,
    parent_id INTEGER,
    is_cash BOOLEAN DEFAULT 0,
    is_client_account BOOLEAN DEFAULT 0,
    is_fx_result BOOLEAN DEFAULT 0,
    is_commission_income BOOLEAN DEFAULT 0,
    is_commission_expense BOOLEAN DEFAULT 0,
    FOREIGN KEY(parent_id) REFERENCES accounts(id)
);

-- Operation types
CREATE TABLE IF NOT EXISTS operation_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
);

-- Operations (header)
CREATE TABLE IF NOT EXISTS operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TIMESTAMP NOT NULL,
    operation_type_id INTEGER NOT NULL,
    party_id INTEGER,
    amount NUMERIC(18,2) NOT NULL,
    currency_id INTEGER NOT NULL,
    exchange_rate NUMERIC(18,4),
    notes TEXT,
    user_id INTEGER NOT NULL,
    FOREIGN KEY(operation_type_id) REFERENCES operation_types(id),
    FOREIGN KEY(party_id) REFERENCES parties(id),
    FOREIGN KEY(currency_id) REFERENCES currencies(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- Journal entries (double entry lines)
CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    debit NUMERIC(18,2) DEFAULT 0,
    credit NUMERIC(18,2) DEFAULT 0,
    currency_id INTEGER NOT NULL,
    FOREIGN KEY(operation_id) REFERENCES operations(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id),
    FOREIGN KEY(currency_id) REFERENCES currencies(id)
);

-- FX details
CREATE TABLE IF NOT EXISTS fx_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id INTEGER UNIQUE NOT NULL,
    usd_amount NUMERIC(18,2) NOT NULL,
    ars_amount NUMERIC(18,2) NOT NULL,
    fx_type TEXT CHECK(fx_type IN ('buy','sell')) NOT NULL,
    FOREIGN KEY(operation_id) REFERENCES operations(id)
);

-- Cheques
CREATE TABLE IF NOT EXISTS cheques (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id INTEGER NOT NULL,
    party_id INTEGER,
    bank TEXT NOT NULL,
    number TEXT NOT NULL,
    nominal_amount NUMERIC(18,2) NOT NULL,
    issue_date DATE,
    due_date DATE NOT NULL,
    expected_accreditation_date DATE,
    interest_rate NUMERIC(10,4),
    interest_base INTEGER DEFAULT 365,
    expenses NUMERIC(18,2) DEFAULT 0,
    commissions NUMERIC(18,2) DEFAULT 0,
    net_amount NUMERIC(18,2),
    status TEXT CHECK(status IN ('pending','accredited','expired','rejected','cancelled')) DEFAULT 'pending',
    currency_id INTEGER NOT NULL,
    FOREIGN KEY(operation_id) REFERENCES operations(id),
    FOREIGN KEY(party_id) REFERENCES parties(id),
    FOREIGN KEY(currency_id) REFERENCES currencies(id)
);

-- Payment details (yo pago)
CREATE TABLE IF NOT EXISTS payment_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id INTEGER UNIQUE NOT NULL,
    gross_amount NUMERIC(18,2) NOT NULL,
    commission_amount NUMERIC(18,2) DEFAULT 0,
    commission_percentage NUMERIC(10,4),
    expenses_amount NUMERIC(18,2) DEFAULT 0,
    payment_method TEXT,
    FOREIGN KEY(operation_id) REFERENCES operations(id)
);

-- Receipt details (me pagan)
CREATE TABLE IF NOT EXISTS receipt_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id INTEGER UNIQUE NOT NULL,
    gross_amount NUMERIC(18,2) NOT NULL,
    commission_amount NUMERIC(18,2) DEFAULT 0,
    commission_percentage NUMERIC(10,4),
    expenses_amount NUMERIC(18,2) DEFAULT 0,
    payment_method TEXT,
    FOREIGN KEY(operation_id) REFERENCES operations(id)
);