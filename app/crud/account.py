from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app import models

async def create_account(db: AsyncSession, user: models.User, protocol: models.ProtocolEnum, public_key: str | None = None, private_key: str | None = None, endpoint: str | None = None) -> models.VPNAccount:
    acc = models.VPNAccount(user_id=user.id, protocol=protocol, public_key=public_key, private_key=private_key, endpoint=endpoint)
    db.add(acc)
    await db.commit()
    await db.refresh(acc)
    return acc

async def list_user_accounts(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[models.VPNAccount]:
    result = await db.execute(select(models.VPNAccount).where(models.VPNAccount.user_id == user_id).offset(skip).limit(limit))
    return list(result.scalars().all())

async def get_account(db: AsyncSession, account_id: int) -> Optional[models.VPNAccount]:
    result = await db.execute(select(models.VPNAccount).where(models.VPNAccount.id == account_id))
    return result.scalar_one_or_none()

