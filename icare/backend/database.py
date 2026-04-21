"""Async SQLAlchemy engine and session (Supabase PostgreSQL via asyncpg)."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
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
