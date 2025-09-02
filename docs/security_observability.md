# Security & Observability Plan

## Security
- Transport:
  - HTTPS for external panel clients (Caddy TLS / ACME).
  - mTLS (internal CA) for gRPC between nodes and control plane (collector / control-api / scheduler).
- AuthN/AuthZ:
  - JWT (HS256 in dev, RS/ES in prod). Access 15m, Refresh 30d.
  - RBAC: roles (owner, admin, operator, auditor) enforced per-tenant. Policy cache (Redis) with version stamp.
  - Admin IP allowlist middleware (CIDR list configurable via env) for sensitive endpoints (tenant/user/plan mgmt).
- Passwords: Argon2id (argon2-cffi) with tuned parameters (time_cost=3, memory_cost=64MB, parallelism=2 – adjust by benchmark).
- Secrets: .env only for dev; production via Docker secrets or Vault injection. SECRET_KEY rotation strategy: overlapping acceptance window; store key id (kid) in JWT header.
- Input Validation: Pydantic strict types, length & enum constraints, custom validators for engine arrays (non-empty subset of [xray, wireguard]).
- Least Privilege: Service containers run as non-root (future hardening), capabilities dropped except node-agent which needs NET_ADMIN for WireGuard.
- Node Identity: SAN (node_id) in client cert validated; CRL or short-lived cert rotation handled by scheduler (future extension).
- Audit Logging: Append-only audit_logs with actor, action, entity, IP, UA; enrich with request_id trace correlation.
- Rate Limiting: Redis token bucket per IP + per username login attempts. Lock out policy exponential backoff.
- Quota Enforcement: Scheduler calculates usage; enforcement commands push to node-agent; node-agent must confirm; retries with exponential backoff, idempotent by revision.
- Supply Chain: Requirements pinned; periodic SCA scan (future).

## Observability
- Logging: structlog JSON with fields (ts, level, service, request_id, tenant_id, user_id, node_id, msg). Logging level configurable.
- Metrics: prometheus-client. Common metrics: http_requests_total{method,route,status}, http_request_duration_seconds histogram, active_subscriptions gauge, quota_enforcements_total counter, traffic_ingest_bytes_total{engine,dir}, traffic_ingest_lag_seconds gauge.
- Tracing: OpenTelemetry optional, resource attrs (service.name, deployment.environment). Propagate traceparent header.
- Dashboards: (Grafana) panels for:
  - API latency & error rate
  - Traffic usage (bytes) per tenant / engine
  - Quota nearing (top 20 remaining <10%)
  - Node health (heartbeat age, assignments count, capacity score)
  - Ingestion lag & duplicate ratio
- Alerting (future):
  - Node heartbeat stale > 2 * sample interval.
  - Ingestion lag > 5m.
  - Error rate > 2% over 5m.
  - Quota enforcement failures > threshold.
- Partition Maintenance: Scheduler logs partition creation/removal events with metrics (partitions_created_total, partitions_dropped_total).
- Correlation: request_id (UUID v4) in headers X-Request-ID (generate if absent). Include trace_id when tracing.

## Resilience / Recovery
- Backpressure: If Postgres slow, collector uses bounded queue & applies drop policy after warning (prefer buffer at node-agent) – (future improvement).
- Node Buffer: node-agent keeps in-memory ring buffer of recent TrafficSample when disconnected (configurable cap/time). Logs warnings when >80% full.
- Graceful Shutdown: Services expose /health (liveness) and /ready (future) for orchestrator; on TERM stop accepting new requests, flush metrics.

