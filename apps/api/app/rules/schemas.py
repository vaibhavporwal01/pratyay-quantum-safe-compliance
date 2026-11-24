"""rules: schemas."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


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
    classified: bool = False
    report: IngestReportOut


class ParagraphOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str | None
    page: int | None
    text: str
    label: str | None
    confidence: Decimal | None


# ---- sources ---------------------------------------------------------------------------


class SourceDocOut(BaseModel):
    id: uuid.UUID
    title: str
    short_code: str | None
    ref_no: str | None
    issued_on: date | None
    url: str | None
    sha3_256: str | None
    pages: int | None
    uploaded_at: datetime
    paragraphs: int
    labels: dict[str, int]
    needs_review: int
    rules: dict[str, int]


# ---- values and templates --------------------------------------------------------------


class ValueOut(BaseModel):
    kind: str
    value: int | str
    text: str
    start: int
    end: int
    unit: str | None = None


class SuggestionOut(BaseModel):
    paragraph: ParagraphOut
    doc_id: uuid.UUID
    template: str
    params: dict[str, Any]
    missing: list[str]
    values: list[ValueOut]


class BoundaryTestOut(BaseModel):
    label: str
    facts: dict[str, Any]
    expected: bool
    actual: bool
    passed: bool


class CheckIn(BaseModel):
    template: str
    params: dict[str, Any]
    paragraph_id: uuid.UUID
    related: list["RelatedIn"] = []


class CheckOut(BaseModel):
    problems: list[str]
    missing: list[str]
    tests: list[BoundaryTestOut]


# ---- rules -----------------------------------------------------------------------------

Code = Annotated[str, Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9-]*$")]


class RelatedIn(BaseModel):
    para: str = Field(min_length=1)
    note: str = ""


class RelatedOut(BaseModel):
    para: str
    text: str
    note: str


class RuleCreate(BaseModel):
    code: Code
    title: str = Field(min_length=1, max_length=200)
    template: str
    params: dict[str, Any]
    applies_to: str = "all"
    effective_from: date | None = None
    paragraph_id: uuid.UUID
    section: str | None = Field(default=None, max_length=200)
    related: list[RelatedIn] = []
    origin: str = Field(default="manual", pattern="^(auto|manual)$")


class RuleUpdate(BaseModel):
    code: Code | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    template: str | None = None
    params: dict[str, Any] | None = None
    applies_to: str | None = None
    effective_from: date | None = None
    section: str | None = Field(default=None, max_length=200)
    related: list[RelatedIn] | None = None


class ReviewIn(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class RuleOut(BaseModel):
    id: uuid.UUID
    code: str
    title: str
    template: str
    params: dict[str, Any]
    applies_to: str
    effective_from: date | None
    effective_to: date | None
    status: str
    source_doc_id: uuid.UUID
    source_doc_title: str
    source_doc_code: str | None
    source_doc_ref: str | None
    source_para: str
    para_text: str
    section: str | None
    related: list[RelatedOut]
    origin: str
    made_by: uuid.UUID
    made_by_name: str | None
    checked_by: uuid.UUID | None
    checked_by_name: str | None
    review_note: str | None
    created_at: datetime
    updated_at: datetime
    checked_at: datetime | None
    missing: list[str]
    problems: list[str]
    tests: list[BoundaryTestOut]


class OverviewOut(BaseModel):
    counts: dict[str, int]
    sources: int
    waiting_for_you: list[RuleOut]
    recently_checked: list[RuleOut]


CheckIn.model_rebuild()
