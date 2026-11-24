"""decision: models.

Foreign keys to other modules use string targets only; no other module's models are imported.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

SCHEMA = "decision"


class Decision(Base):
    __tablename__ = "decisions"
    __table_args__ = (
        CheckConstraint("outcome IN ('pass', 'refer', 'fail')", name="outcome"),
        CheckConstraint("checker_id IS NULL OR checker_id <> maker_id", name="maker_checker"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("origination.applications.id"), index=True
    )
    rule_set_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rules.rule_sets.id"))
    outcome: Mapped[str] = mapped_column(Text)
    offered_paise: Mapped[int | None] = mapped_column(BigInteger)
    maker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    checker_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    ledger_seq: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RuleResult(Base):
    __tablename__ = "rule_results"
    __table_args__ = (
        CheckConstraint(
            "result IN ('pass', 'fail', 'refer', 'not_applicable')", name="result"
        ),
        {"schema": SCHEMA},
    )

    decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.decisions.id", ondelete="CASCADE"), primary_key=True
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rules.rules.id"), primary_key=True)
    result: Mapped[str] = mapped_column(Text)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
