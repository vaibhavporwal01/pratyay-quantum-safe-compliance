"""Maker-checker workflow for rules.

    draft ──approve──▶ approved ──retire──▶ retired
      │  ▲
   reject │ edit
      ▼  │
    rejected

A maker creates and edits drafts. A checker approves or rejects a draft with a note, and can
retire an approved rule. The checker is never the maker (checked here and by the database).
Only approved rules are in the library. Every action is written to the audit log.
"""

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.audit import service as audit
from app.identity.deps import User
from app.rules import templates
from app.rules.models import APPLIES_TO, STAGES, Paragraph, Rule, SourceDoc

TRANSITIONS: dict[tuple[str, str], str] = {
    ("draft", "approve"): "approved",
    ("draft", "reject"): "rejected",
    ("rejected", "edit"): "draft",
    ("draft", "edit"): "draft",
    ("approved", "retire"): "retired",
}


class WorkflowError(ValueError):
    """The action is not allowed on this rule."""


class NotFound(LookupError):
    pass


class MakerIsChecker(WorkflowError):
    pass


class InvalidRule(WorkflowError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def next_status(current: str, action: str) -> str:
    try:
        return TRANSITIONS[(current, action)]
    except KeyError:
        raise WorkflowError(f"Cannot {action} a rule that is {current}.") from None


def _related_text(related: list[dict[str, Any]]) -> str:
    return " ".join(r.get("text", "") for r in related)


def validate_rule(
    template: str,
    params: dict[str, Any],
    para_text: str,
    related: list[dict[str, Any]] | None = None,
    *,
    for_approval: bool = False,
) -> list[str]:
    """Every problem with a rule's content. Numbers must come from the rule's own paragraph;
    a scope phrase may come from the paragraph or from a related paragraph."""
    try:
        templates.validate_params(template, params)
    except templates.TemplateError as exc:
        return exc.errors
    scope_source = f"{para_text} {_related_text(related or [])}"
    errors = templates.check_against_text(template, {**params, "scope": None}, para_text)
    scope = params.get("scope")
    if scope and " ".join(scope.split()).casefold() not in " ".join(scope_source.split()).casefold():
        errors.append(f"scope: {scope!r} is not copied from the quoted text")
    if for_approval:
        errors += [f"{m}: value missing" for m in templates.missing_values(template, params)]
    return errors


async def _paragraph(session: AsyncSession, paragraph_id: uuid.UUID) -> Paragraph:
    para = await session.get(Paragraph, paragraph_id)
    if para is None:
        raise NotFound("Paragraph not found")
    return para


async def _related_from_ids(
    session: AsyncSession, doc_id: uuid.UUID, related: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Related paragraphs are stored with their quoted text, taken from the database."""
    out = []
    for r in related:
        para = await session.scalar(
            select(Paragraph).where(Paragraph.doc_id == doc_id, Paragraph.number == r["para"])
        )
        if para is None:
            raise InvalidRule([f"related: paragraph {r['para']} is not in this document"])
        out.append({"para": para.number, "text": para.text, "note": r.get("note") or ""})
    return out


async def get_rule(session: AsyncSession, rule_id: uuid.UUID) -> Rule:
    rule = await session.get(Rule, rule_id)
    if rule is None:
        raise NotFound("Rule not found")
    return rule


async def create_draft(session: AsyncSession, user: User, data: dict[str, Any]) -> Rule:
    """data: code, title, template, params, applies_to, effective_from, paragraph_id,
    related [{para, note}], origin, and optionally section and supersedes_rule_id."""
    para = await _paragraph(session, data["paragraph_id"])
    related = await _related_from_ids(session, para.doc_id, data.get("related") or [])
    if data["applies_to"] not in APPLIES_TO:
        raise InvalidRule([f"applies_to: must be one of {', '.join(APPLIES_TO)}"])
    stage = data.get("stage") or "origination"
    if stage not in STAGES:
        raise InvalidRule([f"stage: must be one of {', '.join(STAGES)}"])
    if errors := validate_rule(data["template"], data["params"], para.text, related):
        raise InvalidRule(errors)
    rule = Rule(
        code=data["code"],
        title=data["title"],
        template=data["template"],
        params=data["params"],
        applies_to=data["applies_to"],
        stage=stage,
        effective_from=data.get("effective_from"),
        status="draft",
        source_doc_id=para.doc_id,
        source_para=para.number or "",
        para_text=para.text,
        section=data.get("section") or None,
        related=related,
        supersedes_rule_id=data.get("supersedes_rule_id"),
        origin=data.get("origin", "manual"),
        made_by=user.id,
    )
    session.add(rule)
    await session.flush()
    await audit.log_event(
        session, user.id, "rule.draft_created", f"rule:{rule.id}",
        {"code": rule.code, "source_para": rule.source_para, "template": rule.template},
    )
    return rule


async def update_draft(
    session: AsyncSession, user: User, rule_id: uuid.UUID, data: dict[str, Any]
) -> Rule:
    rule = await get_rule(session, rule_id)
    new_status = next_status(rule.status, "edit")
    related = rule.related
    if "related" in data and data["related"] is not None:
        related = await _related_from_ids(session, rule.source_doc_id, data["related"])
    template = data.get("template") or rule.template
    params = data["params"] if data.get("params") is not None else rule.params
    applies_to = data.get("applies_to") or rule.applies_to
    if applies_to not in APPLIES_TO:
        raise InvalidRule([f"applies_to: must be one of {', '.join(APPLIES_TO)}"])
    if data.get("stage") and data["stage"] not in STAGES:
        raise InvalidRule([f"stage: must be one of {', '.join(STAGES)}"])
    if errors := validate_rule(template, params, rule.para_text, related):
        raise InvalidRule(errors)
    for key in ("code", "title"):
        if data.get(key):
            setattr(rule, key, data[key])
    if "effective_from" in data:
        rule.effective_from = data["effective_from"]
    if "section" in data:
        rule.section = data["section"] or None
    if data.get("stage"):
        rule.stage = data["stage"]
    rule.template, rule.params, rule.applies_to, rule.related = (
        template, params, applies_to, related,
    )
    previous = rule.status
    rule.status = new_status
    rule.checked_by = None
    rule.checked_at = None
    await session.flush()
    await audit.log_event(
        session, user.id, "rule.draft_edited", f"rule:{rule.id}",
        {"code": rule.code, "from_status": previous},
    )
    return rule


async def _check(
    session: AsyncSession, user: User, rule_id: uuid.UUID, action: str, note: str | None
) -> Rule:
    rule = await get_rule(session, rule_id)
    new_status = next_status(rule.status, action)
    if rule.made_by == user.id:
        raise MakerIsChecker("The maker of a rule cannot also check it.")
    if action == "approve":
        errors = validate_rule(
            rule.template, rule.params, rule.para_text, rule.related, for_approval=True
        )
        if errors:
            raise InvalidRule(errors)
    if action in ("reject", "retire") and not (note and note.strip()):
        raise WorkflowError(f"A note is needed to {action} a rule.")
    rule.status = new_status
    rule.checked_by = user.id
    rule.checked_at = datetime.now(UTC)
    rule.review_note = note.strip() if note else None
    if action == "retire":
        rule.effective_to = date.today()
        if rule.effective_from and rule.effective_to < rule.effective_from:
            rule.effective_to = rule.effective_from
    await session.flush()
    await audit.log_event(
        session, user.id, f"rule.{new_status}", f"rule:{rule.id}",
        {"code": rule.code, "note": rule.review_note},
    )
    return rule


async def approve(session: AsyncSession, user: User, rule_id: uuid.UUID, note: str | None):
    return await _check(session, user, rule_id, "approve", note)


async def reject(session: AsyncSession, user: User, rule_id: uuid.UUID, note: str | None):
    return await _check(session, user, rule_id, "reject", note)


async def retire(session: AsyncSession, user: User, rule_id: uuid.UUID, note: str | None):
    return await _check(session, user, rule_id, "retire", note)


async def list_rules(
    session: AsyncSession,
    statuses: tuple[str, ...] | None = None,
    as_of: date | None = None,
    made_by: uuid.UUID | None = None,
) -> list[Rule]:
    q = select(Rule)
    if statuses:
        q = q.where(Rule.status.in_(statuses))
    if made_by:
        q = q.where(Rule.made_by == made_by)
    if as_of:
        q = q.where(
            or_(Rule.effective_from.is_(None), Rule.effective_from <= as_of),
            or_(Rule.effective_to.is_(None), Rule.effective_to >= as_of),
        )
    rows = await session.scalars(q.order_by(Rule.code, Rule.created_at))
    return list(rows)


async def library(session: AsyncSession, as_of: date | None = None) -> list[Rule]:
    """The rule library: approved rules only, optionally those in force on a date."""
    return await list_rules(session, ("approved",), as_of)


async def counts(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(select(Rule.status, func.count()).group_by(Rule.status))
    out = {s: 0 for s in ("draft", "approved", "rejected", "retired")}
    out.update({s: n for s, n in rows})
    return out


async def find_rule(
    session: AsyncSession, doc_id: uuid.UUID, code: str
) -> Rule | None:
    """The live (not retired or rejected) rule with this code from this document."""
    return await session.scalar(
        select(Rule).where(
            and_(Rule.source_doc_id == doc_id, Rule.code == code),
            Rule.status.in_(("draft", "approved")),
        )
    )


async def source_docs_by_id(session: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, SourceDoc]:
    if not ids:
        return {}
    rows = await session.scalars(
        select(SourceDoc).options(defer(SourceDoc.file)).where(SourceDoc.id.in_(ids))
    )
    return {d.id: d for d in rows}


async def set_stage(session: AsyncSession, user: User, rule_id: uuid.UUID, stage: str) -> Rule:
    """Change when a rule is checked (origination, servicing or recovery). Audited."""
    if stage not in STAGES:
        raise InvalidRule([f"stage: must be one of {', '.join(STAGES)}"])
    rule = await get_rule(session, rule_id)
    if rule.stage != stage:
        previous, rule.stage = rule.stage, stage
        await session.flush()
        await audit.log_event(
            session, user.id, "rule.stage_set", f"rule:{rule.id}",
            {"code": rule.code, "from": previous, "to": stage},
        )
    return rule


async def rule_version(session: AsyncSession, rule: Rule) -> int:
    """1 for a rule that supersedes nothing, 2 for its first replacement, and so on."""
    version, prev = 1, rule.supersedes_rule_id
    while prev is not None:
        version += 1
        prev = await session.scalar(select(Rule.supersedes_rule_id).where(Rule.id == prev))
    return version
