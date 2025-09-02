from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from packages.common.vpnpanel_common.config import Settings
from packages.common.vpnpanel_common.logging import configure_logging
from packages.common.vpnpanel_common.metrics import metrics_app

from .db import init_db
from .routers import auth, tenants, users, roles, memberships, nodes, plans, subscriptions, assignments, traffic, audit

settings = Settings()
configure_logging(service_name="control-api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="Control API",
    version="0.1.0",
    description="""Multi-tenant VPN control plane API providing RBAC, node & user management, subscriptions, traffic ingestion and audit logs. JWT (Bearer) auth.\n\nUse /auth/register to bootstrap the first user then create roles and memberships.""",
    lifespan=lifespan,
)

# Basic CORS (can be tuned)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/metrics", metrics_app)

# Router inclusion with tags & prefixes kept flat for simplicity
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
app.include_router(roles.router, prefix="/roles", tags=["roles"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(memberships.router, prefix="/memberships", tags=["memberships"])
app.include_router(nodes.router, prefix="/nodes", tags=["nodes"])
app.include_router(plans.router, prefix="/plans", tags=["plans"])
app.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
app.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
app.include_router(traffic.router, prefix="/traffic", tags=["traffic"])
app.include_router(audit.router, prefix="/audit", tags=["audit"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": "control-api"}
