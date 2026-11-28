"""AES-256-GCM encryption and HMAC blind indexes."""

import base64
import hashlib
import hmac
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

PREFIX = "enc:v1:"
NONCE_BYTES = 12
KEY_BYTES = 32


class CryptoIntegrityError(ValueError):
    """Encrypted data failed authentication."""


def decode_key(value: str, name: str) -> bytes:
    try:
        key = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValueError(f"{name} must be valid Base64") from exc

    if len(key) != KEY_BYTES:
        raise ValueError(f"{name} must decode to exactly 32 bytes")

    return key


def _configured_key(name: str) -> bytes:
    setting_name = {
        "DATA_ENCRYPTION_KEY": "data_encryption_key",
        "EMAIL_HMAC_KEY": "email_hmac_key",
    }.get(name)

    value = getattr(settings, setting_name, None) if setting_name else None
    if not value:
        raise RuntimeError(f"Missing security configuration: {name}")
    return decode_key(value, name)


def data_encryption_key() -> bytes:
    return _configured_key("DATA_ENCRYPTION_KEY")


def email_index_key() -> bytes:
    return _configured_key("EMAIL_HMAC_KEY")


def encrypt_text(value: str | None, key: bytes, aad: str) -> str | None:
    if value is None:
        return None
    if len(key) != KEY_BYTES:
        raise ValueError("AES-256-GCM requires a 32-byte key")
    if not aad:
        raise ValueError("AAD must identify the table and column")

    nonce = os.urandom(NONCE_BYTES)
    encrypted = AESGCM(key).encrypt(
        nonce, value.encode("utf-8"), aad.encode("utf-8")
    )
    payload = base64.b64encode(nonce + encrypted).decode("ascii")
    return PREFIX + payload


def decrypt_text(value: str | None, key: bytes, aad: str) -> str | None:
    if value is None:
        return None

    if not value.startswith(PREFIX):
        return value  # Legacy plaintext during staged migration.

    if len(key) != KEY_BYTES:
        raise ValueError("AES-256-GCM requires a 32-byte key")

    try:
        payload = base64.b64decode(value[len(PREFIX):], validate=True)
        if len(payload) <= NONCE_BYTES:
            raise ValueError("Ciphertext is too short")

        nonce = payload[:NONCE_BYTES]
        ciphertext = payload[NONCE_BYTES:]
        plaintext = AESGCM(key).decrypt(
            nonce, ciphertext, aad.encode("utf-8")
        )
        return plaintext.decode("utf-8")
    except (InvalidTag, ValueError, UnicodeDecodeError) as exc:
        raise CryptoIntegrityError(
            "Encrypted value failed authentication"
        ) from exc


def email_blind_index(email: str, key: bytes) -> bytes:
    if len(key) < KEY_BYTES:
        raise ValueError("HMAC key must contain at least 32 bytes")

    normalized = email.strip().casefold().encode("utf-8")
    return hmac.new(key, normalized, hashlib.sha256).digest()
