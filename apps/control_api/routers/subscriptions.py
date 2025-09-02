from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_session
from packages.common.vpnpanel_common.db.models import Subscription, Plan, User, AuditLog
from .. import schemas
from ..security import require_admin
from uuid import UUID

router = APIRouter()

async def log(session, actor, action, target_type, target_id):
    session.add(AuditLog(action=action, actor_user_id=actor, target_type=target_type, target_id=str(target_id)))

@router.post("/", response_model=schemas.SubscriptionOut, status_code=201)
async def create_subscription(body: schemas.SubscriptionCreate, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    if body.plan_id:
        pres = await session.execute(select(Plan).where(Plan.id == body.plan_id))
        if pres.scalars().first() is None:
            raise HTTPException(404, "plan not found")
    ures = await session.execute(select(User).where(User.id == body.user_id))
    if ures.scalars().first() is None:
        raise HTTPException(404, "user not found")
    sub = Subscription(**body.model_dump())
    session.add(sub)
    await log(session, user.id, "subscription.create", "subscription", sub.id)
    await session.commit(); await session.refresh(sub)
    return sub

@router.get("/", response_model=list[schemas.SubscriptionOut])
async def list_subscriptions(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Subscription))
    return res.scalars().all()

@router.get("/{subscription_id}", response_model=schemas.SubscriptionOut)
async def get_subscription(subscription_id: UUID, session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Subscription).where(Subscription.id == subscription_id))
    s = res.scalars().first()
    if not s: raise HTTPException(404, "not found")
    return s

@router.patch("/{subscription_id}", response_model=schemas.SubscriptionOut)
async def update_subscription(subscription_id: UUID, body: schemas.SubscriptionUpdate, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    res = await session.execute(select(Subscription).where(Subscription.id == subscription_id))
    s = res.scalars().first()
    if not s: raise HTTPException(404, "not found")
    data = body.dict(exclude_unset=True)
    for k, v in data.items(): setattr(s, k, v)
    await log(session, user.id, "subscription.update", "subscription", s.id)
    await session.commit(); await session.refresh(s)
    return s

@router.delete("/{subscription_id}", status_code=204)
async def delete_subscription(subscription_id: UUID, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    res = await session.execute(select(Subscription).where(Subscription.id == subscription_id))
    s = res.scalars().first()
    if not s: raise HTTPException(404, "not found")
    await log(session, user.id, "subscription.delete", "subscription", s.id)
    await session.delete(s); await session.commit()
    return None
