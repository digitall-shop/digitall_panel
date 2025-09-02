# Architecture – Marzban‑like Multi‑Engine VPN Panel

## 1. High‑Level Overview
Components (control plane) -> responsibilities:
- reverse-proxy (Caddy): TLS termination (ACME), HTTP/2 & gRPC, request logging, mTLS client auth for node agents.
- control-api (FastAPI): Auth (JWT), RBAC, multi‑tenant CRUD (tenants/users/plans/subscriptions/nodes), assignment logic API, link & config generation (v2ray / clash / WireGuard). Issues signed short‑lived node tokens (mTLS certs created out‑of‑band or via internal CA).
- collector: gRPC server endpoint ingesting streamed traffic samples (Xray counters, WireGuard wg show deltas). Performs idempotent upsert of traffic_events (raw) and triggers rollup pipeline (hourly partitions) using Redis locks.
- scheduler: Periodic tasks (APScheduler / custom) for quota expiry evaluation, node assignment reconciliation, rollup compaction, key rotation. Publishes enforcement tasks to Redis stream / queue consumed by control-api or directly pushes via gRPC to nodes.
- postgres: Primary relational store (SQLAlchemy 2.0). Declarative partitioning for high‑volume traffic tables. Extensions: pgcrypto (optional), uuid‑ossp, timescaledb (optional future), pg_partman (optional).
- redis: Caching (user active state, auth session invalidations), distributed locks (SET NX PX), lightweight task queues (Redis Streams / Lists), rate limits (token bucket).
- prometheus (optional dev) + grafana + loki (optional) for observability.

Node side (per edge server):
- node-agent (Python async): Maintains gRPC mTLS channel to control plane. Applies differential user config for both engines, gathers usage samples, enforces suspensions instantly (disabling user in Xray / removing WireGuard peer / setting allowed IP to 0.0.0.0/32). Abstract driver interface.
- xray: Xray core (v2fly) exposing its internal API socket (Unix or 127.0.0.1 restricted). node-agent uses dynamic API (add/remove clients, query stats) – no restarts.
- wireguard: Kernel module + wg tool. node-agent manipulates peers through `wg set` or pyroute2, generates client configs; usage sampled via `wg show`.

### Data Flow (Traffic Accounting)
1. node-agent polls: Xray stats API (e.g. every 60s) & `wg show`.
2. Computes delta since last sample, builds TrafficSample messages (user, subscription, node, bytes_up/down, engine, ts_start, ts_end, monotonic counters).
3. Streams to collector (at-least-once). Collector deduplicates using (node_id, engine, user_id, ts_end, counter_seq) unique key.
4. Raw events inserted into traffic_events (partition by day). Hourly rollup job aggregates into traffic_rollups_hourly (bytes_up/down aggregated per user, node, engine, hour) using INSERT .. ON CONFLICT.
5. Scheduler enforces quota: SUM(rollups + in‑memory recent deltas) >= quota_bytes => mark subscription state=exhausted, push disable command to node(s).

### User Lifecycle
Plan -> Subscription (per tenant). Subscription chooses engines set {xray, wireguard}. Assignment logic selects nodes (primary + redundancy) based on strategy (manual, round_robin, by_tag, by_capacity). Credentials created per engine: Xray UUID + alterId/flow, WireGuard keypair. Node-agent receives engine-specific instructions.

Per-user engine override: Administrators can restrict or expand allowed engines independent of the subscription defaults via POST /users/{user_id}/engines (stored in UserEngines). Config & QR generation honors this filter.

### Scaling
- Stateless API & collector scale horizontally behind proxy (shared Redis + Postgres).
- Node-agent lightweight – maintains single streaming RPC with keepalive.
- Traffic ingestion sharded by node naturally; partitions ensure prune & retention manageable.
- Potential future: Kafka for ingestion if >100k users; initial design keeps Redis + Postgres.

### Security
- mTLS: Each node has client cert signed by internal CA; control plane verifies SAN=node_id.
- JWT: Access (short, 15m) + Refresh (long). Argon2id password hashing (argon2-cffi). RBAC policy evaluation cached.
- Input validation: Pydantic models with strict types. Central exception handler hides internals.
- Secrets: .env only for dev; production via Docker secrets / vault.
- IP allowlist for admin endpoints (middleware).
- Audit logs table capturing who/when/what (immutable append-only).

### Observability
- structlog JSON logs with context (request_id, tenant_id, user_id, node_id).
- Prometheus metrics per service: counters (requests_total), histograms (latency), gauges (active_users, assigned_nodes).
- OpenTelemetry traces optional (OTLP exporter) – trace correlation id injected.
- Dashboards: Traffic usage per tenant, quota nearing, node capacity, ingestion lag.

### Diagram (Textual)
[Clients] -> (reverse-proxy) -> (control-api replicas) -> Postgres / Redis
(node-agents) <gRPC mTLS> (collector & scheduler & control-api)
(collector) -> traffic_events -> rollups
(scheduler) -> enforcement commands -> node-agents

## 2. Component Responsibilities
- control-api: CRUD, auth, RBAC, config generation, assignment endpoints.
- collector: Ingest traffic, dedupe, persist, trigger rollups.
- scheduler: Periodic jobs, quota enforcement, partition maintenance.
- node-agent: Apply config diff, collect traffic, enforce suspension.

## 3. Partition Strategy
traffic_events: RANGE partition by day on event_end_ts (UTC) (daily).
traffic_rollups_hourly: RANGE partition by month on hour_start_ts (UTC). Hourly granularity aggregated; monthly partitioning reduces catalog bloat.
Retention policy: raw events keep 30–90 days; rollups retained 12–24 months.
Automatic partition creation by scheduler (create next N days/months) & drop expired.

## 4. Failure / Resilience
- At-least-once ingestion: duplicate guard by unique constraint; idempotent aggregation.
- Node disconnected: node-agent buffers up to N minutes; after TTL, subscriptions on that node flagged degraded.
- Postgres outage: node-agent continues buffering; control-api returns 503 for sensitive endpoints; circuit breaker pattern.

## 5. Future Extensions
- Kafka ingestion pipeline; per-tenant bandwidth throttling (if requirement changes); multi-region replication; fine-grained per-endpoint ABAC.

## 6. Recent API Additions (v0.1.1)
Additive, backward-compatible endpoints & schemas:
- RBAC Entities: /roles (CRUD), /memberships (create/list/delete) enabling explicit user↔tenant role mapping.
- Per-User Engines: /users/{id}/engines to set allowed subset of [xray, wireguard]; reflected in /users/{id}/configs and WireGuard QR endpoint.
- Config & QR Delivery: /users/{id}/configs returns engine-keyed config artifacts; /users/{id}/wireguard/qr returns SVG QR (403 if wireguard disabled).
- Traffic Ingestion & Summaries: /traffic/events (raw sampling, at-least-once) + /traffic/summary (aggregate). Complements existing /traffic/rollups for hourly aggregation and /traffic/usage snapshot.
- Node Policy & Health: /nodes/{id}/policy stores opaque policy doc for future scheduling/enforcement; /nodes/{id}/health lightweight probe.
- mTLS Clarification: OpenAPI description now explicitly states client cert SAN=node_id requirement.

No existing paths or response shapes were changed; all additions are optional for older clients.

See ddl.sql for schema & openapi spec for contract.
