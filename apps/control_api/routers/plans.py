from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_session
from packages.common.vpnpanel_common.db.models import Plan, AuditLog
from .. import schemas
from ..security import require_admin
from uuid import UUID

router = APIRouter()

async def log(session, actor, action, target_type, target_id):
    session.add(AuditLog(action=action, actor_user_id=actor, target_type=target_type, target_id=str(target_id)))

@router.post("/", response_model=schemas.PlanOut, status_code=201)
async def create_plan(body: schemas.PlanCreate, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    exists = await session.execute(select(Plan).where(Plan.tenant_id == body.tenant_id, Plan.name == body.name))
    if exists.scalars().first():
        raise HTTPException(400, "plan exists")
    plan = Plan(**body.model_dump())
    session.add(plan)
    await log(session, user.id, "plan.create", "plan", plan.id)
    await session.commit(); await session.refresh(plan)
    return plan

@router.get("/", response_model=list[schemas.PlanOut])
async def list_plans(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Plan))
    return res.scalars().all()

@router.get("/{plan_id}", response_model=schemas.PlanOut)
async def get_plan(plan_id: UUID, session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Plan).where(Plan.id == plan_id))
    p = res.scalars().first()
    if not p: raise HTTPException(404, "not found")
    return p

@router.patch("/{plan_id}", response_model=schemas.PlanOut)
async def update_plan(plan_id: UUID, body: schemas.PlanUpdate, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    res = await session.execute(select(Plan).where(Plan.id == plan_id))
    p = res.scalars().first()
    if not p: raise HTTPException(404, "not found")
    data = body.dict(exclude_unset=True)
    for k, v in data.items(): setattr(p, k, v)
    await log(session, user.id, "plan.update", "plan", p.id)
    await session.commit(); await session.refresh(p)
    return p

@router.delete("/{plan_id}", status_code=204)
async def delete_plan(plan_id: UUID, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    res = await session.execute(select(Plan).where(Plan.id == plan_id))
    p = res.scalars().first()
    if not p: raise HTTPException(404, "not found")
    await log(session, user.id, "plan.delete", "plan", p.id)
    await session.delete(p); await session.commit()
    return None
