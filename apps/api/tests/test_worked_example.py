"""The public worked example: no sign-in, engine figures, saves nothing, cached."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.db import get_session
from app.loans import example
from app.loans.models import Application, Evaluation
from app.main import app
from tests.rule_fixtures import add_rule_set


@pytest.fixture
async def client(session):
    async def _session():
        yield session

    example.clear()
    await add_rule_set(session)
    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    example.clear()


def rule(ev: dict, code: str) -> dict:
    return next(r for r in ev["results"] if r["code"] == code)


async def test_worked_example_is_public_and_from_the_engine(client, session) -> None:
    before = await session.scalar(select(func.count()).select_from(Evaluation))
    apps = await session.scalar(select(func.count()).select_from(Application))
    r = await client.get("/api/v1/loans/worked-example")
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "public, max-age=300"
    body = r.json()
    assert body["ref"] == "APP-2026-0142"
    asked, at_offer = body["asked"], body["at_offer"]
    assert asked["outcome"] == "fail"
    assert rule(asked, "MF-02")["values"]["ratio_percent"] == "53.3"
    assert rule(asked, "MF-02")["values"]["e_max"] == "₹3,500"
    assert rule(asked, "MF-02")["values"]["l_max"] == "₹66,198.74"
    assert asked["offer"]["amount_paise"] == 66_000_00
    assert at_offer["outcome"] == "pass"
    assert rule(at_offer, "MF-02")["values"]["ratio_percent"] == "49.95"
    assert at_offer["kfs"]["emi_paise"] == 3_489_00
    assert at_offer["kfs"]["apr_percent"] == "25.07"
    # Nothing saved.
    assert await session.scalar(select(func.count()).select_from(Evaluation)) == before
    assert await session.scalar(select(func.count()).select_from(Application)) == apps


async def test_worked_example_is_cached_for_five_minutes(client, session, monkeypatch) -> None:
    calls = []
    real = example.build

    async def counting(s):
        calls.append(1)
        return await real(s)

    monkeypatch.setattr(example, "build", counting)
    first = await example.cached(session, now=1000.0)
    again = await example.cached(session, now=1000.0 + 299)
    assert again is first and len(calls) == 1
    await example.cached(session, now=1000.0 + 301)
    assert len(calls) == 2
