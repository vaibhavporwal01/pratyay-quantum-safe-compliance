"""Append-only PQC ledger records. Public verification material is stored per entry."""
import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import BigInteger, DateTime, Identity, LargeBinary, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

class LedgerRecord(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = ({"schema": "trust"},)
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, server_default=text("gen_random_uuid()"))
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    previous_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    entry_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True, nullable=False)
    signature: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_id: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'ML-DSA-65'"))
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
