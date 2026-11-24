"""Maker-checker workflow: drafts, approval, rejection, retirement, and four eyes."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.rules import service, workflow
from tests.helpers import CF_55, CF_56, RATIO_RULE, add_paragraphs, user

MAKER = user("maker", "Neha Verma")
CHECKER = user("checker", "Rahul Mehta")


@pytest.fixture
def audit_log(monkeypatch) -> list[tuple]:
    calls: list[tuple] = []

    async def log_event(session, actor_id, action, target, meta=None):
        calls.append((actor_id, action, target, meta))

    monkeypatch.setattr(workflow.audit, "log_event", log_event)
    return calls


async def draft(session: AsyncSession, **overrides):
    paras = await add_paragraphs(session, {"55": CF_55, "56": CF_56})
    data = {**RATIO_RULE, "paragraph_id": paras["55"].id, **overrides}
    return await service.create_draft(session, MAKER, data)


async def test_create_draft_copies_paragraph_and_related(session, audit_log) -> None:
    rule = await draft(session, related=[{"para": "56", "note": "all loans count"}])
    assert rule.status == "draft" and rule.made_by == MAKER.id and rule.checked_by is None
    assert rule.source_para == "55" and rule.para_text == CF_55
    assert rule.related == [{"para": "56", "text": CF_56, "note": "all loans count"}]
    assert audit_log[-1][:2] == (MAKER.id, "rule.draft_created")


async def test_draft_with_number_not_in_text_is_rejected(session, audit_log) -> None:
    params = {**RATIO_RULE["params"], "max_percent": "40"}
    with pytest.raises(service.InvalidRule, match="40 is not in the quoted text"):
        await draft(session, params=params)


async def test_unknown_related_paragraph_is_rejected(session, audit_log) -> None:
    with pytest.raises(service.InvalidRule, match="paragraph 99"):
        await draft(session, related=[{"para": "99"}])


async def test_maker_cannot_check_own_rule(session, audit_log) -> None:
    rule = await draft(session)
    with pytest.raises(service.MakerIsChecker):
        await service.approve(session, MAKER, rule.id, None)
    with pytest.raises(service.MakerIsChecker):
        await service.reject(session, MAKER, rule.id, "no")
    assert rule.status == "draft"


async def test_database_enforces_maker_is_not_checker(session, audit_log) -> None:
    rule = await draft(session)
    with pytest.raises(IntegrityError, match="ck_rules_maker_checker"):
        async with session.begin_nested():
            await session.execute(
                text("UPDATE rules.rules SET checked_by = made_by WHERE id = :id"),
                {"id": rule.id},
            )


async def test_approve_then_retire(session, audit_log) -> None:
    rule = await draft(session)
    await service.approve(session, CHECKER, rule.id, "Matches para 55.")
    assert (rule.status, rule.checked_by, rule.review_note) == (
        "approved", CHECKER.id, "Matches para 55."
    )
    assert rule.checked_at is not None
    assert [r.id for r in await service.library(session)] == [rule.id]

    with pytest.raises(service.WorkflowError, match="note"):
        await service.retire(session, CHECKER, rule.id, " ")
    await service.retire(session, CHECKER, rule.id, "Superseded.")
    assert rule.status == "retired" and rule.effective_to is not None
    assert await service.library(session) == []
    assert [a[1] for a in audit_log] == ["rule.draft_created", "rule.approved", "rule.retired"]


async def test_reject_needs_note_and_edit_returns_to_draft(session, audit_log) -> None:
    rule = await draft(session)
    with pytest.raises(service.WorkflowError, match="note"):
        await service.reject(session, CHECKER, rule.id, None)
    await service.reject(session, CHECKER, rule.id, "Scope is too wide.")
    assert rule.status == "rejected" and await service.library(session) == []

    await service.update_draft(session, MAKER, rule.id, {"title": "Repayment cap"})
    assert (rule.status, rule.title, rule.checked_by) == ("draft", "Repayment cap", None)


@pytest.mark.parametrize(
    ("current", "action"),
    [("approved", "approve"), ("approved", "reject"), ("approved", "edit"),
     ("rejected", "approve"), ("retired", "edit"), ("retired", "approve"),
     ("draft", "retire")],
)
def test_blocked_transitions(current: str, action: str) -> None:
    with pytest.raises(service.WorkflowError):
        workflow.next_status(current, action)


async def test_approval_blocked_while_values_missing(session, audit_log) -> None:
    params = {**RATIO_RULE["params"], "max_percent": None}
    rule = await draft(session, params=params)
    with pytest.raises(service.InvalidRule, match="max_percent: value missing"):
        await service.approve(session, CHECKER, rule.id, None)


async def test_library_as_of_date(session, audit_log) -> None:
    from datetime import date

    rule = await draft(session, effective_from=date(2025, 11, 28))
    await service.approve(session, CHECKER, rule.id, None)
    assert await service.library(session, as_of=date(2025, 11, 27)) == []
    assert len(await service.library(session, as_of=date(2026, 1, 1))) == 1
