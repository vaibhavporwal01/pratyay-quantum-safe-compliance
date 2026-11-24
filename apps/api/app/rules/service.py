"""rules: service. The only entry point other modules (and the router) use."""

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rules.ingest import (
    MAX_PDF_BYTES,
    FileTooLarge,
    IngestError,
    IngestReport,
    IngestResult,
    ingest_pdf,
)
from app.rules.models import Paragraph, SourceDoc

__all__ = [
    "MAX_PDF_BYTES",
    "FileTooLarge",
    "IngestError",
    "IngestReport",
    "IngestResult",
    "get_source_doc",
    "ingest_pdf",
    "list_paragraphs",
    "paragraph_sort_key",
]


async def get_source_doc(session: AsyncSession, doc_id: uuid.UUID) -> SourceDoc | None:
    return await session.get(SourceDoc, doc_id)


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
