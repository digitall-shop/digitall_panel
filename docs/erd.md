# ERD Description

Entities & Relationships (simplified textual ER diagram):

TENANT (1) ──< (N) USER
TENANT (1) ──< (N) ROLE ──< (N) ROLE_ASSIGNMENT >── (N) USER
TENANT (1) ──< (N) NODE ──< (N) XRAY_INBOUND
TENANT (1) ──< (N) NODE_TAG ──< (N:M) NODE_TAG_MAP >── NODE
TENANT (1) ──< (N) PLAN
USER (1) ──< (N) SUBSCRIPTION  (tenant_id carried for scoping)
PLAN (1) ──< (N) SUBSCRIPTION (optional)
SUBSCRIPTION (1) ──< (1) CREDENTIAL (per engine; unique pair)
SUBSCRIPTION (1) ──< (N) WG_PEER (per node where wireguard assigned)
SUBSCRIPTION (1) ──< (N) ASSIGNMENT >── (N) NODE (engine-scoped, role primary/secondary)
SUBSCRIPTION (1) ──< (N) TRAFFIC_EVENT (partitioned daily)
SUBSCRIPTION (1) ──< (N) TRAFFIC_ROLLUP_HOURLY (partitioned monthly)
USER (N) ──< (N) AUDIT_LOG (actor_user_id optional; some system actions)
TENANT (1) ──< (N) AUDIT_LOG

Key Points:
- credentials.engine ensures exactly one credential per engine per subscription.
- assignments enforce which nodes serve which subscription & engine.
- wg_peers provide per-node WireGuard specifics (AllowedIPs differ per node if split networks).
- traffic_events heavy volume; partitioned. rollups store aggregated metrics for faster queries.

Notation: (1) one, (N) many, (N:M) many-to-many via join table.

