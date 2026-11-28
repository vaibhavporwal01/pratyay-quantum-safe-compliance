"""Persistent audit trail; metadata is encrypted before it reaches the database."""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, LargeBinary, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

class AuditRecord(Base):
    __tablename__ = "events"
    __table_args__ = ({"schema": "audit"},)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    action: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    meta_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
