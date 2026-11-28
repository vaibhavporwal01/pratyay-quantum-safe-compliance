"""SHA3-256 chained, ML-DSA-65 signed append-only ledger."""
import base64
import hashlib
import json
import os
from dataclasses import dataclass, field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.trust.models import LedgerRecord

EVENT_TYPES = ("decision", "rule_set_published", "key_rotated", "audit_finding")
ZERO_HASH = bytes(32)
ALGORITHM = "ML-DSA-65"

@dataclass
class LedgerEntry:
    seq: int
    hash: bytes
    signature: bytes
    key_id: str

@dataclass
class VerifyReport:
    seq: int
    ok: bool
    checks: dict = field(default_factory=dict)

@dataclass
class ChainReport:
    ok: bool
    checked: int
    first_invalid_seq: int | None = None
    checks: dict = field(default_factory=dict)

def _keys():
    try:
        import oqs
    except ImportError as exc:
        raise RuntimeError("PQC provider unavailable; install liboqs-python and native liboqs") from exc
    private_value = os.environ.get("LEDGER_MLDSA_PRIVATE_KEY")
    public_value = os.environ.get("LEDGER_MLDSA_PUBLIC_KEY")
    if not private_value or not public_value:
        raise RuntimeError("Ledger signing keys are not configured")
    try:
        private = base64.b64decode(private_value, validate=True)
        public = base64.b64decode(public_value, validate=True)
    except ValueError as exc:
        raise RuntimeError("Ledger signing keys must be valid Base64") from exc
    if not private or not public:
        raise RuntimeError("Ledger signing keys are empty")
    return oqs, private, public

def _canonical(seq: int, event_type: str, payload: dict, previous_hash: bytes) -> bytes:
    envelope = {"seq": seq, "event_type": event_type, "payload": payload,
                "previous_hash": previous_hash.hex(), "algorithm": ALGORITHM}
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      default=str).encode("utf-8")

async def append(session: AsyncSession, event_type: str, payload: dict) -> LedgerEntry:
    if event_type not in EVENT_TYPES:
        raise ValueError("Unsupported ledger event type")
    oqs, private, public = _keys()
    # Serialize appenders so each transaction sees the preceding committed chain head.
    await session.execute(text("LOCK TABLE trust.ledger_entries IN EXCLUSIVE MODE"))
    previous = await session.scalar(select(LedgerRecord).order_by(LedgerRecord.seq.desc()).limit(1))
    previous_hash = previous.entry_hash if previous else ZERO_HASH
    record = LedgerRecord(event_type=event_type, payload=payload, previous_hash=previous_hash,
                          entry_hash=ZERO_HASH, signature=b"pending", key_id=hashlib.sha3_256(public).hexdigest()[:24],
                          algorithm=ALGORITHM, public_key=public)
    session.add(record)
    await session.flush()
    message = _canonical(record.seq, event_type, payload, previous_hash)
    with oqs.Signature(ALGORITHM, secret_key=private) as signer:
        signature = signer.sign(message)
    digest = hashlib.sha3_256(previous_hash + message + signature).digest()
    record.signature = signature
    record.entry_hash = digest
    await session.flush()
    return LedgerEntry(record.seq, digest, signature, record.key_id)

async def verify(session: AsyncSession, seq: int) -> VerifyReport:
    record = await session.get(LedgerRecord, seq)
    if record is None:
        return VerifyReport(seq, False, {"exists": False})
    prior = await session.scalar(select(LedgerRecord).where(LedgerRecord.seq < seq).order_by(LedgerRecord.seq.desc()).limit(1))
    expected_previous = prior.entry_hash if prior else ZERO_HASH
    message = _canonical(record.seq, record.event_type, record.payload, record.previous_hash)
    digest = hashlib.sha3_256(record.previous_hash + message + record.signature).digest()
    try:
        import oqs
        with oqs.Signature(record.algorithm) as verifier:
            signature_ok = verifier.verify(message, record.signature, record.public_key)
    except (ImportError, ValueError, RuntimeError):
        signature_ok = False
    checks = {"exists": True, "previous_hash": record.previous_hash == expected_previous,
              "entry_hash": digest == record.entry_hash, "signature": bool(signature_ok),
              "key_id": hashlib.sha3_256(record.public_key).hexdigest()[:24] == record.key_id}
    return VerifyReport(seq, all(checks.values()), checks)

async def verify_all(session: AsyncSession) -> ChainReport:
    rows = (await session.scalars(select(LedgerRecord).order_by(LedgerRecord.seq))).all()
    previous = ZERO_HASH
    for row in rows:
        message = _canonical(row.seq, row.event_type, row.payload, row.previous_hash)
        digest = hashlib.sha3_256(row.previous_hash + message + row.signature).digest()
        try:
            import oqs
            with oqs.Signature(row.algorithm) as verifier:
                sig_ok = verifier.verify(message, row.signature, row.public_key)
        except Exception:
            sig_ok = False
        checks = {"previous_hash": row.previous_hash == previous, "entry_hash": digest == row.entry_hash,
                  "signature": bool(sig_ok), "key_id": hashlib.sha3_256(row.public_key).hexdigest()[:24] == row.key_id}
        if not all(checks.values()):
            return ChainReport(False, len(rows), row.seq, checks)
        previous = row.entry_hash
    return ChainReport(True, len(rows), None, {"all_entries_valid": True})
