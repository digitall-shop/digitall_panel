from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from packages.common.vpnpanel_common.db.base import Base
from packages.common.vpnpanel_common.db import models  # noqa: F401

# Prefer explicit control API var, then unified SQLALCHEMY_DATABASE_URL, then legacy DATABASE_URL, finally sqlite fallback.
DATABASE_URL = (
    os.getenv("CONTROL_API_DATABASE_URL")
    or os.getenv("SQLALCHEMY_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or "sqlite+aiosqlite:///./control_api.db"
)

engine = create_async_engine(DATABASE_URL, future=True, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():  # pragma: no cover
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
