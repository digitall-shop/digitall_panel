# VPN Control Plane (Baseline Marzban 0.8.4 API)

This repository is currently in a clean baseline state: the HTTP API surface has been reverted to the original Marzban 0.8.4 endpoints (Admin/Core/Node/Subscription/System/User Template/User/default) with all previously added experimental domains (multi‑tenant, RBAC, commerce, webhooks, scaler, wireguard extensions) removed. This provides a stable foundation for minimal future WireGuard additions.

Default datastore is now PostgreSQL (asyncpg). See `.env.example` for the `SQLALCHEMY_DATABASE_URL` DSN.

Quick start (dev):
1. Copy env: `cp .env.example .env` (adjust secrets)
2. `docker compose -f deploy/compose/control/docker-compose.yml up -d --build`
3. (Migrations) `docker compose -f deploy/compose/control/docker-compose.yml exec control-api alembic upgrade head`
4. Access API via reverse proxy (if enabled) or directly on the control-api service port.

Key environment variables:
- `SQLALCHEMY_DATABASE_URL` (primary) / `DATABASE_URL` (backward compatible) – PostgreSQL DSN
- `POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB` – container initialization
- `REDIS_URL` – Redis cache / queues

Next steps (not yet included):
- Re‑introduce WireGuard subscription endpoints (minimal) without altering existing response shapes
- Add light health / metrics coverage per service

See `openapi/openapi.yaml` for the exact restored endpoint list.
