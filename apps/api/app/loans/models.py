"""loans: applications, rule evaluations, decisions and each application's step history.

Owned by Vaibhav for December (docs/contracts.md). Other modules' tables are referenced by
string foreign keys only; no other module's models are imported.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

SCHEMA = "loans"
_UUID_DEFAULT = text("gen_random_uuid()")

APP_STATUSES = ("evaluated", "recommended", "approved", "approved_modified", "rejected")
OUTCOMES = ("pass", "fail", "refer")
RECOMMENDATIONS = ("approve", "approve_modified", "reject")
FINAL = ("approved", "approved_modified", "rejected")


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)


def _now() -> Mapped[datetime]:
    # clock_timestamp, not now(): several steps in one transaction must keep their order.
    return mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(f"status IN {APP_STATUSES}", name="status"),
        CheckConstraint("amount_paise > 0", name="amount"),
        CheckConstraint("tenor_months > 0", name="tenor"),
        CheckConstraint("rate_bps_month >= 0", name="rate"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = _pk()
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    ref: Mapped[str] = mapped_column(Text, unique=True)
    # The borrower's user, when they applied themselves; null when an officer keyed it in.
    borrower_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    borrower_name: Mapped[str] = mapped_column(Text)
    purpose: Mapped[str | None] = mapped_column(Text)
    product: Mapped[str] = mapped_column(Text)
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    tenor_months: Mapped[int] = mapped_column(Integer)
    rate_bps_month: Mapped[int] = mapped_column(Integer)
    # [{"name", "bps" | "paise", "payable_to", "assumed"}], copied from the product.
    fees: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    prepayment_charge_paise: Mapped[int | None] = mapped_column(BigInteger)
    collateral: Mapped[bool | None] = mapped_column(Boolean)
    household_income_annual_paise: Mapped[int | None] = mapped_column(BigInteger)
    existing_monthly_repayments_paise: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(Text, index=True)
    submitted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(),
        onupdate=func.clock_timestamp(),
    )


class Evaluation(Base):
    """A snapshot of one engine run: every result, and the rule ids and versions used."""

    __tablename__ = "evaluations"
    __table_args__ = (
        CheckConstraint(f"outcome IN {OUTCOMES}", name="outcome"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = _pk()
    # Insert order. Timestamps can tie (seeded steps share a time); this never does.
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), unique=True)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.applications.id", ondelete="CASCADE"), index=True
    )
    on_date: Mapped[date] = mapped_column(Date)
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    outcome: Mapped[str] = mapped_column(Text)
    microfinance: Mapped[bool | None] = mapped_column(Boolean)
    results: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    rules_used: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    offer: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    kfs: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    facts: Mapped[dict[str, Any]] = mapped_column(JSONB)
    run_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = _now()


class Decision(Base):
    """The officer's recommendation and the checker's decision. Four eyes: never one user."""

    __tablename__ = "decisions"
    __table_args__ = (
        CheckConstraint(f"recommendation IN {RECOMMENDATIONS}", name="recommendation"),
        CheckConstraint(f"outcome IS NULL OR outcome IN {FINAL}", name="outcome"),
        CheckConstraint("checker_id IS NULL OR checker_id <> officer_id", name="four_eyes"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = _pk()
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.applications.id", ondelete="CASCADE"), unique=True
    )
    recommendation: Mapped[str] = mapped_column(Text)
    recommended_paise: Mapped[int | None] = mapped_column(BigInteger)
    officer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    officer_note: Mapped[str | None] = mapped_column(Text)
    recommended_at: Mapped[datetime] = _now()
    outcome: Mapped[str | None] = mapped_column(Text)
    approved_paise: Mapped[int | None] = mapped_column(BigInteger)
    checker_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    checker_note: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # The evaluation at the final amount, stored when the checker decides.
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.evaluations.id")
    )
    # HOOK(Pulkit): set from ledger.append(...) when signing lands. Null: signature pending.
    ledger_seq: Mapped[int | None] = mapped_column(BigInteger)


class Event(Base):
    """Each step on an application, in order. Written next to audit.service.log_event so the
    officer, checker and auditor pages have a history before the audit module lands."""

    __tablename__ = "events"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    # Insert order: the step history is read in this order, never by timestamp.
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), unique=True)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.applications.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = _now()
