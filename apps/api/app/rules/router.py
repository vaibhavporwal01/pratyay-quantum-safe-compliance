import uuid
from dataclasses import asdict
from datetime import date
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.identity.deps import User, require_role
from app.rules import facts as rule_facts
from app.rules import service, templates
from app.rules.extract import extract
from app.rules.schemas import (
    CheckIn,
    CheckOut,
    FactOut,
    IngestReportOut,
    OverviewOut,
    ParagraphOut,
    ReviewIn,
    RuleCreate,
    RuleOut,
    RuleUpdate,
    SourceDocOut,
    SourceIngestOut,
    SuggestionOut,
)
from app.rules.service import SHORT_CODE_PATTERN

router = APIRouter(prefix="/rules", tags=["rules"])

Session = Annotated[AsyncSession, Depends(get_session)]
Maker = Annotated[User, Depends(require_role("maker"))]
Checker = Annotated[User, Depends(require_role("checker"))]
Reader = Annotated[User, Depends(require_role("maker", "checker", "auditor", "admin"))]


def _workflow_errors(exc: Exception) -> HTTPException:
    match exc:
        case service.NotFound():
            return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
        case service.InvalidRule():
            return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, {"problems": exc.errors})
        case service.MakerIsChecker():
            return HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
        case service.WorkflowError():
            return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    raise exc


@router.get("/ping")
async def ping() -> dict:
    return {"module": "rules", "status": "ready"}


# ---- sources ---------------------------------------------------------------------------


@router.get("/sources", response_model=list[SourceDocOut])
async def list_sources(session: Session, user: Reader) -> list:
    return await service.source_stats(session, await service.list_source_docs(session))


@router.post("/sources", response_model=SourceIngestOut, status_code=status.HTTP_201_CREATED)
async def upload_source(
    session: Session,
    user: Maker,
    response: Response,
    file: Annotated[UploadFile, File(description="RBI Directions PDF, at most 20 MB")],
    title: Annotated[str, Form(min_length=1)],
    short_code: Annotated[
        str | None, Form(pattern=SHORT_CODE_PATTERN, description='Citation code, e.g. "CF"')
    ] = None,
    ref_no: Annotated[str | None, Form()] = None,
    issued_on: Annotated[date | None, Form()] = None,
    url: Annotated[str | None, Form()] = None,
) -> SourceIngestOut:
    # Read one byte past the limit so an oversized upload is caught without reading it all.
    data = await file.read(service.MAX_PDF_BYTES + 1)
    try:
        result = await service.ingest_pdf(
            session, data, title=title, short_code=short_code, ref_no=ref_no, issued_on=issued_on, url=url,
            uploaded_by=user.id,
        )
    except service.FileTooLarge as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
    except service.IngestError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await session.commit()

    report = result.report
    classified = False
    if not report.duplicate:
        try:
            await service.classify_paragraphs(session, report.doc_id)
            classified = True
        except service.ModelNotFound:
            pass  # labels stay empty until the classifier is trained and run
    if report.duplicate:
        response.status_code = status.HTTP_200_OK  # nothing new was created
    return SourceIngestOut(
        doc_id=report.doc_id,
        sha3_256=report.sha3_256,
        duplicate=report.duplicate,
        classified=classified,
        report=IngestReportOut(
            pages=report.pages,
            paragraphs=report.paragraphs,
            unmatched=[asdict(u) for u in report.unmatched],
            removed=[asdict(r) for r in report.removed],
        ),
    )


@router.get("/sources/{doc_id}", response_model=SourceDocOut)
async def get_source(doc_id: uuid.UUID, session: Session, user: Reader) -> dict:
    doc = await service.get_source_doc(session, doc_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source document not found")
    return (await service.source_stats(session, [doc]))[0]


@router.get("/sources/{doc_id}/paragraphs", response_model=list[ParagraphOut])
async def source_paragraphs(doc_id: uuid.UUID, session: Session, user: Reader) -> list:
    if await service.get_source_doc(session, doc_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source document not found")
    return await service.list_paragraphs(session, doc_id)


@router.get("/paragraphs/{paragraph_id}/suggestion", response_model=SuggestionOut)
async def paragraph_suggestion(paragraph_id: uuid.UUID, session: Session, user: Maker) -> dict:
    para = await service.get_paragraph(session, paragraph_id)
    if para is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paragraph not found")
    return {"paragraph": para, "doc_id": para.doc_id, **templates.suggest(para.text)}


@router.post("/check", response_model=CheckOut)
async def check_rule(body: CheckIn, session: Session, user: Reader) -> dict:
    """Validate a rule against its paragraph and run its boundary tests, without saving."""
    para = await service.get_paragraph(session, body.paragraph_id)
    if para is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paragraph not found")
    related = []
    for r in body.related:
        p = await service.get_paragraph_by_number(session, para.doc_id, r.para)
        if p is None:
            return {"problems": [f"related: paragraph {r.para} is not in this document"],
                    "missing": [], "tests": []}
        related.append({"para": p.number, "text": p.text, "note": r.note})
    problems = service.validate_rule(body.template, body.params, para.text, related)
    if problems:
        return {"problems": problems, "missing": [], "tests": []}
    return {
        "problems": [],
        "missing": templates.missing_values(body.template, body.params),
        "tests": [t.as_dict() for t in templates.boundary_tests(body.template, body.params)],
        "fact_notes": rule_facts.notes(body.template, body.params),
    }


@router.get("/facts", response_model=list[FactOut])
async def fact_catalogue(user: Reader) -> list[dict]:
    """The facts a rule can check, for the rule builder's dropdowns."""
    return [f.as_dict() for f in rule_facts.CATALOGUE]


@router.post("/extract")
async def extract_values(body: dict, user: Reader) -> list[dict]:
    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "text is required")
    return [v.as_dict() for v in extract(text)]


# ---- rules -----------------------------------------------------------------------------


@router.get("/overview", response_model=OverviewOut)
async def overview(session: Session, user: Reader) -> dict:
    drafts = await service.list_rules(session, ("draft",))
    waiting = [r for r in drafts if r.made_by != user.id]
    checked = [
        r for r in await service.list_rules(session, ("approved", "rejected", "retired"))
        if r.checked_at is not None
    ]
    checked.sort(key=lambda r: r.checked_at, reverse=True)
    return {
        "counts": await service.counts(session),
        "sources": len(await service.list_source_docs(session)),
        "waiting_for_you": await service.rules_out(session, user.org_id, waiting),
        "recently_checked": await service.rules_out(session, user.org_id, checked[:5]),
    }


@router.get("/library", response_model=list[RuleOut])
async def rule_library(
    session: Session, user: Reader, as_of: Annotated[date | None, Query()] = None
) -> list:
    return await service.rules_out(session, user.org_id, await service.library(session, as_of))


@router.get("", response_model=list[RuleOut])
async def list_all_rules(
    session: Session,
    user: Reader,
    status_: Annotated[list[str] | None, Query(alias="status")] = None,
    mine: bool = False,
) -> list:
    rules = await service.list_rules(
        session, tuple(status_) if status_ else None, made_by=user.id if mine else None
    )
    return await service.rules_out(session, user.org_id, rules)


@router.post("", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(body: RuleCreate, session: Session, user: Maker) -> dict:
    try:
        rule = await service.create_draft(session, user, body.model_dump())
    except (service.WorkflowError, service.NotFound) as exc:
        raise _workflow_errors(exc) from exc
    await session.commit()
    return (await service.rules_out(session, user.org_id, [rule]))[0]


@router.get("/{rule_id}", response_model=RuleOut)
async def read_rule(rule_id: uuid.UUID, session: Session, user: Reader) -> dict:
    try:
        rule = await service.get_rule(session, rule_id)
    except service.NotFound as exc:
        raise _workflow_errors(exc) from exc
    return (await service.rules_out(session, user.org_id, [rule]))[0]


@router.patch("/{rule_id}", response_model=RuleOut)
async def edit_rule(rule_id: uuid.UUID, body: RuleUpdate, session: Session, user: Maker) -> dict:
    try:
        rule = await service.update_draft(
            session, user, rule_id, body.model_dump(exclude_unset=True)
        )
    except (service.WorkflowError, service.NotFound) as exc:
        raise _workflow_errors(exc) from exc
    await session.commit()
    return (await service.rules_out(session, user.org_id, [rule]))[0]


async def _review(action, rule_id, body, session, user) -> dict:
    try:
        rule = await action(session, user, rule_id, body.note)
    except (service.WorkflowError, service.NotFound) as exc:
        raise _workflow_errors(exc) from exc
    await session.commit()
    return (await service.rules_out(session, user.org_id, [rule]))[0]


@router.post("/{rule_id}/approve", response_model=RuleOut)
async def approve_rule(rule_id: uuid.UUID, body: ReviewIn, session: Session, user: Checker):
    return await _review(service.approve, rule_id, body, session, user)


@router.post("/{rule_id}/reject", response_model=RuleOut)
async def reject_rule(rule_id: uuid.UUID, body: ReviewIn, session: Session, user: Checker):
    return await _review(service.reject, rule_id, body, session, user)


@router.post("/{rule_id}/retire", response_model=RuleOut)
async def retire_rule(rule_id: uuid.UUID, body: ReviewIn, session: Session, user: Checker):
    return await _review(service.retire, rule_id, body, session, user)
