# Contracts between modules

Agreed by all four owners. Change only with the owner's review.

| Contract | Owner | Signature |
| --- | --- | --- |
| Current user | Vishnukant | `get_current_user() -> User(id, org_id, role, name)` |
| Role check | Vishnukant | `require_role(*roles)`; roles: borrower, officer, maker, checker, auditor, admin |
| Ledger append | Pulkit | `ledger.append(session, event_type, payload) -> LedgerEntry(seq, hash, signature, key_id)` inside the caller's transaction |
| Verify | Pulkit | `ledger.verify(session, seq) -> VerifyReport` and `ledger.verify_all(session) -> ChainReport` |
| Audit log | Lokesh | `audit.service.log_event(session, actor_id, action, target, meta)` |
| Rule engine | Vaibhav | `rules.service.evaluate_application(session, facts, on_date) -> Evaluation` |

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

## Rule engine (owner: Vaibhav)

`evaluate_application(session, facts, on_date) -> Evaluation(on_date, outcome, microfinance,
results, rules_used, offer, kfs, notes)` in `app/rules/engine.py`, exported from
`app/rules/service.py`.

- Rules: approved, `effective_from <= on_date < effective_to` (no `effective_to`: in force).
- Only `stage = origination` rules are checked; servicing and recovery rules come back as
  `not_checked`. Microfinance rules are `not_applicable` unless MF-01 says the loan is one.
- Each result: `pass | fail | refer | not_checked | not_applicable`, computed values, the anchor
  ("CF para 55"), the paragraph text, rule id and version. A missing fact gives `refer`.
- `outcome`: `fail` if any rule fails, else `refer` if any refers, else `pass`.
- `offer` (MF-02 fail): the largest loan that fits, rounded down to the product's step.
- `kfs`: amount, tenor, rate, EMI, fees, APR (12 x monthly IRR on the unrounded EMI, RBC Annex
  I), validity date from KF-01 (weekends skipped, holidays not modelled).
- Facts (money in paise): `product_category, amount_paise, tenor_months, rate_bps_month, fees,
  prepayment_charge_paise, collateral, household_income_annual_paise,
  existing_monthly_repayments_paise, offer_step_paise`.

## loans (owner: Vaibhav, December)

The `loans` schema owns loan applications, engine evaluations, decisions and each
application's step history (`loans.events`) for December. The `origination` and `decision`
stubs are untouched. Each step calls `audit.service.log_event`. The final decision has a
`# HOOK(Pulkit)` in `app/loans/service.py` (`_sign_decision`) where `ledger.append(session,
"decision", payload)` goes; until then `ledger_seq` is null and pages show "Signature pending".

## identity.users.active

Migration 0005 adds `active boolean default true` for the admin Users page (read only).
Vishnukant's sign-in sets it.
