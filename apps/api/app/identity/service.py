"""identity: service. Owned by Vishnukant (docs/contracts.md).

Until his module lands this holds only what the development role stand-in needs: look users up
and seed one user per role for Lender A.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models import ROLES, User

# Lender A's org id, fixed so seeded data lines up across machines.
LENDER_A_ORG = uuid.uuid5(uuid.NAMESPACE_DNS, "lender-a.in")

DEV_USERS: dict[str, tuple[str, str]] = {
    "borrower": ("Rekha Kumari", "rekha.kumari@lender-a.in"),
    "officer": ("Anita Sharma", "anita.sharma@lender-a.in"),
    "maker": ("Neha Verma", "neha.verma@lender-a.in"),
    "checker": ("Rahul Mehta", "rahul.mehta@lender-a.in"),
    "auditor": ("Priya Nair", "priya.nair@lender-a.in"),
    "admin": ("Arjun Rao", "arjun.rao@lender-a.in"),
}
assert set(DEV_USERS) == set(ROLES)


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def first_user_with_role(session: AsyncSession, role: str) -> User | None:
    return await session.scalar(
        select(User).where(User.role == role).order_by(User.created_at, User.email).limit(1)
    )


async def list_users(session: AsyncSession, org_id: uuid.UUID) -> list[User]:
    rows = await session.scalars(
        select(User).where(User.org_id == org_id).order_by(User.role, User.name)
    )
    return list(rows)


async def user_names(session: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    ids = {i for i in ids if i is not None}
    if not ids:
        return {}
    rows = await session.execute(select(User.id, User.name).where(User.id.in_(ids)))
    return {r.id: r.name for r in rows}


async def seed_dev_users(session: AsyncSession) -> int:
    """Insert one Lender A user per role. Idempotent (keyed on email). Returns rows added."""
    stmt = (
        insert(User)
        .values(
            [
                {"org_id": LENDER_A_ORG, "email": email, "name": name, "role": role}
                for role, (name, email) in DEV_USERS.items()
            ]
        )
        .on_conflict_do_nothing(index_elements=["email"])
        .returning(User.id)
    )
    return len((await session.execute(stmt)).all())
