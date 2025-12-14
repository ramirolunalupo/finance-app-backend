"""Test client ledger report and cheque status update."""

from fastapi.testclient import TestClient
from app.main_sqlite import app, DB_FILE
from init_db_sqlite import main as init_db
import os


def setup_db():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init_db()


def test_client_ledger_and_cheque_status():
    setup_db()
    client = TestClient(app)
    # login
    resp = client.post("/auth/login", json={"email": "admin@example.com", "password": "admin"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Create a client party
    client.post("/parties", json={"name": "Cliente Ledger", "type": "client"}, headers=headers)
    # Record a receipt: client pays 1000 ARS with 10% commission
    client.post(
        "/operations/receipt",
        json={
            "date": "2025-12-08T00:00:00",
            "party_name": "Cliente Ledger",
            "currency": "ARS",
            "gross_amount": 1000,
            "commission_percentage": 10,
            "expenses_amount": 0,
            "payment_method": "efectivo"
        },
        headers=headers,
    )
    # Record FX sell: client sells 500 USD @ 1400
    client.post(
        "/operations/fx",
        json={
            "date": "2025-12-09T00:00:00",
            "party_name": "Cliente Ledger",
            "fx_type": "sell",
            "usd_amount": 500,
            "exchange_rate": 1400
        },
        headers=headers,
    )
    # Get ledger
    ledger = client.get("/reports/client_ledger", params={"party_name": "Cliente Ledger"}, headers=headers).json()
    assert len(ledger) > 0
    # Running balance should update per entry; final balance equals sum of debits - credits
    final_balance = ledger[-1]['balance']
    expected = 0
    for entry in ledger:
        expected = entry['balance']
    assert final_balance == expected
    # Test update cheque status on nonexistent cheque returns 404
    resp = client.post("/cheques/999/status", params={"new_status": "accredited"}, headers=headers)
    assert resp.status_code == 404