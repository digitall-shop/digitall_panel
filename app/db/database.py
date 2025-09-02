from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.sqlalchemy_database_url, echo=False, pool_pre_ping=True, pool_recycle=1800)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

Base = declarative_base()

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:  # type: ignore
        yield session

