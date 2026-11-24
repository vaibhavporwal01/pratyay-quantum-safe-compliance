"""rules: service. The only entry point other modules (and the router) use."""

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.identity import service as identity
from app.rules import templates
from app.rules.classify import (
    REVIEW_THRESHOLD,
    ClassifyResult,
    ModelNotFound,
    classify_paragraphs,
    needs_review,
)
from app.rules.engine import Evaluation, RuleResult, build_kfs, evaluate_application
from app.rules.ingest import (
    MAX_PDF_BYTES,
    FileTooLarge,
    IngestError,
    IngestReport,
    IngestResult,
    ingest_pdf,
)
from app.rules.models import SHORT_CODE_PATTERN, Paragraph, Rule, SourceDoc
from app.rules.workflow import (
    InvalidRule,
    MakerIsChecker,
    NotFound,
    WorkflowError,
    approve,
    counts,
    create_draft,
    find_rule,
    get_rule,
    library,
    list_rules,
    reject,
    retire,
    rule_version,
    set_stage,
    source_docs_by_id,
    update_draft,
    validate_rule,
)

__all__ = [
    "MAX_PDF_BYTES",
    "REVIEW_THRESHOLD",
    "SHORT_CODE_PATTERN",
    "ClassifyResult",
    "Evaluation",
    "FileTooLarge",
    "IngestError",
    "IngestReport",
    "IngestResult",
    "InvalidRule",
    "MakerIsChecker",
    "ModelNotFound",
    "NotFound",
    "RuleResult",
    "WorkflowError",
    "approve",
    "build_kfs",
    "classify_paragraphs",
    "counts",
    "create_draft",
    "evaluate_application",
    "find_rule",
    "get_paragraph",
    "get_paragraph_by_number",
    "get_rule",
    "get_source_doc",
    "ingest_pdf",
    "library",
    "list_paragraphs",
    "list_rules",
    "list_source_docs",
    "needs_review",
    "paragraph_sort_key",
    "reject",
    "retire",
    "rule_version",
    "rules_out",
    "set_stage",
    "source_stats",
    "update_draft",
    "validate_rule",
]


async def get_source_doc(session: AsyncSession, doc_id: uuid.UUID) -> SourceDoc | None:
    return await session.get(SourceDoc, doc_id)


async def list_source_docs(session: AsyncSession) -> list[SourceDoc]:
    """All source documents, ordered by ref_no then title (file bytes are not loaded)."""
    rows = await session.scalars(
        select(SourceDoc)
        .options(defer(SourceDoc.file))
        .order_by(SourceDoc.ref_no.nulls_last(), SourceDoc.title)
    )
    return list(rows)


_NUMBER_RE = re.compile(r"^(\d+)([A-Z]*)(?:\((\d+)\))?$")


def paragraph_sort_key(number: str | None) -> tuple[int, str, int]:
    """Document order from the paragraph number: 29 < 29(1) < 29(2) < 105 < 105A."""
    m = _NUMBER_RE.match(number or "")
    if not m:
        return (10**9, number or "", 0)
    return (int(m.group(1)), m.group(2), int(m.group(3)) if m.group(3) else -1)


async def list_paragraphs(session: AsyncSession, doc_id: uuid.UUID) -> list[Paragraph]:
    rows = await session.scalars(select(Paragraph).where(Paragraph.doc_id == doc_id))
    return sorted(rows, key=lambda p: paragraph_sort_key(p.number))


async def source_stats(session: AsyncSession, docs: list[SourceDoc]) -> list[dict]:
    """Each document with its paragraph, label and rule counts."""
    ids = [d.id for d in docs]
    labels: dict = {}
    review: dict = {}
    rules: dict = {}
    if ids:
        rows = await session.execute(
            select(Paragraph.doc_id, Paragraph.label, func.count())
            .where(Paragraph.doc_id.in_(ids))
            .group_by(Paragraph.doc_id, Paragraph.label)
        )
        for doc_id, label, n in rows:
            labels.setdefault(doc_id, {})[label or "unlabelled"] = n
        rows = await session.execute(
            select(Paragraph.doc_id, func.count())
            .where(Paragraph.doc_id.in_(ids), Paragraph.confidence < REVIEW_THRESHOLD)
            .group_by(Paragraph.doc_id)
        )
        review = dict(rows.all())
        rows = await session.execute(
            select(Rule.source_doc_id, Rule.status, func.count())
            .where(Rule.source_doc_id.in_(ids))
            .group_by(Rule.source_doc_id, Rule.status)
        )
        for doc_id, status, n in rows:
            rules.setdefault(doc_id, {})[status] = n
    return [
        {
            "id": d.id,
            "title": d.title,
            "short_code": d.short_code,
            "ref_no": d.ref_no,
            "issued_on": d.issued_on,
            "url": d.url,
            "sha3_256": d.sha3_256.hex() if d.sha3_256 else None,
            "pages": d.pages,
            "uploaded_at": d.uploaded_at,
            "paragraphs": sum(labels.get(d.id, {}).values()),
            "labels": labels.get(d.id, {}),
            "needs_review": review.get(d.id, 0),
            "rules": rules.get(d.id, {}),
        }
        for d in docs
    ]


async def rules_out(session: AsyncSession, rules: list[Rule]) -> list[dict]:
    """Rules with names, source titles, open problems and boundary tests, for the API."""
    names = await identity.user_names(
        session, {r.made_by for r in rules} | {r.checked_by for r in rules if r.checked_by}
    )
    docs = await source_docs_by_id(session, {r.source_doc_id for r in rules})
    out = []
    for r in rules:
        try:
            missing = templates.missing_values(r.template, r.params)
            tests = [t.as_dict() for t in templates.boundary_tests(r.template, r.params)]
        except templates.TemplateError:
            missing, tests = [], []
        doc = docs.get(r.source_doc_id)
        out.append(
            {
                **{c: getattr(r, c) for c in (
                    "id", "code", "title", "template", "params", "applies_to", "stage", "effective_from",
                    "effective_to", "status", "source_doc_id", "source_para", "para_text",
                    "section", "related", "origin", "made_by", "checked_by", "review_note", "created_at",
                    "updated_at", "checked_at",
                )},
                "source_doc_title": doc.title if doc else "",
                "source_doc_code": doc.short_code if doc else None,
                "source_doc_ref": doc.ref_no if doc else None,
                "made_by_name": names.get(r.made_by),
                "checked_by_name": names.get(r.checked_by) if r.checked_by else None,
                "missing": missing,
                "problems": validate_rule(r.template, r.params, r.para_text, r.related),
                "tests": tests,
            }
        )
    return out


async def get_paragraph(session: AsyncSession, paragraph_id: uuid.UUID) -> Paragraph | None:
    return await session.get(Paragraph, paragraph_id)


async def get_paragraph_by_number(
    session: AsyncSession, doc_id: uuid.UUID, number: str
) -> Paragraph | None:
    return await session.scalar(
        select(Paragraph).where(Paragraph.doc_id == doc_id, Paragraph.number == number)
    )
