from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models
from app.core.security import get_password_hash, verify_password
from typing import Optional

async def get_by_username(db: AsyncSession, username: str) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.username == username))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, username: str, password: str, is_superuser: bool = False) -> models.User:
    user = models.User(username=username, password_hash=get_password_hash(password), is_superuser=is_superuser)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def authenticate(db: AsyncSession, username: str, password: str) -> Optional[models.User]:
    user = await get_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

