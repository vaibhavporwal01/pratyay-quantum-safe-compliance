"""Passwords for the six seeded Lender A users.

The password comes only from SEED_PASSWORD in the environment. It is never committed, logged
or printed; the seed prints each user's email and role only.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.identity import service

MIN_LENGTH = 12
MISSING = (
    "SEED_PASSWORD is not set. Set it in the environment (or .env) to the password the six "
    f"seeded users will sign in with, at least {MIN_LENGTH} characters, then run the seed again."
)
TOO_SHORT = f"SEED_PASSWORD must be at least {MIN_LENGTH} characters."


class SeedPasswordError(RuntimeError):
    pass


def seed_password() -> str:
    """SEED_PASSWORD from the environment (or .env). Raises with a clear message."""
    value = settings.seed_password
    if not value:
        raise SeedPasswordError(MISSING)
    if len(value) < MIN_LENGTH:
        raise SeedPasswordError(TOO_SHORT)
    return value


async def seed_passwords(session: AsyncSession, password: str) -> list[tuple[str, str]]:
    """Set the password on the seeded users. Returns (email, role) for each, for printing."""
    users = [(email, role) for role, (_, email) in service.DEV_USERS.items()]
    await service.set_passwords(session, [e for e, _ in users], password)
    return users


def print_users(users: list[tuple[str, str]]) -> None:
    print("Seeded users (password from SEED_PASSWORD):")
    for email, role in users:
        print(f"  {role:<9} {email}")
