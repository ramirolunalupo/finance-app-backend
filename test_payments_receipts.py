"""Test payment and receipt operations using the sqlite API."""

from fastapi.testclient import TestClient
from app.main_sqlite import app, DB_FILE
from init_db_sqlite import main as init_db
import os


def setup_db():
    # Ensure fresh DB
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init_db()


def test_payment_and_receipt():
    setup_db()
    client = TestClient(app)
    # Login
    resp = client.post("/auth/login", json={"email": "admin@example.com", "password": "admin"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Create supplier
    client.post("/parties", json={"name": "Proveedor X", "type": "supplier"}, headers=headers)
    # Payment: pay 1000 ARS with 10% commission and 50 expenses
    pay_resp = client.post(
        "/operations/payment",
        json={
            "date": "2025-12-05T00:00:00",
            "party_name": "Proveedor X",
            "currency": "ARS",
            "gross_amount": 1000,
            "commission_percentage": 10,
            "expenses_amount": 50,
            "payment_method": "transferencia"
        },
        headers=headers,
    )
    assert pay_resp.status_code == 200
    total_paid = pay_resp.json()["total_paid"]
    assert total_paid == 1000 + 100 + 50
    # Receipt: receive 2000 ARS from client with 5% commission and no expenses
    client.post("/parties", json={"name": "Cliente Y", "type": "client"}, headers=headers)
    rec_resp = client.post(
        "/operations/receipt",
        json={
            "date": "2025-12-06T00:00:00",
            "party_name": "Cliente Y",
            "currency": "ARS",
            "gross_amount": 2000,
            "commission_percentage": 5,
            "expenses_amount": 0,
            "payment_method": "efectivo"
        },
        headers=headers,
    )
    assert rec_resp.status_code == 200
    net = rec_resp.json()["net_received"]
    assert net == 2000 - 100 - 0
    # Check position: ARS balance should reflect payment and receipt
    pos = client.get("/reports/position", headers=headers).json()
    # Starting from 0, payment decreased ARS by 1150, receipt increased ARS by 1900 => net +750
    assert pos["ars_balance"] == 750


if __name__ == "__main__":
    test_payment_and_receipt()