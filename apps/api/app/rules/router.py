import uuid
from dataclasses import asdict
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.identity.deps import User, require_role
from app.rules import service
from app.rules.schemas import IngestReportOut, ParagraphOut, SourceIngestOut

router = APIRouter(prefix="/rules", tags=["rules"])

Session = Annotated[AsyncSession, Depends(get_session)]
Maker = Annotated[User, Depends(require_role("maker"))]


@router.get("/ping")
async def ping() -> dict:
    return {"module": "rules", "status": "ready"}


@router.post("/sources", response_model=SourceIngestOut, status_code=status.HTTP_201_CREATED)
async def upload_source(
    session: Session,
    user: Maker,
    response: Response,
    file: Annotated[UploadFile, File(description="RBI Directions PDF, at most 20 MB")],
    title: Annotated[str, Form(min_length=1)],
    ref_no: Annotated[str | None, Form()] = None,
    issued_on: Annotated[date | None, Form()] = None,
    url: Annotated[str | None, Form()] = None,
) -> SourceIngestOut:
    # Read one byte past the limit so an oversized upload is caught without reading it all.
    data = await file.read(service.MAX_PDF_BYTES + 1)
    try:
        result = await service.ingest_pdf(
            session, data, title=title, ref_no=ref_no, issued_on=issued_on, url=url,
            uploaded_by=user.id,
        )
    except service.FileTooLarge as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
    except service.IngestError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await session.commit()

    report = result.report
    if report.duplicate:
        response.status_code = status.HTTP_200_OK  # nothing new was created
    return SourceIngestOut(
        doc_id=report.doc_id,
        sha3_256=report.sha3_256,
        duplicate=report.duplicate,
        report=IngestReportOut(
            pages=report.pages,
            paragraphs=report.paragraphs,
            unmatched=[asdict(u) for u in report.unmatched],
            removed=[asdict(r) for r in report.removed],
        ),
    )


@router.get("/sources/{doc_id}/paragraphs", response_model=list[ParagraphOut])
async def source_paragraphs(doc_id: uuid.UUID, session: Session, user: Maker) -> list:
    if await service.get_source_doc(session, doc_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source document not found")
    return await service.list_paragraphs(session, doc_id)
