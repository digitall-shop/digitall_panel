from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.routes import api_router
from app.core.config import get_settings
from app.db.database import engine, Base, AsyncSessionLocal
from sqlalchemy import select
from app import models
from app.crud import user as crud_user

settings = get_settings()

@asynccontextmanager
def lifespan(app: FastAPI):
    # Startup: create tables and bootstrap first superuser
    async with engine.begin() as conn:  # type: ignore
        await conn.run_sync(Base.metadata.create_all)
    if settings.first_superuser and settings.first_superuser_password:
        async with AsyncSessionLocal() as session:  # type: ignore
            result = await session.execute(select(models.User).where(models.User.username == settings.first_superuser))
            su = result.scalar_one_or_none()
            if not su:
                await crud_user.create_user(session, settings.first_superuser, settings.first_superuser_password, is_superuser=True)
    yield
    # Shutdown: nothing yet

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router, prefix=settings.api_v1_prefix)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

