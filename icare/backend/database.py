"""Async SQLAlchemy engine and session (PostgreSQL via asyncpg; Supabase Transaction pooler).

``statement_cache_size=0`` and ``prepared_statement_cache_size=0`` (the latter is consumed by
SQLAlchemy's asyncpg layer, not passed through to ``asyncpg.connect``) avoid pooler
"prepared statement does not exist" errors.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings


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


def resolve_async_database_url() -> str | None:
    """Build asyncpg URL from ``settings.DATABASE_URL`` (from env ``DATABASE_URL``)."""
    raw = (settings.DATABASE_URL or "").strip()
    if not raw:
        return None
    return ensure_asyncpg_ssl_query(normalize_database_url_for_asyncpg(raw))


def _connect_args_for_url(url: str) -> dict:
    """Pooler-safe caches; TLS for remote hosts (Render → Supabase), not typical local Postgres."""
    args: dict = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
    lower = url.lower()
    if "localhost" in lower or "127.0.0.1" in lower:
        return args
    args["ssl"] = "require"
    return args


_RESOLVED_URL = resolve_async_database_url()

if _RESOLVED_URL is None:
    engine = None
    async_session_factory = None
else:
    engine = create_async_engine(
        _RESOLVED_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args=_connect_args_for_url(_RESOLVED_URL),
    )
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    if async_session_factory is None:
        raise HTTPException(status_code=503, detail="Database is not configured")
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    """Import models and create all tables (development bootstrap; prefer Alembic in prod)."""
    if engine is None:
        raise RuntimeError(
            "DATABASE_URL is not set or empty. Set the DATABASE_URL environment variable on Render "
            "(e.g. postgresql+asyncpg://… from Supabase; URL-encode special characters in the password)."
        )
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
