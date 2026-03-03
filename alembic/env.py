"""
Alembic Environment Configuration - Supports SQLite & PostgreSQL

Automatically detects database type from DATABASE_URL environment variable.
Uses synchronous drivers for migrations (Alembic requirement).
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.infrastructure.database.models import Base, TransactionModel, PaymentDetailModel
from src.infrastructure.database.user_model import UserModel  # noqa: F401
from pathlib import Path

# Alembic Config object
config = context.config

# Determine database URL (supports both SQLite and PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL.startswith("postgresql"):
    # PostgreSQL: ensure sync driver for Alembic
    sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    sync_url = sync_url.replace("postgresql+psycopg2://", "postgresql://")
    # Use psycopg2 sync driver
    if "psycopg2" not in sync_url and "+asyncpg" not in sync_url:
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://")
    else:
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    config.set_main_option("sqlalchemy.url", sync_url)
else:
    # SQLite (default)
    DATA_DIR = Path("data")
    DATA_DIR.mkdir(exist_ok=True)
    if DATABASE_URL and DATABASE_URL.startswith("sqlite"):
        sync_url = DATABASE_URL.replace("sqlite+aiosqlite:///", "sqlite:///")
        config.set_main_option("sqlalchemy.url", sync_url)
    else:
        config.set_main_option("sqlalchemy.url", f"sqlite:///{DATA_DIR}/nextrack.db")

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with sync engine."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
