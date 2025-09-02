from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.database import get_db
from app.schemas import Token, UserCreate, UserRead
from app import models
from app.crud import user as crud_user
from app.api import deps

router = APIRouter(tags=["auth"])

@router.post("/token", response_model=Token)
async def login_for_access_token(db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = await crud_user.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")
    access_token = create_access_token(subject=user.username)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserRead, status_code=201)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await crud_user.get_by_username(db, user_in.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = await crud_user.create_user(db, user_in.username, user_in.password)
    return new_user

@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: models.User = Depends(deps.get_current_user)):
    return current_user

