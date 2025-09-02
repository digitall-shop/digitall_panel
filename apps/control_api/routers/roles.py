from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_session
from packages.common.vpnpanel_common.db.models import Role, AuditLog
from .. import schemas
from ..security import require_admin
from uuid import UUID

router = APIRouter()

async def log(session, actor, action, target_type, target_id):
    session.add(AuditLog(action=action, actor_user_id=actor, target_type=target_type, target_id=str(target_id)))

@router.post("/", response_model=schemas.RoleOut, status_code=201)
async def create_role(body: schemas.RoleCreate, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    existing = await session.execute(select(Role).where(Role.name == body.name))
    if existing.scalars().first():
        raise HTTPException(400, "role exists")
    role = Role(name=body.name, description=body.description)
    session.add(role)
    await log(session, user.id, "role.create", "role", role.id)
    await session.commit(); await session.refresh(role)
    return role

@router.get("/", response_model=list[schemas.RoleOut])
async def list_roles(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Role))
    return res.scalars().all()

@router.get("/{role_id}", response_model=schemas.RoleOut)
async def get_role(role_id: UUID, session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Role).where(Role.id == role_id))
    r = res.scalars().first()
    if not r:
        raise HTTPException(404, "not found")
    return r

@router.patch("/{role_id}", response_model=schemas.RoleOut)
async def update_role(role_id: UUID, body: schemas.RoleCreate, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    res = await session.execute(select(Role).where(Role.id == role_id))
    r = res.scalars().first()
    if not r:
        raise HTTPException(404, "not found")
    if body.name:
        r.name = body.name
    r.description = body.description
    await log(session, user.id, "role.update", "role", r.id)
    await session.commit(); await session.refresh(r)
    return r

@router.delete("/{role_id}", status_code=204)
async def delete_role(role_id: UUID, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    res = await session.execute(select(Role).where(Role.id == role_id))
    r = res.scalars().first()
    if not r:
        raise HTTPException(404, "not found")
    await log(session, user.id, "role.delete", "role", r.id)
    await session.delete(r); await session.commit()
    return None
