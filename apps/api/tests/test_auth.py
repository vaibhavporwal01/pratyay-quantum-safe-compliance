"""Email and password sign-in, sessions, lockout, sign-out, role checks and the CSRF guard."""

import uuid
from contextlib import asynccontextmanager
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import csrf
from app.core.db import get_session
from app.identity import deps, service
from app.identity import seed as identity_seed
from app.identity.models import Session as SessionRow
from app.identity.models import User as UserRow
from app.main import app

# A throwaway test value, not a real password.
PASSWORD = "test-only-correct-horse"
JSON = {"Content-Type": "application/json"}


@pytest.fixture
async def officer(session: AsyncSession) -> UserRow:
    u = UserRow(org_id=uuid.uuid4(), email=f"officer.{uuid.uuid4().hex[:8]}@example.test",
                name="Test Officer", role="officer",
                password_hash=service.hash_password(PASSWORD))
    session.add(u)
    await session.flush()
    return u


@pytest.fixture
async def client(session: AsyncSession, monkeypatch):
    """HTTP client on the rolled-back test session, with the stand-in switched off."""

    async def _session():
        yield session

    @asynccontextmanager
    async def _local():
        yield session

    monkeypatch.setattr(deps, "SessionLocal", _local)
    monkeypatch.setattr(deps.settings, "app_env", "production")
    monkeypatch.setattr(deps.settings, "allow_role_switcher", False)
    app.dependency_overrides[get_session] = _session
    # https so the Secure cookie set in production is sent back.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as c:
        yield c
    app.dependency_overrides.clear()


async def sign_in(c: AsyncClient, email: str, password: str = PASSWORD):
    return await c.post("/api/identity/sign-in", json={"email": email, "password": password})


async def stored_session(session: AsyncSession, user: UserRow) -> SessionRow:
    return await session.scalar(select(SessionRow).where(SessionRow.user_id == user.id))


def test_passwords_are_argon2id_and_verify() -> None:
    h = service.hash_password(PASSWORD)
    assert h.startswith("$argon2id$") and PASSWORD not in h
    assert service.verify_password(h, PASSWORD)
    assert not service.verify_password(h, "wrong")
    assert not service.verify_password(None, PASSWORD)
    assert not service.verify_password("not-a-hash", PASSWORD)


async def test_sign_in_sets_a_session_cookie_and_me_reads_it(client, session, officer) -> None:
    r = await sign_in(client, officer.email.upper())
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == "officer"
    cookie = r.headers["set-cookie"]
    assert cookie.startswith(f"{deps.SESSION_COOKIE}=")
    for attr in ("HttpOnly", "SameSite=lax", "Secure", "Path=/"):
        assert attr.lower() in cookie.lower()
    # Only the SHA-256 of the token is stored.
    token = client.cookies.get(deps.SESSION_COOKIE)
    row = await stored_session(session, officer)
    assert row.token_sha256 == service.token_hash(token) and len(row.token_sha256) == 32
    assert row.expires_at - row.created_at <= timedelta(hours=12, seconds=1)

    me = await client.get("/api/v1/me")
    assert me.status_code == 200 and me.json()["name"] == "Test Officer"


async def test_cookie_is_not_secure_outside_production(client, officer, monkeypatch) -> None:
    monkeypatch.setattr(deps.settings, "app_env", "staging")
    r = await sign_in(client, officer.email)
    assert "secure" not in r.headers["set-cookie"].lower()


async def test_unknown_email_and_wrong_password_give_the_same_error(client, officer) -> None:
    wrong = await sign_in(client, officer.email, "not-the-password")
    unknown = await sign_in(client, "nobody@example.test")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": service.SIGN_IN_FAILED}
    assert "set-cookie" not in wrong.headers


async def test_five_failures_lock_the_account_for_15_minutes(client, session, officer) -> None:
    for _ in range(5):
        assert (await sign_in(client, officer.email, "nope")).status_code == 401
    await session.refresh(officer)
    assert officer.locked_until is not None
    left = officer.locked_until - service.now()
    assert timedelta(minutes=14) < left <= timedelta(minutes=15)
    # Even the right password is refused while locked, with the same message.
    r = await sign_in(client, officer.email)
    assert r.status_code == 401 and r.json()["detail"] == service.SIGN_IN_FAILED
    # After the lock ends, the right password works and the counter is cleared.
    officer.locked_until = service.now() - timedelta(seconds=1)
    await session.flush()
    assert (await sign_in(client, officer.email)).status_code == 200
    await session.refresh(officer)
    assert officer.failed_attempts == 0 and officer.locked_until is None


async def test_four_failures_then_success_does_not_lock(client, session, officer) -> None:
    for _ in range(4):
        await sign_in(client, officer.email, "nope")
    assert (await sign_in(client, officer.email)).status_code == 200


async def test_idle_timeout_ends_the_session(client, session, officer) -> None:
    await sign_in(client, officer.email)
    row = await stored_session(session, officer)
    row.last_seen_at = service.now() - timedelta(minutes=15, seconds=1)
    await session.flush()
    assert (await client.get("/api/v1/me")).status_code == 401
    assert await stored_session(session, officer) is None


async def test_activity_keeps_the_session_alive(client, session, officer) -> None:
    await sign_in(client, officer.email)
    row = await stored_session(session, officer)
    row.last_seen_at = service.now() - timedelta(minutes=14)
    await session.flush()
    assert (await client.get("/api/v1/me")).status_code == 200
    await session.refresh(row)
    assert service.now() - row.last_seen_at < timedelta(minutes=1)


async def test_absolute_expiry_ends_the_session(client, session, officer) -> None:
    await sign_in(client, officer.email)
    row = await stored_session(session, officer)
    row.expires_at = service.now() - timedelta(seconds=1)
    await session.flush()
    assert (await client.get("/api/v1/me")).status_code == 401


async def test_sign_out_deletes_the_session(client, session, officer) -> None:
    await sign_in(client, officer.email)
    token = client.cookies.get(deps.SESSION_COOKIE)
    r = await client.post("/api/identity/sign-out", json={})
    assert r.status_code == 204
    assert await stored_session(session, officer) is None
    # The old token no longer works, even if a client kept it.
    client.cookies.set(deps.SESSION_COOKIE, token)
    assert (await client.get("/api/v1/me")).status_code == 401


async def test_role_guard_gives_403_to_a_signed_in_user(client, officer) -> None:
    await sign_in(client, officer.email)
    assert (await client.get("/api/v1/admin/users")).status_code == 403
    # The rule library is for maker, checker, auditor and admin.
    assert (await client.get("/api/v1/rules/library")).status_code == 403


async def test_switcher_cookie_is_ignored_when_off(client) -> None:
    client.cookies.set(deps.DEV_ROLE_COOKIE, "admin")
    assert (await client.get("/api/v1/me")).status_code == 401


async def test_switcher_never_overrides_a_real_session(client, officer, monkeypatch) -> None:
    monkeypatch.setattr(deps.settings, "allow_role_switcher", True)
    await sign_in(client, officer.email)
    client.cookies.set(deps.DEV_ROLE_COOKIE, "admin")
    me = await client.get("/api/v1/me")
    assert me.json()["role"] == "officer"


async def test_inactive_user_cannot_sign_in(client, session, officer) -> None:
    officer.active = False
    await session.flush()
    assert (await sign_in(client, officer.email)).status_code == 401


# ---- CSRF guard -------------------------------------------------------------------------


async def test_state_changing_requests_must_be_json(client) -> None:
    r = await client.post("/api/identity/sign-in", content="email=a&password=b",
                          headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 415
    r = await client.post("/api/identity/sign-out")
    assert r.status_code == 415
    # Reads are not affected.
    assert (await client.get("/health")).status_code == 200


async def test_pdf_upload_needs_the_site_origin(client, monkeypatch) -> None:
    monkeypatch.setattr(csrf.settings, "allowed_origin", "https://pratyay.example")
    files = {"file": ("a.pdf", b"%PDF-1.4", "application/pdf")}
    r = await client.post("/api/v1/rules/sources", files=files,
                          headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    r = await client.post("/api/v1/rules/sources", files=files)
    assert r.status_code == 403
    # Right origin: past the guard (then 401, nobody is signed in).
    r = await client.post("/api/v1/rules/sources", files=files,
                          headers={"Origin": "https://pratyay.example"})
    assert r.status_code == 401


# ---- seed password ----------------------------------------------------------------------


def test_seed_password_is_required(monkeypatch) -> None:
    monkeypatch.setattr(identity_seed.settings, "seed_password", None)
    with pytest.raises(identity_seed.SeedPasswordError, match="SEED_PASSWORD is not set"):
        identity_seed.seed_password()
    monkeypatch.setattr(identity_seed.settings, "seed_password", "short")
    with pytest.raises(identity_seed.SeedPasswordError):
        identity_seed.seed_password()


async def test_seed_sets_passwords_and_prints_no_secret(session, capsys) -> None:
    await service.seed_dev_users(session)
    users = await identity_seed.seed_passwords(session, PASSWORD)
    identity_seed.print_users(users)
    out = capsys.readouterr().out
    assert PASSWORD not in out
    assert len(users) == 6 and all(e in out for e, _ in users)
    row = await session.scalar(select(UserRow).where(UserRow.email == users[0][0]))
    assert service.verify_password(row.password_hash, PASSWORD)
