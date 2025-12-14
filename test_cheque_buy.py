"""Test cheque purchase operation."""

from fastapi.testclient import TestClient
from app.main_sqlite import app, DB_FILE
from init_db_sqlite import main as init_db
import os
from datetime import datetime


def setup_db():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init_db()


def test_cheque_buy():
    setup_db()
    client = TestClient(app)
    # login
    resp = client.post("/auth/login", json={"email": "admin@example.com", "password": "admin"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Create client
    client.post("/parties", json={"name": "Cliente Cheque", "type": "client"}, headers=headers)
    # Buy cheque: nominal 10000 ARS, rate 0.1 (10%), due in 30 days, commission 200, expenses 50
    date = datetime(2025, 12, 7)
    due = datetime(2026, 1, 6)
    resp = client.post(
        "/operations/cheque_buy",
        json={
            "date": date.isoformat(),
            "party_name": "Cliente Cheque",
            "currency": "ARS",
            "bank": "Banco X",
            "number": "123456",
            "nominal_amount": 10000,
            "due_date": due.isoformat(),
            "interest_rate": 0.1,
            "interest_base": 365,
            "commissions_amount": 200,
            "expenses_amount": 50
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # Interest amount should be 10000 * 0.1 * 30/365 ≈ 82.19
    assert round(data["interest_amount"], 2) == round(10000 * 0.1 * 30 / 365, 2)
    assert data["net_amount"] == round(10000 - data["interest_amount"] - 200 - 50, 2)
    # List cheques
    cheques = client.get("/reports/cheques", headers=headers).json()
    assert len(cheques) == 1
    assert cheques[0]["status"] == "pending"


if __name__ == "__main__":
    test_cheque_buy()