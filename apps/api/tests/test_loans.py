"""Loan flow over HTTP: submit, engine snapshot, recommend, decide; roles and four eyes."""

import uuid
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.db import get_session
from app.identity.deps import User, get_current_user
from app.loans import service
from app.loans.models import Event
from app.main import app
from tests.helpers import ORG, user
from tests.rule_fixtures import add_rule_set

BORROWER = user("borrower", "Rekha K.")
OFFICER = user("officer", "Anita Sharma")
CHECKER = user("checker", "Rahul Mehta")
AUDITOR = user("auditor", "Priya Nair")
ADMIN = user("admin", "Arjun Rao")

REKHA = {
    "product": "MFL", "amount_paise": 80_000_00, "tenor_months": 24,
    "purpose": "Two sewing machines", "household_income_annual_paise": 2_64_000_00,
    "existing_monthly_repayments_paise": 7_500_00,
}


@pytest.fixture
async def api(session, monkeypatch):
    async def _session():
        yield session

    logged: list[tuple] = []

    async def _log(session, actor_id, action, target, meta=None):
        logged.append((actor_id, action, target))

    monkeypatch.setattr(service.audit, "log_event", _log)
    monkeypatch.setattr(service, "today", lambda: date(2026, 11, 25))
    await add_rule_set(session)
    current = {"user": BORROWER}
    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_current_user] = lambda: current["user"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.as_ = lambda u: current.update(user=u)  # type: ignore[attr-defined]
        c.logged = logged  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()


async def submit(api, who=BORROWER, **over):
    api.as_(who)
    r = await api.post("/api/v1/loans/applications", json={**REKHA, **over})
    assert r.status_code == 201, r.text
    return r.json()


async def test_full_flow_with_modified_amount(api, session) -> None:
    d = await submit(api)
    app_id = d["application"]["id"]
    assert d["application"]["status"] == "evaluated"
    assert d["application"]["borrower_id"] == str(BORROWER.id)
    ev = d["evaluation"]
    assert ev["outcome"] == "fail" and ev["offer"]["amount_paise"] == 66_000_00
    assert {r["code"] for r in ev["rules_used"]} >= {"MF-01", "MF-02", "KF-01"}
    assert all("version" in r for r in ev["rules_used"])

    # Approving at the amount asked for is refused: MF-02 fails.
    api.as_(OFFICER)
    r = await api.post(f"/api/v1/loans/applications/{app_id}/recommend",
                       json={"recommendation": "approve"})
    assert r.status_code == 409 and "MF-02" in r.json()["detail"]

    r = await api.post(f"/api/v1/loans/applications/{app_id}/recommend", json={
        "recommendation": "approve_modified", "amount_paise": 66_000_00, "note": "Fits MF-02"})
    assert r.status_code == 200, r.text
    assert r.json()["application"]["status"] == "recommended"

    api.as_(CHECKER)
    queue = (await api.get("/api/v1/loans/applications?status=recommended")).json()
    assert [a["ref"] for a in queue] == [d["application"]["ref"]]
    r = await api.post(f"/api/v1/loans/applications/{app_id}/decide",
                       json={"outcome": "approve", "note": "Agreed"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["application"]["status"] == "approved_modified"
    assert out["decision"]["approved_paise"] == 66_000_00
    assert out["decision"]["signature"] == "pending"
    assert out["decision"]["ledger_seq"] is None
    assert out["final_evaluation"]["outcome"] == "pass"
    assert out["final_evaluation"]["kfs"]["apr_percent"] == "25.07"
    # The latest evaluation shown is still the one at the amount asked for.
    assert out["evaluation"]["amount_paise"] == 80_000_00

    actions = [e["action"] for e in out["events"]]
    assert actions[0] == "submitted" and actions[-1] == "decided"
    assert "recommended" in actions
    assert ("loan.decided" in [a for _, a, _ in api.logged])

    # Final: no more steps.
    r = await api.post(f"/api/v1/loans/applications/{app_id}/decide", json={"outcome": "reject",
                                                                          "note": "x"})
    assert r.status_code == 409

    # The borrower sees the decision.
    api.as_(BORROWER)
    mine = (await api.get("/api/v1/loans/applications")).json()
    assert mine[0]["status"] == "approved_modified" and mine[0]["approved_paise"] == 66_000_00


async def test_officer_and_checker_must_differ(api, session) -> None:
    d = await submit(api, OFFICER, borrower_name="Sunita D.", amount_paise=30_000_00,
                     tenor_months=12)
    app_id = d["application"]["id"]
    assert d["evaluation"]["outcome"] == "pass"
    api.as_(OFFICER)
    r = await api.post(f"/api/v1/loans/applications/{app_id}/recommend",
                       json={"recommendation": "approve"})
    assert r.status_code == 200, r.text
    api.as_(User(OFFICER.id, ORG, "checker", OFFICER.name))
    r = await api.post(f"/api/v1/loans/applications/{app_id}/decide", json={"outcome": "approve"})
    assert r.status_code == 403 and "officer" in r.json()["detail"]

    # The database refuses it too.
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await session.execute(text(
                "UPDATE loans.decisions SET checker_id = officer_id WHERE application_id = :a"
            ), {"a": app_id})


async def test_refer_then_officer_fills_the_fact(api) -> None:
    d = await submit(api, OFFICER, borrower_name="Lakshmi R.", amount_paise=35_000_00,
                     tenor_months=12, household_income_annual_paise=None,
                     existing_monthly_repayments_paise=1_500_00)
    app_id = d["application"]["id"]
    assert d["evaluation"]["outcome"] == "refer"
    r = await api.post(f"/api/v1/loans/applications/{app_id}/recommend",
                       json={"recommendation": "approve"})
    assert r.status_code == 409
    r = await api.patch(f"/api/v1/loans/applications/{app_id}",
                        json={"household_income_annual_paise": 2_00_000_00})
    assert r.status_code == 200, r.text
    assert r.json()["evaluation"]["outcome"] == "pass"


async def test_reject_needs_a_note_and_roles_are_enforced(api) -> None:
    d = await submit(api)
    app_id = d["application"]["id"]
    # A borrower cannot recommend or decide; a checker cannot submit.
    r = await api.post(f"/api/v1/loans/applications/{app_id}/recommend",
                       json={"recommendation": "reject", "note": "x"})
    assert r.status_code == 403
    api.as_(CHECKER)
    assert (await api.post("/api/v1/loans/applications", json=REKHA)).status_code == 403
    api.as_(OFFICER)
    r = await api.post(f"/api/v1/loans/applications/{app_id}/recommend",
                       json={"recommendation": "reject"})
    assert r.status_code == 422
    r = await api.post(f"/api/v1/loans/applications/{app_id}/recommend",
                       json={"recommendation": "reject", "note": "Over the limit"})
    assert r.status_code == 200
    api.as_(CHECKER)
    r = await api.post(f"/api/v1/loans/applications/{app_id}/decide", json={"outcome": "reject"})
    assert r.status_code == 422
    r = await api.post(f"/api/v1/loans/applications/{app_id}/decide",
                       json={"outcome": "reject", "note": "Agreed"})
    assert r.json()["application"]["status"] == "rejected"
    assert r.json()["decision"]["approved_paise"] is None


async def test_borrowers_see_only_their_own(api) -> None:
    d = await submit(api, OFFICER, borrower_name="Meena P.")
    other = User(uuid.uuid4(), ORG, "borrower", "Someone Else")
    api.as_(other)
    assert (await api.get("/api/v1/loans/applications")).json() == []
    r = await api.get(f"/api/v1/loans/applications/{d['application']['id']}")
    assert r.status_code == 404


async def test_auditor_views_and_admin_users(api, session) -> None:
    await submit(api)
    api.as_(AUDITOR)
    assert (await api.get("/api/v1/loans/counts")).json()["applications"] == 1
    events = (await api.get("/api/v1/loans/events")).json()
    assert {e["action"] for e in events} == {"submitted", "evaluated"}
    assert (await api.get("/api/v1/loans/decisions")).status_code == 200
    assert (await api.get("/api/v1/admin/users")).status_code == 403
    api.as_(OFFICER)
    assert (await api.get("/api/v1/loans/events")).status_code == 403
    assert (await api.get("/api/v1/loans/overview")).json()["counts"]["evaluated"] == 1
    api.as_(ADMIN)
    assert (await api.get("/api/v1/admin/users")).status_code == 200
    n = len((await session.scalars(select(Event))).all())
    assert n == 2


async def test_unknown_product_and_tenor(api) -> None:
    api.as_(BORROWER)
    r = await api.post("/api/v1/loans/applications", json={**REKHA, "product": "XYZ"})
    assert r.status_code == 422
    r = await api.post("/api/v1/loans/applications", json={**REKHA, "tenor_months": 7})
    assert r.status_code == 422


async def test_seed_loans_covers_every_path(session, monkeypatch) -> None:
    from app.identity import service as identity
    from app.loans.models import Application
    from app.loans.seed import seed_loans

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(service.audit, "log_event", _noop)
    await identity.seed_dev_users(session)
    await add_rule_set(session)
    created, present = await seed_loans(session)
    assert len(created) == 6 and present == []
    rows = {a.ref: a for a in (await session.scalars(select(Application))).all()}
    status = {ref: a.status for ref, a in rows.items()}
    assert status == {
        "APP-2026-0142": "approved_modified", "APP-2026-0137": "approved",
        "APP-2026-0139": "rejected", "APP-2026-0145": "recommended",
        "APP-2026-0148": "evaluated", "APP-2026-0150": "evaluated",
    }
    rekha = rows["APP-2026-0142"]
    assert rekha.borrower_name == "Rekha K." and rekha.borrower_id is not None
    ev = await service.latest_evaluation(session, rows["APP-2026-0148"])
    assert ev.outcome == "refer"
    ev = await service.latest_evaluation(session, rows["APP-2026-0150"])
    assert ev.outcome == "fail" and ev.offer["amount_paise"] > 0
    created, present = await seed_loans(session)
    assert created == [] and len(present) == 6


async def test_preview_saves_nothing_and_replay_matches(api, session) -> None:
    api.as_(BORROWER)
    r = await api.post("/api/v1/loans/preview", json={
        "product": "MFL", "amount_paise": 80_000_00, "tenor_months": 24,
        "household_income_annual_paise": 2_64_000_00,
        "existing_monthly_repayments_paise": 7_500_00})
    assert r.status_code == 200, r.text
    assert r.json()["outcome"] == "fail" and r.json()["offer"]["amount_paise"] == 66_000_00
    r = await api.post("/api/v1/loans/preview", json={"product": "MFL"})
    assert r.json()["outcome"] == "refer"
    assert (await session.scalars(select(Event))).all() == []

    d = await submit(api, OFFICER, borrower_name="Sunita D.", amount_paise=30_000_00,
                     tenor_months=12, existing_monthly_repayments_paise=2_000_00)
    app_id = d["application"]["id"]
    await api.post(f"/api/v1/loans/applications/{app_id}/recommend",
                   json={"recommendation": "approve"})
    api.as_(CHECKER)
    await api.post(f"/api/v1/loans/applications/{app_id}/decide", json={"outcome": "approve"})
    api.as_(AUDITOR)
    rep = (await api.get(f"/api/v1/loans/applications/{app_id}/replay")).json()
    assert rep["same_outcome"] and rep["same_results"] and rep["same_rules"]
    assert rep["signature"] == "pending"
    api.as_(BORROWER)
    assert (await api.get(f"/api/v1/loans/applications/{app_id}/replay")).status_code == 403
