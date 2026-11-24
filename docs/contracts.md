# Contracts between modules

Agreed by all four owners. Change only with the owner's review.

| Contract | Owner | Signature |
| --- | --- | --- |
| Current user | Vishnukant | `get_current_user() -> User(id, org_id, role, name)` |
| Role check | Vishnukant | `require_role(*roles)`; roles: borrower, officer, maker, checker, auditor, admin |
| Ledger append | Pulkit | `ledger.append(session, event_type, payload) -> LedgerEntry(seq, hash, signature, key_id)` inside the caller's transaction |
| Verify | Pulkit | `ledger.verify(session, seq) -> VerifyReport` and `ledger.verify_all(session) -> ChainReport` |
| Audit log | Lokesh | `audit.service.log_event(session, actor_id, action, target, meta)` |

Ledger event types: `decision`, `rule_set_published`, `key_rotated`, `audit_finding`.

Until a module is ready its owner keeps the stub in place. Stubs log `STUB`.

## identity.users (owner: Vishnukant)

Migration 0003 creates `identity.users (id, org_id, email unique, name, role, created_at)`, the
minimum the development stand-in needs. Vishnukant owns this table and will extend it (sign-in,
sessions, passwords are his). `app/identity/service.py` holds `get_user`, `user_names` and
`seed_dev_users` (one Lender A user per role at `@lender-a.in`).

## Development role stand-in (temporary)

`get_current_user()` keeps its signature. Until sign-in lands:

- `APP_ENV=development`: the user is the seeded Lender A user whose role is in the cookie
  `pratyay_dev_role`, falling back to `DEV_USER_ROLE` (default `maker`). The web masthead shows a
  role switcher that sets the cookie when `NEXT_PUBLIC_APP_ENV=development`.
- Any other `APP_ENV`: 401, nobody is signed in.
- `require_role(*roles)` now refuses other roles with 403.
- `GET /api/v1/me` returns the current user for the masthead.

Replace `get_current_user` and remove the cookie middleware in `app/main.py` when the real
identity module lands; callers do not change.
