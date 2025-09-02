# VPN Control Plane (Marzban‑like) – Xray + WireGuard

High‑level: Horizontally scalable control plane managing multi‑tenant VPN subscriptions across Xray & WireGuard nodes. Quota (bytes) + expiry only (no speed limits). Per‑user selectable engines: xray, wireguard, or both. Nodes updated dynamically (no service restarts) via gRPC (mTLS). Traffic sampled/polled and ingested at least‑once; rollups maintained hourly.

See docs/architecture.md, docs/ddl.sql, openapi/openapi.yaml, proto/node_control.proto.

Quick start (dev):
1. cp .env.example .env  (adjust secrets)
2. docker compose up -d --build
3. Apply migrations (future): alembic upgrade head (inside control-api container)
4. Access API: https://localhost:8443 (reverse proxy terminates TLS)

Node bootstrap (example):
 docker compose -f docker-compose.node.yml --env-file .env up -d --build

Components:
- control-api (FastAPI) – Auth, RBAC, CRUD, subscription logic
- collector – ingest traffic events from nodes (gRPC stream) and persist; rollup scheduler
- scheduler – user/node assignment, quota & expiry enforcement pushes
- postgres – primary data store (partitioned traffic tables)
- redis – cache, rate limiting, short task queue, locks
- reverse-proxy (Caddy) – TLS + mTLS to nodes
- node-agent – manages local Xray and WireGuard runtime
- xray – Xray core process with dynamic API
- wireguard – kernel module + wg tool (host network, NET_ADMIN)

Observability: structlog JSON logs, Prometheus /metrics (all services), optional OpenTelemetry traces, Grafana/Loki stack (future). Security: JWT (HS/ or RS/ES) for panel users, Argon2 password hashing, mTLS gRPC channel panel<->nodes, RBAC per tenant.

Milestones: see bottom of architecture doc.

