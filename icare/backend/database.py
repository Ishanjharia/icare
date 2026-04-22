"""Async SQLAlchemy engine and session (Supabase PostgreSQL via asyncpg).

Supabase Transaction pooler: disable asyncpg statement caching and SQLAlchemy's
asyncpg prepared-statement cache, or you can see "prepared statement does not exist"
when connections move between pooler backends. ``statement_cache_size=0`` is passed
to asyncpg via ``connect_args``; ``prepared_statement_cache_size=0`` is a
SQLAlchemy dialect option on ``create_async_engine`` (not an asyncpg connect kwarg).
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings


def _require_database_url() -> str:
    raw = (settings.DATABASE_URL or "").strip()
    if not raw:
        raise RuntimeError(
            "DATABASE_URL is not set. Use postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB "
            "and URL-encode special characters in the password (e.g. @ → %40, [ → %5B, ] → %5D)."
        )
    return raw


def normalize_database_url_for_asyncpg(url: str) -> str:
    """
    Ensure SQLAlchemy uses the asyncpg async driver (postgresql+asyncpg://).

    Accepts common variants (postgresql://, postgres://, postgresql+psycopg2://, …)
    and rewrites them to postgresql+asyncpg://. Other schemes (e.g. sqlite) are unchanged.
    """
    u = url.strip()
    if u.startswith("postgresql+asyncpg://"):
        return u
    if "://" not in u:
        return f"postgresql+asyncpg://{u}"
    scheme, _, remainder = u.partition("://")
    if not remainder:
        return u
    lower = scheme.lower()
    if lower in ("postgres", "postgresql") or lower.startswith("postgresql+"):
        return f"postgresql+asyncpg://{remainder}"
    return u


def ensure_asyncpg_ssl_query(url: str) -> str:
    """Append ssl=require for Supabase / common cloud hosts if not already set (asyncpg + TLS)."""
    u = url.strip()
    if not u.startswith("postgresql+asyncpg://"):
        return u
    lower = u.lower()
    if "ssl=" in lower or "sslmode=" in lower:
        return u
    if "supabase.co" in lower or "supabase.com" in lower or ".pooler.supabase.com" in lower:
        joiner = "&" if "?" in u else "?"
        return f"{u}{joiner}ssl=require"
    return u


_ASYNC_DATABASE_URL = ensure_asyncpg_ssl_query(
    normalize_database_url_for_asyncpg(_require_database_url()),
)


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


def _asyncpg_connect_args(url: str) -> dict:
    """asyncpg options; SSL required for Supabase pooler / TLS hosts, optional for local Postgres."""
    lower = url.lower()
    need_ssl = (
        "supabase.co" in lower
        or "supabase.com" in lower
        or ".pooler.supabase.com" in lower
        or "ssl=require" in lower
        or "sslmode=require" in lower
    )
    args: dict = {"statement_cache_size": 0}
    if need_ssl:
        args["ssl"] = "require"
    return args


# postgresql+asyncpg:// in the URL selects the asyncpg driver (see normalize_database_url_for_asyncpg).
engine = create_async_engine(
    _ASYNC_DATABASE_URL,
    echo=False,
    future=True,
    pool_size=3,
    max_overflow=5,
    pool_recycle=300,
    pool_pre_ping=True,
    prepared_statement_cache_size=0,
    connect_args=_asyncpg_connect_args(_ASYNC_DATABASE_URL),
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    """Import models and create all tables (development bootstrap; prefer Alembic in prod)."""
    from models import (  # noqa: F401
        alert,
        appointment,
        health_profile,
        health_record,
        medication,
        patient_vitals_threshold,
        prescription,
        saved_hospital,
        user,
        vitals_queue,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
