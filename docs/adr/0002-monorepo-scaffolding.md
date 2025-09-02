# ADR 0002: Monorepo Scaffolding & Cross-Cutting Implementation Decisions

Date: 2025-09-02  
Status: Accepted  
Supersedes / Related: Complements ADR 0001 (foundational stack)

## Context
ADR 0001 established the high-level technology stack (FastAPI async services, SQLAlchemy 2.0 async ORM, Alembic, Redis, structured logging, Prometheus metrics, Argon2 hashing, JWT, RBAC, mTLS between panel and nodes). This ADR records the concrete repository scaffolding and codifies the mandatory implementation conventions now in place so future additions stay consistent.

Key drivers:
- Enforce 12-Factor configuration across all services.
- Provide repeatable developer workflow (format, lint, test, proto generation) with uniform Makefiles.
- Ensure security & observability primitives (Argon2, JWT, structlog JSON, Prometheus) are centrally provided via a shared common package.
- Prepare control-plane ↔ node secure comms (HTTPS + mTLS) and future gRPC streaming channels.

## Decision
Adopt & lock in the following monorepo structure and cross-cutting implementation policies:

### 1. Monorepo Layout
```
/apps
  /control-api      (HTTP REST + future gRPC client; panel control surface)
  /collector        (ingestion service; future gRPC server for streaming stats)
  /scheduler        (periodic tasks / quota & expiry enforcement)
  /node-agent       (runs on edge nodes, reports metrics, executes config)
/packages
  /common/vpnpanel_common (shared config, logging, metrics, proto stubs, security utils)
/deploy/compose
  /control          (docker-compose assets for control plane stack)
  /node             (docker-compose assets for node-side agent)
/docs/adr          (architecture decision records)
/proto             (gRPC proto definitions)
```

### 2. Service Conventions
Each service MUST:
- Expose /health (readiness) and /metrics (Prometheus) endpoints (FastAPI mounts or minimal ASGI).
- Load configuration exclusively from environment variables via a shared Pydantic Settings class (env_file ONLY for local dev).
- Use async FastAPI + async SQLAlchemy patterns (session management via explicit async context when DB used).
- Emit JSON logs (structlog) with contextual keys: event, level, service, request_id (if HTTP), tenant_id (when available), node_id (agent / collector paths).
- Register base service_info metric (Gauge: service, version) on startup.
- Hash credentials using Argon2id (argon2-cffi) via shared helper; no direct bcrypt usage (legacy passlib kept only if migration needed; new code uses Argon2 helper).
- Issue and validate JWT (PyJWT) with KID header support for future key rotation; expiration derived from env-configured lifetimes.
- Enforce RBAC (admin/owner/operator/auditor) at route layer via dependency functions (shared decorators / FastAPI dependencies, cached policy in Redis).
- Prepare for mutual TLS: control-plane outbound HTTP/gRPC clients must support presenting a client certificate; node-agent must validate CA chain.

### 3. Tooling & Quality Gates
- Pre-commit hooks (black, ruff, eof-fixer, trailing-whitespace, yaml checks) REQUIRED before merge; CI will run `make lint` + `make test`.
- Makefile Targets (uniform):
  - run (dev execution)
  - fmt (black + ruff format limited to service scope)
  - lint (ruff static analysis)
  - test (pytest with service-focused selection OR full suite at root)
  - proto (delegates to root `make generate-proto`)
- Root Makefile aggregates fmt/lint/test and proto generation (grpc_tools.protoc → shared package path).

### 4. Shared Package (packages/common/vpnpanel_common)
Provides:
- Settings (12-Factor env ingestion)
- Logging configuration (structlog processors assembling JSON for stdout)
- Metrics helpers (Prometheus registry + service_info Gauge; multiprocess support env-gated)
- Security primitives (password hashing {Argon2id}, JWT encode/decode with error mapping)
- (Planned) mTLS client context builders & certificate rotation helpers
- (Planned) RBAC policy cache abstraction backed by Redis

### 5. Security & Crypto
- Argon2id parameters (initial baseline) documented: time_cost=2, memory_cost=512 MB (tune), parallelism=2; to be validated under production hardware—tracked as a follow-up.
- JWT clock skew tolerance configurable (future addition; default 0–30s window TBD).
- Admin RBAC enforcement: privileged endpoints decorated; allowed admin source IPs validated against CIDR allowlist env var.

### 6. Observability
- Logging strictly structured; no bare print().
- Metrics namespace kept flat initially; prefix collisions avoided via consistent naming (service_* or domain-specific counters).
- Trace integration (OpenTelemetry) optional; toggle via env (future). Basic instrumentation hooks will live in common package.

### 7. Database & Migrations
- SQLAlchemy 2.0 style (declarative + typed annotations) for models; async session for I/O.
- Alembic env configured for async engine (future integration step); migration scripts kept under /app or /migrations (TBD in separate ADR if layout changes). This ADR only locks in Alembic usage, not directory finalization.

### 8. Redis Usage
- Centralized for caching (JWT blacklist / revocation if needed), RBAC policy, rate limiting tokens, lightweight task signalling.
- Strict separation of logical DB indexes by concern (document to avoid key collisions) – to be enumerated in follow-up doc.

### 9. Mutual TLS (Panel ↔ Nodes)
- Internal CA issues both control-plane client certs and node-agent server certs (and optionally reciprocal for bidirectional auth depending on chosen directionality). SAN contains node_id.
- All control-plane → node REST/gRPC calls must validate presented certificate chain + node_id match (future middleware / interceptor).
- Certificate rotation process (grace window, dual-trust) deferred to a future ADR once implementation begins.

### 10. Compliance Checklist (Per Service)
- [x] Directory exists
- [x] Makefile with run/fmt/lint/test/proto
- [x] Health endpoint
- [x] Metrics mount (where FastAPI present; node-agent pending HTTP layer addition)
- [x] Uses shared Settings + logging
- [ ] RBAC decorators (placeholder; to implement)
- [ ] JWT issuance/validation integration (placeholder; control-api only initially)
- [ ] Argon2 helpers exposed (WIP – ensure bcrypt removed from new code paths)
- [ ] mTLS client/server plumbing (future)

Items left unchecked are intentionally staged for incremental PRs.

## Rationale
Centralizing these decisions early reduces divergence, accelerates onboarding, and limits refactors. The explicit checklist clarifies current coverage vs. planned features while tying directly back to ADR 0001’s strategic selections.

## Alternatives Considered
1. Multiple repositories (polyrepo): rejected due to overhead for early-stage iteration and cross-cutting changes.
2. Poetry/uv per-service envs: deferred; single pinned requirements.txt simpler initially. Could move to per-service lockfiles later.
3. Gunicorn + workers from start: premature; uvicorn direct run adequate until scaling is validated.

## Consequences
Positive:
- Consistent developer ergonomics & CI gating.
- Faster feature delivery via shared utilities.
- Clear path for layering security (mTLS, RBAC) without per-service reinvention.
Negative / Trade-offs:
- Single dependency set means heavier global upgrades even if only one service needs a bump.
- Potential naming drift (control-api vs control_api) requires standardization soon.
- Some future concerns (cert rotation, advanced tracing) deferred, implying future ADR churn.

## Follow-Up Actions
1. Implement RBAC decorators + Redis policy cache (Issue: SECURITY-001).
2. Add Argon2 helper module; remove bcrypt variant from new auth flows (SECURITY-002).
3. Standardize control-api directory naming (pick underscore for Python import) (REPO-001).
4. Add Alembic async env + first migration framework (DATA-001).
5. Implement mTLS client/session builder & verify with integration test harness (MTLS-001).
6. Introduce OpenTelemetry optional tracing (OBS-001).

## Status Tracking
This ADR remains Accepted until a structural change (e.g., move to polyrepo, major tool replacement) is proposed, at which point a superseding ADR will be authored.

## References
- ADR 0001 (stack foundations)
- requirements.txt (tooling & runtime deps)
- .pre-commit-config.yaml (code quality enforcement)
- proto/node_control.proto (future gRPC stubs)

