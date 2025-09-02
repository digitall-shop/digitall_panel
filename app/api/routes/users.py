from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.db.database import get_db
from app import models
from app.schemas import UserRead

router = APIRouter(tags=["users"], dependencies=[Depends(deps.get_current_active_superuser)])

@router.get("/", response_model=list[UserRead])
async def list_users(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    return list(result.scalars().all())

@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

