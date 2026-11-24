import logging

log = logging.getLogger("pratyay.stub")
from dataclasses import dataclass, field

EVENT_TYPES = ("decision", "rule_set_published", "key_rotated", "audit_finding")


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


async def append(session, event_type: str, payload: dict) -> LedgerEntry:
    """STUB until Pulkit's trust module lands (see docs/contracts.md)."""
    assert event_type in EVENT_TYPES
    log.warning("STUB ledger.append %s", event_type)
    return LedgerEntry(seq=0, hash=b"", signature=b"", key_id="stub")


async def verify(session, seq: int) -> VerifyReport:
    log.warning("STUB ledger.verify %s", seq)
    return VerifyReport(seq=seq, ok=True)
