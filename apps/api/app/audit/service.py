"""Encrypted, persistent audit events. Never log plaintext metadata or secrets."""
import json
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.audit.models import AuditRecord
from app.core.crypto import data_encryption_key, encrypt_text

log = logging.getLogger("pratyay.audit")

async def log_event(session: AsyncSession, actor_id: UUID | None, action: str, target: str,
                    meta: dict | None = None) -> None:
    safe_meta = json.dumps(meta or {}, sort_keys=True, separators=(",", ":"), default=str)
    encrypted = encrypt_text(safe_meta, data_encryption_key(), "audit.events.meta")
    session.add(AuditRecord(actor_id=actor_id, action=action, target=target,
                            meta_ciphertext=encrypted))
    await session.flush()
