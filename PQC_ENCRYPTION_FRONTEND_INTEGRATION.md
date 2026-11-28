# Pratyay PQC + encryption integration patch

This patch adds a live, read-only trust status API and wires the Crypto Lab, Admin Signing Keys,
and Auditor Ledger verification banner to it. It does not expose private signing keys.

## API additions
- `GET /api/v1/trust/status` (admin/auditor): encryption/HMAC configuration, PQC provider
  readiness, public signing-key fingerprint and ledger count.
- `GET /api/v1/trust/ledger/verify` (admin/auditor): verifies the complete persisted ledger.
- `GET /api/v1/trust/ledger` (admin/auditor): returns public ledger metadata only.

## Required runtime secrets
Set independent values in the API environment:
- `DATA_ENCRYPTION_KEY`: Base64 of 32 random bytes (AES-256-GCM).
- `EMAIL_HMAC_KEY`: Base64 of at least 32 random bytes.
- `LEDGER_MLDSA_PUBLIC_KEY` and `LEDGER_MLDSA_PRIVATE_KEY`: generated using
  `apps/api/scripts/generate_pqc_keys.py` inside the PQC-enabled API image.

Do not commit `.env`, key output, or private signing keys. Use your secret manager in production.
Keep keys stable across restarts. Back up the private signing key securely; losing it prevents
future signing with that key, though old records retain their public verification key.

## Apply
Copy the patch contents over the same paths in the repository root. Keep your branch unchanged.
The patch is designed for the current snapshot that already contains migration `0009_audit_pqc_ledger`.

## Important scope / migration gate
The current source still stores identity email and loan application facts in their existing
database columns. The existing AES-GCM utility and audit metadata encryption are present, but
the loan/identity field-at-rest rollout needs a separate additive schema and dual-read/write
migration plan (including the unique email blind index) before those fields can safely be
encrypted. This patch does not claim those fields are encrypted. Do not run migration `0009`
until local database backup, configured keys, API tests, and migration review are complete.
