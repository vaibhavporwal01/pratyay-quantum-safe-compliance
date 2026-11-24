"""rules: schemas."""

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class SkippedLineOut(BaseModel):
    page: int
    text: str
    reason: str


class IngestReportOut(BaseModel):
    pages: int
    paragraphs: int
    unmatched: list[SkippedLineOut]
    removed: list[SkippedLineOut]


class SourceIngestOut(BaseModel):
    doc_id: uuid.UUID
    sha3_256: str
    duplicate: bool
    report: IngestReportOut


class ParagraphOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str | None
    page: int | None
    text: str
    label: str | None
    confidence: Decimal | None
