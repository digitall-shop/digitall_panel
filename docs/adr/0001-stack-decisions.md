# ADR 0001: Technology Stack & Architectural Foundations

Date: 2025-09-02
Status: Accepted

## Context
We are building a horizontally scalable, Marzban-like VPN control plane supporting Xray and WireGuard with up to 100k users. Requirements include multi-tenancy, RBAC, quota (bytes) + expiry enforcement (no speed limiting), per-user selectable engines, dynamic runtime reconfiguration without restarts, and robust traffic accounting. A Python-centric ecosystem was chosen for team familiarity, async IO capabilities, and rich networking libraries.

## Decision
Adopt the following stack & cross-cutting practices:

### Core Backend (Control Plane)
- FastAPI (async) for REST API: high performance, OpenAPI generation, async support.
- SQLAlchemy 2.0 async ORM + Core for DB access; explicit sessions & typed models.
- Alembic for schema migrations (versioned, repeatable, online migration capability).
- PostgreSQL for relational data (partitioned traffic tables) with future scaling (Timescale/Partman optional).
- Redis for: caching (auth/session/RBAC), lightweight queues, distributed locks, rate limiting tokens.

### Node Communication
- HTTPS + mutual TLS (mTLS) for secure transport between panel and nodes.
- gRPC (proto3) for control & traffic ingest channels (streaming, low overhead). HTTP/2 over TLS.

### Security & Auth
- JWT (access & refresh) for stateless auth; rotating secret keys with KID header.
- Argon2id password hashing (argon2-cffi) with tuned parameters.
- RBAC (roles: owner, admin, operator, auditor) enforced at tenant scope with cached policy.
- Admin IP allow-list for privileged endpoints.
- Internal CA for node certificates; SAN includes node_id.

### Observability & Operations
- JSON structured logging with structlog (context enrichment: request_id, tenant_id, node_id).
- Prometheus metrics (service /metrics endpoint) + Grafana dashboards.
- Optional OpenTelemetry traces for distributed correlation.
- Audit log table capturing security-sensitive actions.

### Code Quality & Tooling
- Monorepo layout with isolated service apps and shared common package.
- Pre-commit hooks: black (format), ruff (lint), end-of-file-fixer, trailing-whitespace.
- pytest for tests; pytest-asyncio for async integration.
- 12-Factor configuration strictly via environment variables (with .env only for local dev).
- Makefile per service for common developer tasks (fmt, lint, test, run, proto-gen). Root Makefile aggregates.

### Performance & Scalability
- Async IO stack for high concurrency (FastAPI + async drivers + uvloop optional future).
- Partitioned traffic tables (daily raw, monthly hourly rollups) to bound index bloat & enable retention.
- At-least-once ingestion with dedupe keys for idempotent processing.

### Extensibility
- Common package for shared config, logging, security utilities, metrics helpers, and proto stubs.
- Clear driver abstraction in node-agent for Xray / WireGuard; future engines pluggable.

## Alternatives Considered
1. Django + DRF: Slower for highly concurrent async streaming & adds heavier ORM abstractions.
2. Go microservices: Higher performance potential but slower initial delivery; team velocity lower.
3. REST-only node protocol: Harder to support streaming ingest & enforcement; higher overhead.
4. MongoDB / NoSQL: We need strong relational integrity & partitioning strategy; PostgreSQL fits.

## Consequences
Positive:
- Consistent, maintainable Python stack with rich ecosystem & fast iteration.
- Strong observability and security posture from start.
- Scalable ingestion path with gRPC streaming + partitioned storage.
Negative / Trade-offs:
- Python GIL may cap single-process CPU throughput; mitigated by multi-process scaling.
- gRPC adds operational complexity (cert management, HTTP/2) vs. pure REST.
- Async complexity (session management, proper cancellation) requires discipline.

## Compliance / Non-Functional
- All services export health & metrics endpoints.
- Structured logs mandatory; no print statements.
- No blocking network or CPU-intense work in event loop (offload if needed).
- Secrets never logged, hashed credentials only.

## Status & Next Steps
This ADR governs initial implementation. Revisit if traffic scale exceeds design thresholds (introduce Kafka, specialized TSDB, or Go ingestion microservice) or if engine set expands.

## References
- Architecture Doc (docs/architecture.md)
- DDL Schema (docs/ddl.sql)
- OpenAPI (openapi/openapi.yaml)
- Proto (proto/node_control.proto)

