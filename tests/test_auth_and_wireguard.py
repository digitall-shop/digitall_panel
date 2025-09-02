import os
import pytest
import uuid
from httpx import AsyncClient
from app.main import app
from app.db.database import engine, Base

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    # Ensure fresh sqlite file
    if os.path.exists("app.db"):
        os.remove("app.db")
    async with engine.begin() as conn:  # type: ignore
        await conn.run_sync(Base.metadata.create_all)
    yield

@pytest.mark.asyncio
async def test_register_login_create_wireguard_account():
    username = f"user_{uuid.uuid4().hex[:8]}"
    password = "secret123"
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        # Register
        r = await client.post("/api/v1/auth/register", json={"username": username, "password": password})
        assert r.status_code == 201, r.text
        user_id = r.json()["id"]

        # Login
        r = await client.post("/api/v1/auth/token", data={"username": username, "password": password}, headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # Create wireguard account
        r = await client.post("/api/v1/accounts/wireguard", headers=headers)
        assert r.status_code == 201, r.text
        acc_id = r.json()["id"]

        # List my accounts
        r = await client.get("/api/v1/accounts/me", headers=headers)
        assert r.status_code == 200
        assert any(a["id"] == acc_id for a in r.json())

        # Get config
        r = await client.get(f"/api/v1/accounts/{acc_id}/config", headers=headers)
        assert r.status_code == 200, r.text
        assert "[Interface]" in r.text
        assert "[Peer]" in r.text

