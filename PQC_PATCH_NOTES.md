# Initial PQC / audit integration patch

This patch adds persistent audit storage with AES-GCM encrypted metadata, an append-only trust ledger, ML-DSA-65 signing and SHA3-256 chain verification, migration 0009, and wires final loan decisions to the ledger.

## Required environment values

Generate independent 32-byte random keys and Base64 encode them for `DATA_ENCRYPTION_KEY` and `EMAIL_HMAC_KEY`. Generate an ML-DSA-65 keypair using the pinned liboqs provider and Base64 encode the raw private/public key bytes into `LEDGER_MLDSA_PRIVATE_KEY` and `LEDGER_MLDSA_PUBLIC_KEY`. Do not commit real keys. Keep private signing keys in a secret manager in production.

## Apply locally

1. Copy the changed files into the same relative paths in your feature branch.
2. Set the four local environment variables (never paste them into chat).
3. Run `uv run ruff check .` and `uv run pytest -q`.
4. With the local database only, run `uv run alembic upgrade head`.
5. Run the loan flow and verify the resulting ledger entries.

## Scope / important remaining work

This is the first integration slice, not the complete encryption rollout. Existing identity and loan columns remain compatible and are not yet transparently encrypted at rest. The next migration must add encrypted shadow columns and HMAC email indexes, dual-write and backfill existing data, switch service reads/login to decrypted values, and only later retire plaintext columns. API endpoints and frontend views for key inventory, ledger verification and Crypto Lab are also still to be connected. Do not deploy this patch to production until key provisioning, migration/backfill, API authorization, integration tests and independent cryptographic review are complete.
