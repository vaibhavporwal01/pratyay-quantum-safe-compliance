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

## Sign-in and sessions (identity, owner: Vishnukant; email and password built by Vaibhav)

Vishnukant extends this with TOTP for staff and mobile OTP for borrowers. Signatures of
`get_current_user()` and `require_role(*roles)` are unchanged.

- Migration 0007: `identity.users` gains `password_hash` (Argon2id, argon2-cffi),
  `failed_attempts`, `locked_until`. `identity.sessions (id, token_sha256 unique, user_id,
  created_at, last_seen_at, expires_at)` stores only the SHA-256 of a random 32-byte token.
- `POST /api/identity/sign-in {email, password}` -> `{user}` and sets cookie `pratyay_session`
  (httpOnly, SameSite=Lax, Secure when APP_ENV=production, path=/). One 401 message for unknown
  email, wrong password, inactive or locked account. `LOCKOUT_ATTEMPTS` (5) failures lock the
  account for `LOCKOUT_MINUTES` (15).
- Sessions end after `SESSION_IDLE_MINUTES` (15) without a request or `SESSION_ABSOLUTE_HOURS`
  (12) after sign-in. `POST /api/identity/sign-out` deletes the session and the cookie.
- `GET /api/v1/me` reads the session. `get_current_user`: a live session always wins; only
  without one does the "Act as" stand-in apply (APP_ENV=development or ALLOW_ROLE_SWITCHER=true).
- Audit: `sign_in`, `sign_in_failed` (meta `locked`), `sign_out` via `audit.service.log_event`.
- CSRF guard (`app/core/csrf.py`): POST/PUT/PATCH/DELETE must be `application/json`; the
  multipart PDF upload (`/api/v1/rules/sources`) must carry `Origin` equal to ALLOWED_ORIGIN.
- Seed: `SEED_PASSWORD` (required, never committed or printed) on the six Lender A users.
- Web: `proxy.ts` sends signed-out visitors on app pages to `/sign-in?next=`. Mobile OTP and the
  authenticator screens stay behind `NEXT_PUBLIC_ENABLE_OTP` (sample calls in `lib/api/auth.ts`).

## identity.users (owner: Vishnukant)

Migration 0003 creates `identity.users (id, org_id, email unique, name, role, created_at)`, the
minimum the development stand-in needs. Vishnukant owns this table and will extend it (sign-in,
sessions, passwords are his). `app/identity/service.py` holds `get_user`, `user_names` and
`seed_dev_users` (one Lender A user per role at `@lender-a.in`).

## Development role stand-in

Applies only when the request has no live session (see Sign-in and sessions):

- `APP_ENV=development`: the user is the seeded Lender A user whose role is in the cookie
  `pratyay_dev_role`, falling back to `DEV_USER_ROLE` (default `maker`). The web masthead shows a
  role switcher that sets the cookie when `NEXT_PUBLIC_APP_ENV=development`.
- Any other `APP_ENV` (and ALLOW_ROLE_SWITCHER false): 401 unless signed in.
- `require_role(*roles)` now refuses other roles with 403.
- `GET /api/v1/me` returns the current user for the masthead.

**Showcase flag, temporary (Vishnukant: remove when login lands).** `ALLOW_ROLE_SWITCHER=true`
(API) and `NEXT_PUBLIC_ALLOW_ROLE_SWITCHER=true` (web) make the "Act as" switcher and the
cookie stand-in work outside development, so the deployed site can be shown before sign-in
exists. Both default to false. Remove both flags, `stand_in_enabled()` in
`app/identity/deps.py` and the check in `components/app/DevRoleSwitcher.tsx` with the stand-in.

## Rule engine (owner: Vaibhav)

`evaluate_application(session, facts, on_date) -> Evaluation(on_date, outcome, microfinance,
results, rules_used, offer, kfs, notes)` in `app/rules/engine.py`, exported from
`app/rules/service.py`.

- Rules: approved, `effective_from <= on_date < effective_to` (no `effective_to`: in force).
- Evaluation is by template; no rule code appears in engine logic. Each template reads the
  fact(s) named in its params from the fact catalogue (`app/rules/facts.py`, `GET
  /api/v1/rules/facts`): `max_amount {fact, max_paise, must_be_false?, decides_scope?}`,
  `max_ratio {numerator_fact, denominator_fact, max_percent, offer_on_fail}`,
  `min_days {fact, tiers}`, `prohibited_charge {fact}`, `required_disclosure {item, fact}`,
  `time_window {start, end}` (recovery: not checked on an application). A fact outside the
  catalogue (or none) can be approved but evaluates as `refer` ("Fact not in catalogue").
- Migration 0008 only added these fields to the seeded rules; no number changed.
- Only `stage = origination` rules are checked; servicing and recovery rules come back as
  `not_checked`. Microfinance rules are `not_applicable` unless the rule with `decides_scope` (MF-01)
  says the loan is one.
- Each result: `pass | fail | refer | not_checked | not_applicable`, computed values, the anchor
  ("CF para 55"), the paragraph text, rule id and version. A missing fact gives `refer`.
- `outcome`: `fail` if any rule fails, else `refer` if any refers, else `pass`.
- `offer` (MF-02 fail): the largest loan that fits, rounded down to the product's step.
- `kfs`: amount, tenor, rate, EMI, fees, APR (12 x monthly IRR on the unrounded EMI, RBC Annex
  I), validity date from KF-01 (weekends skipped, holidays not modelled).
- Facts (money in paise): `product_category, amount_paise, tenor_months, rate_bps_month, fees,
  prepayment_charge_paise, collateral, household_income_annual_paise,
  existing_monthly_repayments_paise, offer_step_paise`.

## Public worked example

`GET /api/v1/loans/worked-example`: no sign-in, read only, saves nothing. The fictional
APP-2026-0142 facts (from `app/loans/seed.py`) through `loans.service.preview`, at the asked
amount and at the offer, on its submission date. Cached in process for five minutes
(`Cache-Control: public, max-age=300`). The landing page renders every example figure from it.

## loans (owner: Vaibhav, December)

The `loans` schema owns loan applications, engine evaluations, decisions and each
application's step history (`loans.events`) for December. The `origination` and `decision`
stubs are untouched. Each step calls `audit.service.log_event`. The final decision has a
`# HOOK(Pulkit)` in `app/loans/service.py` (`_sign_decision`) where `ledger.append(session,
"decision", payload)` goes; until then `ledger_seq` is null and pages show "Signature pending".

## identity.users.active

Migration 0005 adds `active boolean default true` for the admin Users page (read only).
Vishnukant's sign-in sets it.
