"""Database fixtures.

Schema tests run the real Alembic migration against a dedicated `<db>_test` database on the
Postgres from docker-compose (or the CI service). They skip if Postgres is unreachable.
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
from alembic.config import Config
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from alembic import command
from app.core.config import settings

API_DIR = Path(__file__).resolve().parent.parent
BASE_URL = make_url(settings.database_url)
TEST_URL = BASE_URL.set(database=f"{BASE_URL.database}_test")


async def _ensure_test_db() -> None:
    conn = await asyncpg.connect(
        user=BASE_URL.username,
        password=BASE_URL.password,
        host=BASE_URL.host,
        port=BASE_URL.port or 5432,
        database=BASE_URL.database,
        timeout=3,
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", TEST_URL.database
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{TEST_URL.database}"')
    finally:
        await conn.close()


def alembic_config() -> Config:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "alembic"))
    # ConfigParser treats % as interpolation, so escape it in the URL.
    cfg.set_main_option(
        "sqlalchemy.url", TEST_URL.render_as_string(hide_password=False).replace("%", "%%")
    )
    return cfg


@pytest.fixture(scope="session")
def migrated_db() -> str:
    """Create the test database and run the migration from scratch. Sync on purpose:
    alembic/env.py calls asyncio.run, which cannot run inside a running event loop."""
    try:
        asyncio.run(_ensure_test_db())
    except (OSError, asyncpg.PostgresError, TimeoutError) as exc:
        pytest.skip(f"Postgres not reachable at {BASE_URL.host}:{BASE_URL.port}: {exc}")
    cfg = alembic_config()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    return TEST_URL.render_as_string(hide_password=False)


@pytest.fixture
async def conn(migrated_db: str) -> AsyncIterator[AsyncConnection]:
    """A connection inside a transaction that is rolled back after each test."""
    engine = create_async_engine(migrated_db)
    async with engine.connect() as connection:
        trans = await connection.begin()
        try:
            yield connection
        finally:
            await trans.rollback()
    await engine.dispose()
