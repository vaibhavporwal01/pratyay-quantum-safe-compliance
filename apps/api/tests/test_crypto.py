import pytest

from app.core.crypto import (
    CryptoIntegrityError,
    decrypt_text,
    email_blind_index,
    encrypt_text,
)


def test_encryption_round_trip():
    key = b"a" * 32
    encrypted = encrypt_text(
        "borrower@example.com", key, "identity.users.email"
    )
    assert encrypted != "borrower@example.com"
    assert decrypt_text(
        encrypted, key, "identity.users.email"
    ) == "borrower@example.com"


def test_random_nonce():
    key = b"a" * 32
    first = encrypt_text("same-value", key, "loans.applications.name")
    second = encrypt_text("same-value", key, "loans.applications.name")
    assert first != second


def test_wrong_key_rejected():
    encrypted = encrypt_text("secret", b"a" * 32, "identity.users.email")
    with pytest.raises(CryptoIntegrityError):
        decrypt_text(encrypted, b"b" * 32, "identity.users.email")


def test_wrong_aad_rejected():
    encrypted = encrypt_text("secret", b"a" * 32, "identity.users.email")
    with pytest.raises(CryptoIntegrityError):
        decrypt_text(encrypted, b"a" * 32, "identity.users.name")


def test_tampering_rejected():
    encrypted = encrypt_text("secret", b"a" * 32, "identity.users.email")
    tampered = encrypted[:-1] + ("A" if encrypted[-1] != "A" else "B")
    with pytest.raises(CryptoIntegrityError):
        decrypt_text(tampered, b"a" * 32, "identity.users.email")


def test_email_blind_index_normalizes():
    key = b"h" * 32
    assert email_blind_index(" User@Example.com ", key) == (
        email_blind_index("user@example.com", key)
    )


def test_different_emails_have_different_indexes():
    key = b"h" * 32
    assert email_blind_index("one@example.com", key) != (
        email_blind_index("two@example.com", key)
    )


def test_legacy_plaintext_readable():
    assert decrypt_text(
        "legacy-value", b"a" * 32, "identity.users.email"
    ) == "legacy-value"
