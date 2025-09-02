from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from ..db import get_session
from packages.common.vpnpanel_common.db.models import Tenant, AuditLog
from ..security import require_admin
from .. import schemas

router = APIRouter()

async def log_audit(session: AsyncSession, actor_id, action, target_type, target_id):
    session.add(AuditLog(action=action, actor_user_id=actor_id, target_type=target_type, target_id=str(target_id)))

@router.post("/", response_model=schemas.TenantOut, status_code=201)
async def create_tenant(body: schemas.TenantCreate, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    existing = await session.execute(select(Tenant).where(Tenant.name == body.name))
    if existing.scalars().first():
        raise HTTPException(400, "tenant exists")
    tenant = Tenant(name=body.name)
    session.add(tenant)
    await log_audit(session, user.id, "tenant.create", "tenant", tenant.id)
    await session.commit()
    await session.refresh(tenant)
    return tenant

@router.get("/", response_model=list[schemas.TenantOut])
async def list_tenants(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Tenant))
    return res.scalars().all()

@router.get("/{tenant_id}", response_model=schemas.TenantOut)
async def get_tenant(tenant_id: UUID, session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    t = res.scalars().first()
    if not t:
        raise HTTPException(404, "not found")
    return t

@router.patch("/{tenant_id}", response_model=schemas.TenantOut)
async def update_tenant(tenant_id: UUID, body: schemas.TenantUpdate, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    res = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    t = res.scalars().first()
    if not t:
        raise HTTPException(404, "not found")
    if body.name:
        t.name = body.name
    await log_audit(session, user.id, "tenant.update", "tenant", t.id)
    await session.commit(); await session.refresh(t)
    return t

@router.delete("/{tenant_id}", status_code=204)
async def delete_tenant(tenant_id: UUID, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    res = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    t = res.scalars().first()
    if not t:
        raise HTTPException(404, "not found")
    await log_audit(session, user.id, "tenant.delete", "tenant", t.id)
    await session.delete(t)
    await session.commit()
    return None
