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
