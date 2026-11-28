import hashlib
from app.trust.ledger import ZERO_HASH, _canonical

def test_canonical_payload_is_stable_and_sorted():
    a = _canonical(1, "decision", {"z": 2, "a": 1}, ZERO_HASH)
    b = _canonical(1, "decision", {"a": 1, "z": 2}, ZERO_HASH)
    assert a == b
    assert len(hashlib.sha3_256(a).digest()) == 32

def test_canonical_payload_binds_sequence_type_and_previous_hash():
    a = _canonical(1, "decision", {"x": 1}, ZERO_HASH)
    assert a != _canonical(2, "decision", {"x": 1}, ZERO_HASH)
    assert a != _canonical(1, "audit_finding", {"x": 1}, ZERO_HASH)
    assert a != _canonical(1, "decision", {"x": 1}, b"1" * 32)
