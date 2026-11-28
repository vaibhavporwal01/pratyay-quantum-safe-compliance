"""Read-only trust and PQC ledger endpoints for the admin and auditor consoles."""
import base64
import hashlib
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.identity.deps import User, require_role
from app.trust import ledger
from app.trust.models import LedgerRecord

router = APIRouter(prefix="/trust", tags=["trust"])
Session = Annotated[AsyncSession, Depends(get_session)]
Oversight = Annotated[User, Depends(require_role("admin", "auditor"))]


def _provider_status() -> tuple[bool, list[str]]:
    try:
        import oqs
        enabled = list(oqs.get_enabled_sig_mechanisms())
        return "ML-DSA-65" in enabled, enabled
    except (ImportError, OSError, RuntimeError):
        return False, []


@router.get("/status")
async def trust_status(session: Session, user: Oversight) -> dict:
    """Expose public metadata and readiness only; never return private signing material."""
    pqc_available, algorithms = _provider_status()
    private_set = bool(os.environ.get("LEDGER_MLDSA_PRIVATE_KEY"))
    public_value = os.environ.get("LEDGER_MLDSA_PUBLIC_KEY")
    public = None
    if public_value:
        try:
            public = base64.b64decode(public_value, validate=True)
        except ValueError:
            public = None
    count = await session.scalar(select(func.count()).select_from(LedgerRecord))
    latest = await session.scalar(select(LedgerRecord).order_by(LedgerRecord.seq.desc()).limit(1))
    key_id = hashlib.sha3_256(public).hexdigest()[:24] if public else None
    return {
        "encryption": {"algorithm": "AES-256-GCM", "configured": bool(os.environ.get("DATA_ENCRYPTION_KEY"))},
        "email_index": {"algorithm": "HMAC-SHA-256", "configured": bool(os.environ.get("EMAIL_HMAC_KEY"))},
        "hash": {"algorithm": "SHA3-256", "enabled": True},
        "signature": {
            "algorithm": "ML-DSA-65", "standard": "FIPS 204",
            "provider_available": pqc_available, "private_key_configured": private_set,
            "public_key_configured": public is not None, "enabled": pqc_available and private_set and public is not None,
            "key_id": key_id, "public_key_bytes": len(public) if public else None,
            "available_signature_algorithms": algorithms,
        },
        "ledger": {"entries": int(count or 0), "latest_seq": latest.seq if latest else None},
    }


@router.get("/ledger/verify")
async def verify_chain(session: Session, user: Oversight) -> dict:
    """Verify every persisted ledger entry; read-only."""
    try:
        report = await ledger.verify_all(session)
    except (RuntimeError, ImportError) as exc:
        raise HTTPException(503, "PQC verification is not configured on this API instance") from exc
    return {
        "ok": report.ok,
        "checked": report.checked,
        "first_invalid_seq": report.first_invalid_seq,
        "checks": report.checks,
    }


@router.get("/ledger")
async def list_ledger(session: Session, user: Oversight, limit: int = 50) -> list[dict]:
    limit = max(1, min(limit, 100))
    rows = (await session.scalars(
        select(LedgerRecord).order_by(LedgerRecord.seq.desc()).limit(limit)
    )).all()
    return [{
        "seq": row.seq, "event_type": row.event_type, "hash": row.entry_hash.hex(),
        "previous_hash": row.previous_hash.hex(), "signature_bytes": len(row.signature),
        "algorithm": row.algorithm, "key_id": row.key_id,
        "public_key_bytes": len(row.public_key), "created_at": row.created_at,
    } for row in rows]
