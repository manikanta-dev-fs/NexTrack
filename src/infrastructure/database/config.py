"""
Database Configuration - Dual Support (SQLite + PostgreSQL)

Automatically detects database type from DATABASE_URL:
- SQLite (default): No setup needed, great for local development
- PostgreSQL: Production-grade, used in Docker deployment
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
import os
from pathlib import Path

# Database URL from environment (supports both SQLite and PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Auto-detect database type and configure accordingly
if DATABASE_URL.startswith("postgresql"):
    # PostgreSQL: convert to async driver if needed
    if "asyncpg" not in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )
else:
    # SQLite (default for local development)
    DATA_DIR = Path("data")
    DATA_DIR.mkdir(exist_ok=True)
    
    if not DATABASE_URL:
        DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR}/nextrack.db"
    elif DATABASE_URL.startswith("sqlite:///"):
        DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
    )

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for all models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to inject database sessions.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """Drop all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
