from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_session
from packages.common.vpnpanel_common.db.models import Membership, Tenant, User, Role, AuditLog
from .. import schemas
from ..security import get_current_user, require_admin
from uuid import UUID

router = APIRouter()

async def log(session, actor, action, target_type, target_id):
    session.add(AuditLog(action=action, actor_user_id=actor, target_type=target_type, target_id=str(target_id)))

@router.post("/", response_model=schemas.MembershipOut, status_code=201)
async def create_membership(body: schemas.MembershipCreate, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    # Basic validation existence
    for model, field, value in [(Tenant, Tenant.id, body.tenant_id), (User, User.id, body.user_id), (Role, Role.id, body.role_id)]:
        res = await session.execute(select(model).where(field == value))
        if not res.scalars().first():
            raise HTTPException(404, f"{model.__name__} not found")
    existing = await session.execute(select(Membership).where(Membership.tenant_id==body.tenant_id, Membership.user_id==body.user_id, Membership.role_id==body.role_id))
    if existing.scalars().first():
        raise HTTPException(400, "membership exists")
    m = Membership(tenant_id=body.tenant_id, user_id=body.user_id, role_id=body.role_id)
    session.add(m)
    await log(session, user.id, "membership.create", "membership", m.id)
    await session.commit(); await session.refresh(m)
    return m

@router.get("/", response_model=list[schemas.MembershipOut])
async def list_memberships(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Membership))
    return res.scalars().all()

@router.delete("/{membership_id}", status_code=204)
async def delete_membership(membership_id: UUID, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    res = await session.execute(select(Membership).where(Membership.id == membership_id))
    m = res.scalars().first()
    if not m:
        raise HTTPException(404, "membership not found")
    await log(session, user.id, "membership.delete", "membership", m.id)
    await session.delete(m); await session.commit()
    return None
