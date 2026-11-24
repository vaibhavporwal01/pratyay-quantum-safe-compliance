import time

from fastapi import APIRouter
from sqlalchemy import text

from app.core.db import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """No database call, so pinging this keeps the API awake without waking the database."""
    return {"api": "up"}


@router.get("/health/db")
async def health_db() -> dict:
    t0 = time.perf_counter()
    async with engine.connect() as conn:
        version = (await conn.execute(text("select version()"))).scalar()
    return {"api": "up", "db": "up", "ms": round((time.perf_counter() - t0) * 1000), "version": version}
