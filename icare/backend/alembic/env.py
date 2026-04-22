"""Alembic migration environment (async SQLAlchemy)."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from config import settings
from database import Base, normalize_database_url_for_asyncpg

# Import models so metadata is populated for autogenerate.
from models import alert  # noqa: F401
from models import appointment  # noqa: F401
from models import health_profile  # noqa: F401
from models import health_record  # noqa: F401
from models import medication  # noqa: F401
from models import patient_vitals_threshold  # noqa: F401
from models import prescription  # noqa: F401
from models import saved_hospital  # noqa: F401
from models import user  # noqa: F401
from models import vitals_queue  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_db_url = (settings.DATABASE_URL or "").strip()
if not _db_url:
    raise RuntimeError("DATABASE_URL is not set. Export DATABASE_URL before running Alembic.")
config.set_main_option("sqlalchemy.url", normalize_database_url_for_asyncpg(_db_url))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using async engine."""
    section = dict(config.get_section(config.config_ini_section) or {})
    section["sqlalchemy.url"] = normalize_database_url_for_asyncpg(_db_url)
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entrypoint used by Alembic CLI."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
