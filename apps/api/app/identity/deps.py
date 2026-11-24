"""Current user and role checks (contract in docs/contracts.md, owned by Vishnukant).

STUB until the identity module lands. There is no sign-in yet: in development
(APP_ENV=development) the user is the seeded Lender A user for the role in the
`pratyay_dev_role` cookie, falling back to DEV_USER_ROLE. Anywhere else every request is
unauthenticated.
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
_dev_role: ContextVar[str | None] = ContextVar("pratyay_dev_role", default=None)

__all__ = ["DEV_ROLE_COOKIE", "ROLES", "User", "get_current_user", "require_role"]


@dataclass
class User:
    id: UUID
    org_id: UUID
    role: str
    name: str


async def dev_role_middleware(request: Request, call_next):
    """Carry the development role cookie to get_current_user without changing its signature."""
    token = _dev_role.set(request.cookies.get(DEV_ROLE_COOKIE))
    try:
        return await call_next(request)
    finally:
        _dev_role.reset(token)


def dev_role() -> str | None:
    """The role the development stand-in signs in as, or None outside development."""
    if settings.app_env != "development":
        return None
    for role in (_dev_role.get(), settings.dev_user_role):
        if role in ROLES:
            return role
    return None


async def get_current_user() -> User:
    """STUB until Vishnukant's identity module lands (see docs/contracts.md)."""
    role = dev_role()
    if role is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign-in is not available yet.")
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
