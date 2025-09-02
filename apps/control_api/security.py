import os
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID as UUIDCls
from packages.common.vpnpanel_common.db.models import User, Role, Membership
from .db import get_session

ph = PasswordHasher(time_cost=2, memory_cost=51200, parallelism=2, hash_len=32, salt_len=16)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
SECRET_KEY = os.getenv("SECRET_KEY", "devsecret")
ALGORITHM = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

class TokenData:
    def __init__(self, user_id: str | None = None):
        self.user_id = user_id

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, password)
    except Exception:
        return False

def create_access_token(data: dict, expires_minutes: int | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)) -> User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_raw: str = payload.get("sub")
        if user_id_raw is None:
            raise credentials_exception
        user_uuid = UUIDCls(user_id_raw)
    except Exception:
        raise credentials_exception
    result = await session.execute(select(User).where(User.id == user_uuid))
    user = result.scalars().first()
    if not user or not user.is_active:
        raise credentials_exception
    return user

async def require_role(role_name: str, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> User:
    if role_name == "any":
        return current_user
    q = (
        select(Role.name)
        .join(Membership, Role.id == Membership.role_id)
        .where(Membership.user_id == current_user.id, Role.name == role_name)
    )
    res = await session.execute(q)
    if res.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Insufficient role")
    return current_user

async def require_admin(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> User:
    roles_count = (await session.execute(select(func.count()).select_from(Role))).scalar() or 0
    memb_count = (await session.execute(select(func.count()).select_from(Membership))).scalar() or 0
    if roles_count == 0 or memb_count == 0:
        return current_user
    q = (
        select(Role.name)
        .join(Membership, Role.id == Membership.role_id)
        .where(Membership.user_id == current_user.id, Role.name == 'admin')
    )
    res = await session.execute(q)
    if res.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user
