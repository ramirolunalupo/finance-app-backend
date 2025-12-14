"""Integration tests for the sqlite‑based FastAPI application."""

from fastapi.testclient import TestClient
from app.main_sqlite import app, DB_FILE
import os
import sqlite3
import hashlib


def setup_db():
    # Ensure a fresh database for testing
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    # Recreate DB
    from init_db_sqlite import main as init_db
    init_db()


def test_login_and_fx_flow():
    setup_db()
    client = TestClient(app)
    # Login with admin credentials
    response = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "admin"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Create a new party
    party_resp = client.post(
        "/parties",
        json={"name": "Test Client", "type": "client"},
        headers=headers,
    )
    assert party_resp.status_code == 200
    party_id = party_resp.json()["id"]
    # Create FX operation (buy 100 USD @ 1400)
    fx_resp = client.post(
        "/operations/fx",
        json={
            "date": "2025-12-03T00:00:00",
            "party_name": "Test Client",
            "fx_type": "buy",
            "usd_amount": 100,
            "exchange_rate": 1400,
            "notes": "Test FX buy",
        },
        headers=headers,
    )
    assert fx_resp.status_code == 200
    # Check position
    pos_resp = client.get("/reports/position", headers=headers)
    assert pos_resp.status_code == 200
    data = pos_resp.json()
    assert data["usd_position"] == 100
    assert data["ars_balance"] == -140000


if __name__ == "__main__":
    test_login_and_fx_flow()