import asyncio
import sys
from logging.config import fileConfig

# asyncpg is incompatible with ProactorEventLoop (Windows default in Python 3.8+).
# Switch to SelectorEventLoop so that asyncpg connections work correctly.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Import Base and models so Alembic can detect table metadata
from app.core.config import settings
from app.core.database import Base
import app.models.db_models  # noqa: F401 — registers ORM models with Base.metadata

# Alembic Config object
config = context.config

# Override sqlalchemy.url with the value from our Settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live database connection (generates SQL script)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations through a sync connection."""
    # Pass ssl=False explicitly via connect_args to avoid SSL negotiation errors
    # on Docker-hosted PostgreSQL (which has no SSL configured by default).
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"ssl": False},
    )
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
