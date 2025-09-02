import pytest
import uuid
from httpx import AsyncClient
from apps.control_api.main import app

@pytest.mark.asyncio
async def test_control_api_auth_and_crud_flow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register initial user (bootstrap)
        r = await client.post("/auth/register", json={"email": "admin@example.com", "password": "Secret123!"})
        assert r.status_code == 201, r.text
        admin_id = r.json()["id"]

        # Login
        r = await client.post("/auth/login", json={"email": "admin@example.com", "password": "Secret123!"})
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create tenant (bootstrap admin bypass)
        r = await client.post("/tenants/", json={"name": "acme"}, headers=headers)
        assert r.status_code == 201, r.text
        tenant_id = r.json()["id"]

        # Create admin role
        r = await client.post("/roles/", json={"name": "admin"}, headers=headers)
        assert r.status_code == 201, r.text
        role_id = r.json()["id"]

        # Assign membership (makes user real admin)
        r = await client.post("/memberships/", json={"tenant_id": tenant_id, "user_id": admin_id, "role_id": role_id}, headers=headers)
        assert r.status_code == 201, r.text

        # Create second user (now requires admin)
        r = await client.post("/users/", json={"email": "user2@example.com", "password": "Secret123!"}, headers=headers)
        assert r.status_code == 201, r.text
        user2_id = r.json()["id"]

        # Create node
        r = await client.post("/nodes/", json={"name": "node-1", "region": "eu"}, headers=headers)
        assert r.status_code == 201, r.text
        node_id = r.json()["id"]

        # Update node policy
        r = await client.post(f"/nodes/{node_id}/policy", json={"allow": True}, headers=headers)
        assert r.status_code == 200, r.text

        # Create plan
        r = await client.post("/plans/", json={"tenant_id": tenant_id, "name": "basic", "quota_bytes": 1000, "duration_days": 30}, headers=headers)
        assert r.status_code == 201, r.text
        plan_id = r.json()["id"]

        # Create subscription for second user
        r = await client.post("/subscriptions/", json={"tenant_id": tenant_id, "user_id": user2_id, "plan_id": plan_id}, headers=headers)
        assert r.status_code == 201, r.text

        # Assign user to node
        r = await client.post("/assignments/", json={"user_id": user2_id, "node_id": node_id}, headers=headers)
        assert r.status_code == 201, r.text

        # Ingest traffic events
        r = await client.post("/traffic/events", json=[{"user_id": user2_id, "node_id": node_id, "bytes_up": 10, "bytes_down": 20}], headers=headers)
        assert r.status_code == 202, r.text

        # Traffic summary
        r = await client.get(f"/traffic/summary?user_id={user2_id}", headers=headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data and data[0]["total_up"] == 10 and data[0]["total_down"] == 20

        # Audit logs listing
        r = await client.get("/audit/logs", headers=headers)
        assert r.status_code == 200, r.text
        assert len(r.json()) > 0

