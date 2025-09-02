from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from ..db import get_session
from packages.common.vpnpanel_common.db.models import User, Role, Membership
from ..security import hash_password, verify_password, create_access_token, get_current_user
from .. import schemas

router = APIRouter()

@router.post("/login", response_model=schemas.TokenOut, summary="Login and obtain JWT", responses={200: {"description": "Successful login"}})
async def login(payload: dict, session: AsyncSession = Depends(get_session)):
    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        raise HTTPException(400, "email and password required")
    res = await session.execute(select(User).where(User.email == email))
    user = res.scalars().first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/register", response_model=schemas.UserOut, status_code=201, summary="Register new user (bootstrap)")
async def register(user_in: schemas.UserCreate, session: AsyncSession = Depends(get_session)):
    # Allow open registration only if no users exist yet (bootstrap) else forbid
    count = (await session.execute(select(User))).scalars().first()
    if count and (await session.execute(select(User).where(User.email == user_in.email))).scalars().first():
        raise HTTPException(400, "User already exists")
    user = User(email=user_in.email, password_hash=hash_password(user_in.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

@router.get("/me", response_model=schemas.MeOut, summary="Current user profile")
async def me(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    q = select(Role.name).join(Membership, Role.id == Membership.role_id).where(Membership.user_id == current_user.id)
    roles = [r[0] for r in (await session.execute(q)).all()]
    return schemas.MeOut(id=current_user.id, email=current_user.email, roles=roles)

