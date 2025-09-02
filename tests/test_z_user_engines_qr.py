import pytest
from httpx import AsyncClient
from apps.control_api.main import app

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASS = "Secret123!"

@pytest.mark.asyncio
async def test_user_engine_toggle_and_wireguard_qr():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Try login, if fails register then login
        r = await client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        if r.status_code != 200:
            rr = await client.post("/auth/register", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
            assert rr.status_code == 201, rr.text
            r = await client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a new user
        email = "engines-user@example.com"
        r = await client.post("/users/", json={"email": email, "password": "Secret123!"}, headers=headers)
        if r.status_code == 201:
            user_id = r.json()["id"]
        else:
            assert r.status_code == 400
            users = (await client.get("/users/", headers=headers)).json()
            user_id = next(u["id"] for u in users if u["email"] == email)

        # Restrict engines to xray only
        r = await client.post(f"/users/{user_id}/engines", json={"engines": ["xray"]}, headers=headers)
        assert r.status_code == 200, r.text

        # Fetch configs: should not include wireguard
        r = await client.get(f"/users/{user_id}/configs", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "xray" in data
        assert "wireguard" not in data

        # Attempt QR (should be 403)
        r = await client.get(f"/users/{user_id}/wireguard/qr", headers=headers)
        assert r.status_code == 403, r.text

        # Enable wireguard
        r = await client.post(f"/users/{user_id}/engines", json={"engines": ["xray", "wireguard"]}, headers=headers)
        assert r.status_code == 200

        # Now QR should work
        r = await client.get(f"/users/{user_id}/wireguard/qr", headers=headers)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/svg+xml")
