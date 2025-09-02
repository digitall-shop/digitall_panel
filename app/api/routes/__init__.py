from fastapi import APIRouter
from . import auth, users, accounts

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(users.router, prefix="/users")
api_router.include_router(accounts.router, prefix="/accounts")

