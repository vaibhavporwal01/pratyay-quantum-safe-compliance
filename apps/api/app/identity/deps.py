import logging

log = logging.getLogger("pratyay.stub")
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends

ROLES = ("borrower", "officer", "maker", "checker", "auditor", "admin")


@dataclass
class User:
    id: UUID
    org_id: UUID
    role: str
    name: str


async def get_current_user() -> User:
    """STUB until Vishnukant's identity module lands (see docs/contracts.md)."""
    log.warning("STUB get_current_user")
    return User(UUID(int=1), UUID(int=1), "officer", "Stub User")


def require_role(*roles: str):
    async def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        log.warning("STUB require_role %s", roles)
        return user
    return checker
