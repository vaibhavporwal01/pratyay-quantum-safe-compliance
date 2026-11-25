"""Current user and role checks (contract in docs/contracts.md, owned by Vishnukant).

The `pratyay_session` cookie is the source of truth: a live session gives its user. Only when
there is no live session, and only in development (APP_ENV=development) or with
ALLOW_ROLE_SWITCHER=true, does the "Act as" stand-in apply: the seeded Lender A user for the
role in the `pratyay_dev_role` cookie, falling back to DEV_USER_ROLE. Otherwise: 401.
"""

import logging
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.db import SessionLocal
from app.identity import service
from app.identity.models import ROLES

log = logging.getLogger("pratyay.stub")

DEV_ROLE_COOKIE = "pratyay_dev_role"
SESSION_COOKIE = "pratyay_session"
_dev_role: ContextVar[str | None] = ContextVar("pratyay_dev_role", default=None)
_session_token: ContextVar[str | None] = ContextVar("pratyay_session", default=None)

__all__ = [
    "DEV_ROLE_COOKIE", "ROLES", "SESSION_COOKIE", "User", "get_current_user", "require_role",
    "stand_in_enabled",
]


@dataclass
class User:
    id: UUID
    org_id: UUID
    role: str
    name: str


async def identity_cookie_middleware(request: Request, call_next):
    """Carry the session and role cookies to get_current_user without changing its signature."""
    role = _dev_role.set(request.cookies.get(DEV_ROLE_COOKIE))
    sess = _session_token.set(request.cookies.get(SESSION_COOKIE))
    try:
        return await call_next(request)
    finally:
        _session_token.reset(sess)
        _dev_role.reset(role)


def stand_in_enabled() -> bool:
    """The cookie stand-in works in development, or anywhere ALLOW_ROLE_SWITCHER is true."""
    return settings.app_env == "development" or settings.allow_role_switcher


def dev_role() -> str | None:
    """The role the stand-in signs in as, or None when the stand-in is off."""
    if not stand_in_enabled():
        return None
    for role in (_dev_role.get(), settings.dev_user_role):
        if role in ROLES:
            return role
    return None


async def session_user() -> User | None:
    """The user of the live session in the request's cookie, or None."""
    token = _session_token.get()
    if not token:
        return None
    async with SessionLocal() as session:
        row = await service.user_for_token(session, token)
        await session.commit()
    return None if row is None else User(row.id, row.org_id, row.role, row.name)


async def get_current_user() -> User:
    """The signed-in user. A real session always wins over the stand-in."""
    if (user := await session_user()) is not None:
        return user
    role = dev_role()
    if role is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.")
    log.warning("STUB get_current_user as %s", role)
    async with SessionLocal() as session:
        row = await service.first_user_with_role(session, role)
    if row is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"No {role} user exists. Run: uv run python -m app.rules.seed",
        )
    return User(row.id, row.org_id, row.role, row.name)


def require_role(*roles: str):
    unknown = set(roles) - set(ROLES)
    if unknown:
        raise ValueError(f"unknown roles {sorted(unknown)}")

    async def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"This needs the {' or '.join(roles)} role."
            )
        return user

    return checker
