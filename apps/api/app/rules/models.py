"""rules: models."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

SCHEMA = "rules"
_UUID_DEFAULT = text("gen_random_uuid()")


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)


class SourceDoc(Base):
    __tablename__ = "source_docs"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    title: Mapped[str] = mapped_column(Text)
    ref_no: Mapped[str | None] = mapped_column(Text)
    issued_on: Mapped[date | None] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(Text)
    file: Mapped[bytes | None] = mapped_column(LargeBinary)
    # Unique: the same file is stored once (ingest relies on this under concurrent uploads).
    sha3_256: Mapped[bytes | None] = mapped_column(LargeBinary, index=True, unique=True)
    pages: Mapped[int | None] = mapped_column(Integer)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Paragraph(Base):
    __tablename__ = "paragraphs"
    __table_args__ = (
        CheckConstraint(
            "label IS NULL OR label IN ('requirement', 'definition', 'information')",
            name="label",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = _pk()
    doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.source_docs.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[str | None] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    label: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))


class RuleSet(Base):
    __tablename__ = "rule_sets"
    __table_args__ = (
        UniqueConstraint("org_id", "version"),
        CheckConstraint("status IN ('draft', 'published')", name="status"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = _pk()
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, server_default=text("'draft'"))
    published_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ledger_seq: Mapped[int | None] = mapped_column(BigInteger)


RULE_STATUSES = ("draft", "approved", "rejected", "retired")
TEMPLATES = (
    "max_amount",
    "max_ratio",
    "min_days",
    "time_window",
    "prohibited_charge",
    "required_disclosure",
)
APPLIES_TO = ("microfinance", "all")


class Rule(Base):
    __tablename__ = "rules"
    # Fetch server-set columns (updated_at on UPDATE) with RETURNING, so async code never
    # lazy-loads them.
    __mapper_args__: ClassVar[dict[str, Any]] = {"eager_defaults": True}
    __table_args__ = (
        UniqueConstraint("rule_set_id", "code"),
        CheckConstraint(f"status IN {RULE_STATUSES}", name="status"),
        CheckConstraint(f"template IN {TEMPLATES}", name="template"),
        CheckConstraint(f"applies_to IN {APPLIES_TO}", name="applies_to"),
        CheckConstraint("origin IN ('auto', 'manual')", name="origin"),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="effective_range",
        ),
        # Four eyes: the checker is never the maker.
        CheckConstraint("checked_by IS NULL OR checked_by <> made_by", name="maker_checker"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = _pk()
    # Set when the rule is published into a rule set (P5); null while in the library.
    rule_set_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.rule_sets.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    template: Mapped[str] = mapped_column(Text)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB)
    applies_to: Mapped[str] = mapped_column(Text, server_default=text("'all'"))
    # Null when the source gives no date we could verify.
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text, server_default=text("'draft'"), index=True)
    source_doc_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.source_docs.id"))
    source_para: Mapped[str] = mapped_column(Text)
    para_text: Mapped[str] = mapped_column(Text)
    # Other paragraphs that qualify this rule: [{"para", "text", "note"}].
    related: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    origin: Mapped[str] = mapped_column(Text)
    made_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    checked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    review_note: Mapped[str | None] = mapped_column(Text)
    supersedes_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.rules.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ChangeProposal(Base):
    __tablename__ = "change_proposals"
    __table_args__ = (
        CheckConstraint("kind IN ('new', 'amends', 'repeals')", name="kind"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="status"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = _pk()
    doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.source_docs.id", ondelete="CASCADE"), index=True
    )
    paragraph_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.paragraphs.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(Text)
    proposed: Mapped[dict[str, Any]] = mapped_column(JSONB)
    matched_words: Mapped[str | None] = mapped_column(Text)
    template: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    drafted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
