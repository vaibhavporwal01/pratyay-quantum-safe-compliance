import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401  (registers every module's tables)
from alembic import context
from app.core.config import settings
from app.core.db import Base

target_metadata = Base.metadata
SCHEMAS = ("rules", "origination", "decision", "identity", "loans", "audit", "trust")
# Tests override the URL via the Alembic config; otherwise read it from env settings.
DATABASE_URL = context.config.get_main_option("sqlalchemy.url") or settings.database_url


def include_name(name, type_, parent_names) -> bool:
    if type_ == "schema":
        return name in SCHEMAS
    return True


def run_offline() -> None:
    context.configure(url=DATABASE_URL, target_metadata=target_metadata,
                      literal_binds=True, include_schemas=True, include_name=include_name)
    with context.begin_transaction():
        context.run_migrations()


def _run(conn) -> None:
    context.configure(connection=conn, target_metadata=target_metadata, include_schemas=True,
                      include_name=include_name)
    with context.begin_transaction():
        context.run_migrations()


async def run_online() -> None:
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        await conn.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    run_offline()
else:
    asyncio.run(run_online())
