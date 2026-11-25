"""Rules from a new PDF execute with no code change: the engine evaluates by template and reads
the fact named in the rule's params from the fact catalogue."""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.db import get_session
from app.identity.deps import get_current_user
from app.loans import service as loans
from app.main import app
from app.rules import engine, facts, templates, workflow
from app.rules.models import Paragraph, SourceDoc
from tests.helpers import user
from tests.rule_fixtures import REKHA, add_rule_set

MAKER = user("maker", "Neha Verma")
CHECKER = user("checker", "Rahul Mehta")
BORROWER = user("borrower", "Rekha K.")
OFFICER = user("officer", "Anita Sharma")

# A paragraph from a new (test) Directions document: a cap on the loan amount.
NEW_PARA = ("The loan amount sanctioned to a borrower under this scheme shall not exceed "
            "₹50,000.")
APPLICATION = {
    "product": "MFL", "tenor_months": 24, "purpose": "Stock",
    "household_income_annual_paise": 2_64_000_00, "existing_monthly_repayments_paise": 0,
}


@pytest.fixture
async def api(session, monkeypatch):
    async def _session():
        yield session

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(workflow.audit, "log_event", _noop)
    monkeypatch.setattr(loans.audit, "log_event", _noop)
    monkeypatch.setattr(loans, "today", lambda: date(2026, 11, 25))
    await add_rule_set(session)
    current = {"user": MAKER}
    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_current_user] = lambda: current["user"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.as_ = lambda u: current.update(user=u)  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()


async def add_paragraphs(session, paras: dict[str, str]) -> dict[str, Paragraph]:
    """Paragraphs of a new Directions document, short code NEW."""
    doc = SourceDoc(title="New Scheme Directions", short_code="NEW", ref_no="RBI/TEST/9")
    session.add(doc)
    await session.flush()
    rows = {n: Paragraph(doc_id=doc.id, number=n, page=1, text=t) for n, t in paras.items()}
    session.add_all(rows.values())
    await session.flush()
    return rows


def result(detail: dict, code: str) -> dict:
    return next(r for r in detail["evaluation"]["results"] if r["code"] == code)


async def test_new_max_amount_rule_runs_with_no_code_change(api, session) -> None:
    paras = await add_paragraphs(session, {"12": NEW_PARA})

    # The maker sees the loan amount fact pre-selected for this paragraph.
    r = await api.get(f"/api/v1/rules/paragraphs/{paras['12'].id}/suggestion")
    assert r.status_code == 200, r.text
    suggestion = r.json()
    assert suggestion["template"] == "max_amount"
    assert suggestion["params"]["fact"] == "amount_paise"
    assert suggestion["params"]["max_paise"] == 50_000_00

    keys = [f["key"] for f in (await api.get("/api/v1/rules/facts")).json()]
    assert "amount_paise" in keys and "household_income_annual_paise" in keys

    r = await api.post("/api/v1/rules", json={
        "code": "LA-01", "title": "Loan amount up to ₹50,000", "template": "max_amount",
        "params": {"subject": "loan amount", "fact": "amount_paise",
                   "max_paise": suggestion["params"]["max_paise"]},
        "applies_to": "all", "effective_from": "2026-01-01",
        "paragraph_id": str(paras["12"].id),
    })
    assert r.status_code == 201, r.text
    rule = r.json()
    assert rule["problems"] == [] and rule["fact_notes"] == []
    api.as_(CHECKER)
    r = await api.post(f"/api/v1/rules/{rule['id']}/approve", json={"note": "ok"})
    assert r.status_code == 200 and r.json()["status"] == "approved"

    api.as_(BORROWER)
    ok = (await api.post("/api/v1/loans/applications",
                         json={**APPLICATION, "amount_paise": 40_000_00})).json()
    over = (await api.post("/api/v1/loans/applications",
                           json={**APPLICATION, "amount_paise": 60_000_00})).json()

    assert result(ok, "LA-01")["status"] == "pass"
    assert result(ok, "LA-01")["message"] == "Loan amount ₹40,000, within ₹50,000."
    assert result(ok, "LA-01")["anchor"] == "NEW para 12"
    assert result(over, "LA-01")["status"] == "fail"
    assert result(over, "LA-01")["message"] == "Loan amount ₹60,000 is above ₹50,000."
    assert over["evaluation"]["outcome"] == "fail"
    assert {"code": "LA-01", "version": 1} in [
        {k: u[k] for k in ("code", "version")} for u in over["evaluation"]["rules_used"]]
    # The seeded rules are unaffected.
    assert result(ok, "MF-01")["status"] == result(ok, "MF-02")["status"] == "pass"


async def test_fact_not_in_catalogue_can_be_approved_and_refers(api, session) -> None:
    paras = await add_paragraphs(session, {"14": NEW_PARA})
    r = await api.post("/api/v1/rules", json={
        "code": "LA-02", "title": "Gold value up to ₹50,000", "template": "max_amount",
        "params": {"subject": "gold value", "fact": "gold_value_paise", "max_paise": 50_000_00},
        "applies_to": "all", "effective_from": "2026-01-01",
        "paragraph_id": str(paras["14"].id),
    })
    assert r.status_code == 201, r.text
    rule = r.json()
    assert rule["fact_notes"] == [
        "fact: fact not in catalogue (gold_value_paise); the rule evaluates as refer."]
    api.as_(CHECKER)
    assert (await api.post(f"/api/v1/rules/{rule['id']}/approve", json={})).status_code == 200

    api.as_(OFFICER)
    d = (await api.post("/api/v1/loans/applications", json={
        **APPLICATION, "amount_paise": 40_000_00, "borrower_name": "Test"})).json()
    la02 = result(d, "LA-02")
    assert la02["status"] == "refer"
    assert la02["message"] == "Fact not in catalogue: gold_value_paise."


async def test_ratio_on_new_facts_without_offer(session) -> None:
    """A max_ratio between any two catalogue facts, no offer unless offer_on_fail is set."""
    rules = await add_rule_set(session)
    rules["MF-02"].params = {**rules["MF-02"].params, "offer_on_fail": False}
    await session.flush()
    ev = await engine.evaluate_application(session, REKHA, date(2025, 12, 10))
    assert ev.result("MF-02").status == "fail"
    assert ev.offer is None and "l_max" not in ev.result("MF-02").values


def test_engine_has_no_rule_codes() -> None:
    import inspect
    import re

    source = inspect.getsource(engine)
    code_lines = [line for line in source.splitlines()
                  if not line.strip().startswith("#") and re.search(r"\b(MF|KF)-\d", line)]
    # Only the module docstring mentions one, as an example.
    assert all("e.g." in line for line in code_lines), code_lines


def test_suggest_preselects_facts_from_wording() -> None:
    cf51 = ("A microfinance loan is a collateral-free loan given to a household having annual "
            "household income up to ₹3,00,000.")
    assert templates.suggest(cf51)["params"]["fact"] == "household_income_annual_paise"
    cf55 = ("limit on the outflows on account of repayment of monthly loan obligations of a "
            "household as a percentage of the monthly household income. This shall be subject "
            "to a limit of maximum 50 per cent of the monthly household income.")
    p = templates.suggest(cf55)["params"]
    assert (p["numerator_fact"], p["denominator_fact"]) == (
        "monthly_repayments_paise", "household_income_monthly_paise")
    assert templates.suggest("No fee shall be charged.")["params"]["fact"] is None


def test_catalogue_notes() -> None:
    assert facts.notes("max_amount", {"fact": "amount_paise"}) == []
    assert facts.notes("max_amount", {}) == [
        "fact: no fact chosen; the rule evaluates as refer."]
    assert facts.notes("time_window", {}) == []
