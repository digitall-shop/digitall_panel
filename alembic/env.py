import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
import os

from packages.common.vpnpanel_common.db.base import Base  # noqa: F401
from packages.common.vpnpanel_common.db import models  # noqa: F401

# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def get_url():
    return os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))

# target metadata for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    connectable = create_async_engine(get_url(), poolclass=pool.NullPool)

    async with connectable.connect() as connection:  # type: ignore
        await connection.run_sync(lambda sync_conn: context.configure(
            connection=sync_conn,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        ))

        async with connection.begin():
            await connection.run_sync(do_run_migrations)

async def do_run_migrations(connection: Connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

def run():
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_migrations_online())

run()

