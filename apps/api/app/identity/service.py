"""identity: service. Owned by Vishnukant (docs/contracts.md).

Users, Argon2id passwords, sign-in with lockout, and server-side sessions. The browser holds a
random 32-byte token; the database holds only its SHA-256. A session ends after
SESSION_IDLE_MINUTES without a request, or SESSION_ABSOLUTE_HOURS after sign-in.
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.identity.models import ROLES, User
from app.identity.models import Session as SessionRow

_hasher = PasswordHasher()  # Argon2id with argon2-cffi's recommended parameters.
# Verified when the email is unknown, so both failures take about the same time.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))
SIGN_IN_FAILED = "Email or password is incorrect."

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


# ---- passwords -----------------------------------------------------------------------------


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and bool(password_hash)
    except (VerificationError, InvalidHashError):
        return False


async def set_passwords(session: AsyncSession, emails: list[str], password: str) -> int:
    """Set one password on the given users (the seed). Returns users updated."""
    rows = (await session.scalars(select(User).where(User.email.in_(emails)))).all()
    for u in rows:
        u.password_hash = hash_password(password)
        u.failed_attempts = 0
        u.locked_until = None
    await session.flush()
    return len(rows)


# ---- sign-in -------------------------------------------------------------------------------


def now() -> datetime:
    return datetime.now(UTC)


def token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


@dataclass
class SignIn:
    """ok: token and user are set. Otherwise user is the account that failed, if any."""

    ok: bool
    user: User | None = None
    token: str | None = None
    locked: bool = False


async def sign_in(session: AsyncSession, email: str, password: str) -> SignIn:
    """Check the password and open a session. The caller commits and shows one generic error
    for every failure."""
    user = await session.scalar(
        select(User).where(func.lower(User.email) == email.strip().lower())
    )
    t = now()
    if user is None:
        verify_password(None, password)
        return SignIn(False)
    if user.locked_until is not None and user.locked_until > t:
        verify_password(None, password)
        return SignIn(False, user, locked=True)
    if not user.active or not verify_password(user.password_hash, password):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        locked = user.failed_attempts >= settings.lockout_attempts
        if locked:
            user.locked_until = t + timedelta(minutes=settings.lockout_minutes)
            user.failed_attempts = 0
        await session.flush()
        return SignIn(False, user, locked=locked)
    user.failed_attempts = 0
    user.locked_until = None
    token = secrets.token_urlsafe(32)
    session.add(SessionRow(
        token_sha256=token_hash(token), user_id=user.id, last_seen_at=t,
        expires_at=t + timedelta(hours=settings.session_absolute_hours),
    ))
    await session.flush()
    return SignIn(True, user, token)


async def user_for_token(session: AsyncSession, token: str) -> User | None:
    """The user behind a live session, touching last_seen_at. An expired session is deleted."""
    row = await session.scalar(
        select(SessionRow).where(SessionRow.token_sha256 == token_hash(token))
    )
    if row is None:
        return None
    t = now()
    idle = timedelta(minutes=settings.session_idle_minutes)
    if row.expires_at <= t or row.last_seen_at + idle <= t:
        await session.delete(row)
        await session.flush()
        return None
    user = await session.get(User, row.user_id)
    if user is None or not user.active:
        return None
    row.last_seen_at = t
    await session.flush()
    return user


async def sign_out(session: AsyncSession, token: str) -> uuid.UUID | None:
    """Delete the session. Returns its user id, or None if there was none."""
    row = await session.scalar(
        select(SessionRow).where(SessionRow.token_sha256 == token_hash(token))
    )
    if row is None:
        return None
    await session.execute(delete(SessionRow).where(SessionRow.id == row.id))
    return row.user_id
