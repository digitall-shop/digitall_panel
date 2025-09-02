# Implementation Phases & Acceptance Criteria

## Phase 0 – Scaffold (CURRENT)
Deliverables:
- Architecture docs, DDL, OpenAPI spec, proto definitions.
- Docker Compose (control + node) & basic service skeletons.
Acceptance:
- Repo builds containers successfully (image build) (manual verify).
- OpenAPI + proto compile without syntax errors.

## Phase 1 – Core Auth & Tenancy
Scope:
- SQLAlchemy models + Alembic migrations for tenants, users, roles, role_assignments.
- JWT auth (access/refresh) + bootstrap superuser + tenant creation flow.
- RBAC middleware enforcing tenant scoping.
Acceptance:
- Tests: create tenant -> user -> login -> role assignment works.
- 100 req/s auth endpoint smoke with <200ms p95 (dev env).

## Phase 2 – Plans & Subscriptions
Scope:
- CRUD for plans; subscription creation (derives quota + expiry), engine validation.
- Credential generation (xray UUID, WireGuard keypair store encrypted).
- Config export endpoints (v2ray link, clash config, wg config + QR code placeholder).
Acceptance:
- Create plan -> subscription -> fetch config outputs valid templates.
- Engines subset rule enforced; invalid returns 422.

## Phase 3 – Node & Assignment Logic
Scope:
- Node registration, tagging, heartbeat endpoint.
- Assignment strategies: manual, round_robin, by_tag.
- Automatic assignment service (scheduler) producing assignments.
Acceptance:
- Assignments stored; duplicate prevention; strategy switch updates future assignments.
- p95 assignment decision <100ms for 10k subs.

## Phase 4 – Node-Agent & Config Push
Scope:
- gRPC NodeControl service (PushFullConfig, StreamEnforcements).
- Node-agent implements config diff for Xray (dynamic API) + WireGuard (wg set / pyroute2).
- mTLS provisioning (dev CA) & revision semantics.
Acceptance:
- Add subscription -> node receives config within <5s.
- Modify subscription status -> suspend command applied (user disabled / peer removed) <5s.
- No Xray restart during changes (validated via uptime check).

## Phase 5 – Traffic Collection & Rollups
Scope:
- TrafficIngest bi-di streaming; node-agent sampling (delta computation) both engines.
- Collector ingestion with dedupe (unique constraint) + raw event insert.
- Rollup job (hourly) + usage snapshot API (subscription usage).
Acceptance:
- Simulated load 10k users * 3 nodes * 1m sampling: <80% of 1 core on collector.
- Duplicates injected -> no double counting (unit test addresses).
- Quota threshold triggers suspension reliably (<2m latency from exceed to suspend).

## Phase 6 – Quota & Expiry Enforcement
Scope:
- Scheduler job computing aggregated usage + in-flight deltas.
- Enforcement push + confirmation; retry & backoff.
- Subscription status transitions (active -> exhausted/expired -> suspended/resumed).
Acceptance:
- Exceed quota triggers status=exhausted; manual override resets usage cache.
- Expired subscriptions not served by nodes.

## Phase 7 – Observability & Hardening
Scope:
- structlog integration, request_id, metrics endpoints.
- Basic Grafana dashboards, alerts rules (sample).
- Rate limiting & admin IP allowlist.
Acceptance:
- Metrics show traffic ingest & quota enforcement counters.
- Security scans (bandit/pip-audit) produce no HIGH severity unresolved.

## Phase 8 – Scale Test & Optimization
Scope:
- Load test 100k subscriptions, measure ingestion latency, DB partition size.
- Index tuning, connection pool adjustments, pgbouncer introduction if needed.
Acceptance:
- 100k subs: insertion p95 <50ms, usage snapshot p95 <300ms.
- Postgres CPU <70% sustained under test profile.

## Phase 9 – Production Readiness
Scope:
- Key rotation (JWT secret), backup & retention policies, partition pruning automation.
- Disaster recovery runbook.
Acceptance:
- Successful restore drill from backup to point-in-time <30m.
- Documented RPO=5m (with WAL shipping), RTO=30m.

## Phase 10 – Nice-to-Haves / Extensions
- Multi-region failover.
- Kafka ingestion pipeline.
- Advanced ABAC policies.
- Web UI (frontend) integration.

