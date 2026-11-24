"""Rules API: roles, maker-checker over HTTP, library and check endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.identity.deps import get_current_user
from app.main import app
from app.rules import workflow
from tests.helpers import CF_55, CF_56, RATIO_RULE, add_paragraphs, user

MAKER = user("maker", "Neha Verma")
CHECKER = user("checker", "Rahul Mehta")
OFFICER = user("officer", "Anita Sharma")


@pytest.fixture
async def api(session: AsyncSession, monkeypatch):
    """A client whose user can be switched with api.as_(user)."""

    async def _session():
        yield session

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(workflow.audit, "log_event", _noop)
    current = {"user": MAKER}
    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_current_user] = lambda: current["user"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.as_ = lambda u: current.update(user=u)  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def paras(session: AsyncSession):
    return await add_paragraphs(session, {"55": CF_55, "56": CF_56})


async def create(api: AsyncClient, paras, **overrides):
    body = {**RATIO_RULE, "paragraph_id": str(paras["55"].id), **overrides}
    return await api.post("/api/v1/rules", json=body)


async def test_maker_creates_checker_approves(api, paras) -> None:
    r = await create(api, paras, related=[{"para": "56", "note": "all loans"}])
    assert r.status_code == 201, r.text
    rule = r.json()
    assert rule["status"] == "draft" and rule["made_by"] == str(MAKER.id)
    assert rule["related"][0]["text"] == CF_56
    assert rule["problems"] == [] and rule["missing"] == []
    assert all(t["passed"] for t in rule["tests"])

    # The maker role cannot approve at all.
    r = await api.post(f"/api/v1/rules/{rule['id']}/approve", json={})
    assert r.status_code == 403

    api.as_(CHECKER)
    r = await api.post(f"/api/v1/rules/{rule['id']}/approve", json={"note": "ok"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"
    assert r.json()["checked_by"] == str(CHECKER.id)

    lib = (await api.get("/api/v1/rules/library")).json()
    assert [x["code"] for x in lib] == ["MF-02"]


async def test_same_person_cannot_approve(api, paras) -> None:
    rule = (await create(api, paras)).json()
    # Same person, now holding the checker role.
    api.as_(type(MAKER)(MAKER.id, MAKER.org_id, "checker", MAKER.name))
    r = await api.post(f"/api/v1/rules/{rule['id']}/approve", json={})
    assert r.status_code == 403
    assert "maker" in r.json()["detail"]


async def test_reject_with_note_then_edit(api, paras) -> None:
    rule = (await create(api, paras)).json()
    api.as_(CHECKER)
    assert (await api.post(f"/api/v1/rules/{rule['id']}/reject", json={})).status_code == 409
    r = await api.post(f"/api/v1/rules/{rule['id']}/reject", json={"note": "Check scope"})
    assert r.json()["status"] == "rejected" and r.json()["review_note"] == "Check scope"

    api.as_(MAKER)
    r = await api.patch(f"/api/v1/rules/{rule['id']}", json={"title": "Repayment cap"})
    assert r.status_code == 200 and r.json()["status"] == "draft"


async def test_invalid_number_returns_problems(api, paras) -> None:
    r = await create(api, paras, params={**RATIO_RULE["params"], "max_percent": "45"})
    assert r.status_code == 422
    assert r.json()["detail"]["problems"] == ["max_percent: 45 is not in the quoted text"]


async def test_other_roles_are_refused(api, paras) -> None:
    api.as_(OFFICER)
    assert (await create(api, paras)).status_code == 403
    assert (await api.get("/api/v1/rules/library")).status_code == 403


async def test_suggestion_and_check(api, paras) -> None:
    r = await api.get(f"/api/v1/rules/paragraphs/{paras['55'].id}/suggestion")
    assert r.status_code == 200
    s = r.json()
    assert s["template"] == "max_ratio" and s["params"]["max_percent"] == "50"
    assert any(v["text"] == "50 per cent" for v in s["values"])

    body = {"template": "max_ratio", "paragraph_id": str(paras["55"].id),
            "params": {"numerator": "a", "denominator": "b", "max_percent": "50"}}
    r = await api.post("/api/v1/rules/check", json=body)
    assert r.json()["problems"] == [] and len(r.json()["tests"]) == 3


async def test_overview_lists_drafts_for_other_checkers(api, paras) -> None:
    await create(api, paras)
    api.as_(CHECKER)
    o = (await api.get("/api/v1/rules/overview")).json()
    assert o["counts"]["draft"] >= 1
    assert [r["code"] for r in o["waiting_for_you"]] == ["MF-02"]


async def test_unknown_rule_is_404(api) -> None:
    r = await api.get("/api/v1/rules/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


async def test_rule_carries_source_code_and_section(api, paras) -> None:
    r = await create(api, paras, section="H. Conduct towards Microfinance borrowers")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["source_doc_code"] == "CF"
    assert body["section"] == "H. Conduct towards Microfinance borrowers"
    sources = (await api.get("/api/v1/rules/sources")).json()
    assert [d["short_code"] for d in sources] == ["CF"]
