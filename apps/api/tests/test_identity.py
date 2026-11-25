"""Development role stand-in for get_current_user, and role checks."""

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.identity import deps
from app.identity.service import DEV_USERS, seed_dev_users
from app.main import app


@pytest.fixture
def fake_users(monkeypatch):
    """Users looked up by role without touching the development database."""

    async def first_user_with_role(session, role):
        return SimpleNamespace(id=uuid.uuid5(uuid.NAMESPACE_DNS, role), org_id=uuid.UUID(int=1),
                               role=role, name=DEV_USERS[role][0])

    monkeypatch.setattr(deps.service, "first_user_with_role", first_user_with_role)
    monkeypatch.setattr(deps.settings, "app_env", "development")
    monkeypatch.setattr(deps.settings, "dev_user_role", "maker")


async def test_cookie_picks_the_role(fake_users) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.cookies.set(deps.DEV_ROLE_COOKIE, "checker")
        r = await c.get("/api/v1/me")
        assert r.status_code == 200
        assert (r.json()["role"], r.json()["name"]) == ("checker", "Rahul Mehta")
        # No cookie: DEV_USER_ROLE.
        c.cookies.clear()
        r = await c.get("/api/v1/me")
        assert r.json()["role"] == "maker"


async def test_unknown_cookie_role_falls_back(fake_users) -> None:
    token = deps._dev_role.set("superuser")
    try:
        assert deps.dev_role() == "maker"
    finally:
        deps._dev_role.reset(token)


async def test_outside_development_nobody_is_signed_in(fake_users, monkeypatch) -> None:
    monkeypatch.setattr(deps.settings, "app_env", "production")
    monkeypatch.setattr(deps.settings, "allow_role_switcher", False)
    with pytest.raises(HTTPException) as exc:
        await deps.get_current_user()
    assert exc.value.status_code == 401


async def test_role_switcher_flag_allows_the_stand_in_outside_development(
    fake_users, monkeypatch
) -> None:
    monkeypatch.setattr(deps.settings, "app_env", "production")
    monkeypatch.setattr(deps.settings, "allow_role_switcher", True)
    token = deps._dev_role.set("checker")
    try:
        assert deps.dev_role() == "checker"
    finally:
        deps._dev_role.reset(token)


def test_neon_urls_become_asyncpg_urls() -> None:
    from app.core.config import asyncpg_url

    neon = ("postgresql://u:p@ep-x.ap-southeast-1.aws.neon.tech/neondb"
            "?sslmode=require&channel_binding=require")
    assert asyncpg_url(neon) == (
        "postgresql+asyncpg://u:p@ep-x.ap-southeast-1.aws.neon.tech/neondb?ssl=require"
    )
    assert asyncpg_url("postgres://u:p@h/db?ssl=require") == "postgresql+asyncpg://u:p@h/db?ssl=require"
    local = "postgresql+asyncpg://pratyay:pratyay@localhost:5432/pratyay"
    assert asyncpg_url(local) == local


async def test_require_role_refuses_other_roles() -> None:
    check = deps.require_role("checker")
    maker = deps.User(uuid.uuid4(), uuid.uuid4(), "maker", "Neha")
    with pytest.raises(HTTPException) as exc:
        await check(maker)
    assert exc.value.status_code == 403
    with pytest.raises(ValueError):
        deps.require_role("superuser")


async def test_seed_one_user_per_role_idempotent(session) -> None:
    from sqlalchemy import select

    from app.identity.models import User

    await seed_dev_users(session)
    assert await seed_dev_users(session) == 0
    rows = (await session.scalars(select(User).where(User.email.like("%@lender-a.in")))).all()
    assert sorted(u.role for u in rows) == sorted(deps.ROLES)
