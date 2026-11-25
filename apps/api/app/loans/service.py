"""loans: service. The only entry point the router, the seed and other modules use.

    borrower or officer submits ─▶ engine runs, snapshot stored ─▶ status "evaluated"
    officer recommends (approve | approve_modified | reject) ─▶ "recommended"
    checker approves, modifies or rejects with a note ─▶ approved | approved_modified | rejected

The officer and the checker on one decision are different users (checked here and by the
database). Every step is written to the audit log (audit.service.log_event) and to the
application's own history (loans.events). Approving at an amount reruns the engine at that
amount and refuses unless every origination rule passes.
"""

import uuid
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.identity import service as identity
from app.identity.deps import User
from app.loans.models import FINAL, Application, Decision, Evaluation, Event
from app.loans.products import PRODUCTS, get_product
from app.rules import service as rules

STAFF_ROLES = ("officer", "checker", "auditor", "admin")


class LoanError(ValueError):
    """The action is not allowed on this application (409)."""


class NotFound(LookupError):
    pass


class SameUser(LoanError):
    """The checker would also be the officer (403)."""


class Invalid(LoanError):
    """The request itself is wrong (422)."""


LENDER_TZ = ZoneInfo("Asia/Kolkata")


def today() -> date:
    """The lender's calendar date (IST): rules' effective dates and KFS validity use it."""
    return datetime.now(LENDER_TZ).date()


def day_of(at: datetime | None) -> date:
    """The lender's calendar date of a step: its own date when it has a fixed time."""
    return at.astimezone(LENDER_TZ).date() if at else today()


def _stamp(column: str, at: datetime | None) -> dict[str, datetime]:
    """A fixed time for a timestamp column, or nothing (the database clock fills it)."""
    return {column: at} if at else {}


# ---- helpers -----------------------------------------------------------------------------


async def _log(session: AsyncSession, actor_id: uuid.UUID, app: Application, action: str,
               meta: dict[str, Any] | None = None, at: datetime | None = None) -> None:
    meta = meta or {}
    session.add(Event(application_id=app.id, actor_id=actor_id, action=action, meta=meta,
                      **_stamp("created_at", at)))
    await session.flush()
    await audit.log_event(session, actor_id, f"loan.{action}", f"application:{app.ref}", meta)


def facts_for(app: Application, amount_paise: int | None = None) -> dict[str, Any]:
    product = get_product(app.product) or {}
    return {
        "product_category": product.get("category"),
        "amount_paise": amount_paise or app.amount_paise,
        "tenor_months": app.tenor_months,
        "rate_bps_month": app.rate_bps_month,
        "fees": app.fees,
        "prepayment_charge_paise": app.prepayment_charge_paise,
        "collateral": app.collateral,
        "household_income_annual_paise": app.household_income_annual_paise,
        "existing_monthly_repayments_paise": app.existing_monthly_repayments_paise,
        "offer_step_paise": product.get("offer_step_paise"),
    }


async def _evaluate(session: AsyncSession, app: Application, actor: User,
                    amount_paise: int | None = None, on_date: date | None = None,
                    at: datetime | None = None) -> Evaluation:
    facts = facts_for(app, amount_paise)
    result = await rules.evaluate_application(session, facts, on_date or day_of(at))
    row = Evaluation(
        application_id=app.id, on_date=date.fromisoformat(result.on_date),
        amount_paise=facts["amount_paise"], outcome=result.outcome,
        microfinance=result.microfinance, results=result.as_dict()["results"],
        rules_used=result.rules_used, offer=result.offer, kfs=result.kfs, facts=facts,
        run_by=actor.id, **_stamp("created_at", at),
    )
    session.add(row)
    await session.flush()
    await _log(session, actor.id, app, "evaluated", {
        "evaluation_id": str(row.id), "amount_paise": row.amount_paise, "outcome": row.outcome,
        "rules": [f"{r['code']} v{r['version']}" for r in row.rules_used],
    }, at)
    return row


async def next_ref(session: AsyncSession, year: int) -> str:
    prefix = f"APP-{year}-"
    last = await session.scalar(
        select(func.max(Application.ref)).where(Application.ref.like(f"{prefix}%"))
    )
    n = int(last.removeprefix(prefix)) + 1 if last else 1
    return f"{prefix}{n:04d}"


# ---- reads -------------------------------------------------------------------------------


def list_products() -> list[dict[str, Any]]:
    return list(PRODUCTS.values())


async def get_application(session: AsyncSession, user: User, app_id: uuid.UUID) -> Application:
    app = await session.get(Application, app_id)
    if app is None or app.org_id != user.org_id:
        raise NotFound("Application not found")
    if user.role == "borrower" and app.borrower_id != user.id:
        raise NotFound("Application not found")
    return app


async def latest_evaluation(session: AsyncSession, app: Application) -> Evaluation | None:
    """The latest engine run at the amount asked for. Runs at a modified amount are the
    decision's (final_evaluation)."""
    return await session.scalar(
        select(Evaluation)
        .where(Evaluation.application_id == app.id, Evaluation.amount_paise == app.amount_paise)
        .order_by(Evaluation.seq.desc()).limit(1)
    )


async def get_decision(session: AsyncSession, app_id: uuid.UUID) -> Decision | None:
    return await session.scalar(select(Decision).where(Decision.application_id == app_id))


async def list_applications(
    session: AsyncSession, user: User, statuses: tuple[str, ...] | None = None
) -> list[dict[str, Any]]:
    q = select(Application).where(Application.org_id == user.org_id)
    if user.role == "borrower":
        q = q.where(Application.borrower_id == user.id)
    if statuses:
        q = q.where(Application.status.in_(statuses))
    apps = list(await session.scalars(q.order_by(Application.created_at.desc(), Application.ref)))
    return [await summary(session, a) for a in apps]


async def summary(session: AsyncSession, app: Application) -> dict[str, Any]:
    ev = await latest_evaluation(session, app)
    dec = await get_decision(session, app.id)
    first_problem = None
    if ev:
        bad = [r for r in ev.results if r["status"] in ("fail", "refer")]
        first_problem = f"{bad[0]['code']} {bad[0]['status']}" if bad else None
    return {
        **_app_dict(app),
        "outcome": ev.outcome if ev else None,
        "first_problem": first_problem,
        "offer_paise": (ev.offer or {}).get("amount_paise") if ev else None,
        "approved_paise": dec.approved_paise if dec else None,
        "recommendation": dec.recommendation if dec else None,
        "signed": bool(dec and dec.ledger_seq is not None),
    }


def _app_dict(app: Application) -> dict[str, Any]:
    product = get_product(app.product) or {}
    return {
        c: getattr(app, c) for c in (
            "id", "ref", "borrower_id", "borrower_name", "purpose", "product", "amount_paise",
            "tenor_months", "rate_bps_month", "fees", "prepayment_charge_paise", "collateral",
            "household_income_annual_paise", "existing_monthly_repayments_paise", "status",
            "submitted_by", "created_at", "updated_at",
        )
    } | {"product_name": product.get("name", app.product)}


def evaluation_dict(ev: Evaluation | None) -> dict[str, Any] | None:
    if ev is None:
        return None
    return {c: getattr(ev, c) for c in (
        "id", "on_date", "amount_paise", "outcome", "microfinance", "results", "rules_used",
        "offer", "kfs", "run_by", "created_at",
    )}


async def detail(session: AsyncSession, app: Application) -> dict[str, Any]:
    ev = await latest_evaluation(session, app)
    dec = await get_decision(session, app.id)
    events = list(await session.scalars(
        select(Event).where(Event.application_id == app.id).order_by(Event.seq)
    ))
    ids = {e.actor_id for e in events} | {app.submitted_by}
    if dec:
        ids |= {dec.officer_id, dec.checker_id}
    names = await identity.user_names(session, ids)
    final_ev = await session.get(Evaluation, dec.evaluation_id) if dec and dec.evaluation_id else None
    at_recommended = None
    if dec and dec.recommended_paise and dec.recommended_paise != app.amount_paise:
        at_recommended = await session.scalar(
            select(Evaluation).where(Evaluation.application_id == app.id,
                                     Evaluation.amount_paise == dec.recommended_paise)
            .order_by(Evaluation.seq.desc()).limit(1)
        )
    return {
        "application": _app_dict(app) | {"submitted_by_name": names.get(app.submitted_by)},
        "evaluation": evaluation_dict(ev),
        "final_evaluation": evaluation_dict(final_ev),
        "recommended_evaluation": evaluation_dict(at_recommended),
        "decision": _decision_dict(dec, names) if dec else None,
        "events": [
            {"id": e.id, "action": e.action, "actor_id": e.actor_id,
             "actor_name": names.get(e.actor_id), "meta": e.meta, "created_at": e.created_at}
            for e in events
        ],
    }


def _decision_dict(dec: Decision, names: dict[uuid.UUID, str]) -> dict[str, Any]:
    return {
        **{c: getattr(dec, c) for c in (
            "id", "recommendation", "recommended_paise", "officer_id", "officer_note",
            "recommended_at", "outcome", "approved_paise", "checker_id", "checker_note",
            "decided_at", "evaluation_id", "ledger_seq",
        )},
        "officer_name": names.get(dec.officer_id),
        "checker_name": names.get(dec.checker_id) if dec.checker_id else None,
        # HOOK(Pulkit): "signed" when ledger_seq is set by ledger.append.
        "signature": "signed" if dec.ledger_seq is not None else "pending",
    }


# ---- writes ------------------------------------------------------------------------------


async def create_application(
    session: AsyncSession, user: User, data: dict[str, Any], on_date: date | None = None,
    at: datetime | None = None,
) -> Application:
    """data: product, amount_paise, tenor_months, purpose, household_income_annual_paise,
    existing_monthly_repayments_paise, and for an officer borrower_name. Rate, fees and the
    pre-payment charge come from the product."""
    product = get_product(data["product"])
    if product is None:
        raise Invalid(f"Unknown product {data['product']!r}.")
    if data["tenor_months"] not in product["tenors"]:
        raise Invalid(f"Tenor must be one of {', '.join(map(str, product['tenors']))} months.")
    if user.role == "borrower":
        borrower_id, borrower_name = user.id, data.get("borrower_name") or user.name
    else:
        borrower_id, borrower_name = data.get("borrower_id"), (data.get("borrower_name") or "").strip()
        if not borrower_name:
            raise Invalid("The borrower's name is needed.")
    when = on_date or day_of(at)
    app = Application(
        org_id=user.org_id,
        ref=data.get("ref") or await next_ref(session, when.year),
        borrower_id=borrower_id,
        borrower_name=borrower_name,
        purpose=(data.get("purpose") or "").strip() or None,
        product=product["code"],
        amount_paise=data["amount_paise"],
        tenor_months=data["tenor_months"],
        rate_bps_month=product["rate_bps_month"],
        fees=product["fees"],
        prepayment_charge_paise=product["prepayment_charge_paise"],
        collateral=product["collateral"],
        household_income_annual_paise=data.get("household_income_annual_paise"),
        existing_monthly_repayments_paise=data.get("existing_monthly_repayments_paise"),
        status="evaluated",
        submitted_by=user.id,
        **_stamp("created_at", at),
        **_stamp("updated_at", at),
    )
    session.add(app)
    await session.flush()
    await _log(session, user.id, app, "submitted", {
        "by_role": user.role, "amount_paise": app.amount_paise, "tenor_months": app.tenor_months,
    }, at)
    await _evaluate(session, app, user, on_date=when, at=at)
    return app


EDITABLE = ("household_income_annual_paise", "existing_monthly_repayments_paise", "purpose")


async def update_facts(
    session: AsyncSession, user: User, app_id: uuid.UUID, data: dict[str, Any],
    on_date: date | None = None,
) -> Application:
    """Officer fills in or corrects facts before recommending; the engine runs again."""
    app = await get_application(session, user, app_id)
    if app.status != "evaluated":
        raise LoanError("Facts can change only before the officer recommends.")
    changed = {k: data[k] for k in EDITABLE if k in data}
    for k, v in changed.items():
        setattr(app, k, v)
    await session.flush()
    await _log(session, user.id, app, "facts_updated", {"fields": sorted(changed)})
    await _evaluate(session, app, user, on_date=on_date)
    return app


async def reevaluate(session: AsyncSession, user: User, app_id: uuid.UUID,
                     on_date: date | None = None) -> Application:
    app = await get_application(session, user, app_id)
    if app.status in FINAL:
        raise LoanError("The decision is final; the engine is not run again.")
    await _evaluate(session, app, user, on_date=on_date)
    return app


def _note(note: str | None) -> str | None:
    return note.strip() if note and note.strip() else None


async def _must_pass(session: AsyncSession, app: Application, user: User, amount: int,
                     on_date: date | None, at: datetime | None = None) -> Evaluation:
    ev = await _evaluate(session, app, user, amount, on_date, at)
    if ev.outcome != "pass":
        bad = [f"{r['code']} {r['status']}" for r in ev.results if r["status"] in ("fail", "refer")]
        raise LoanError(f"Not every rule passes at this amount ({', '.join(bad)}).")
    return ev


async def recommend(
    session: AsyncSession, user: User, app_id: uuid.UUID, recommendation: str,
    amount_paise: int | None, note: str | None, on_date: date | None = None,
    at: datetime | None = None,
) -> Application:
    app = await get_application(session, user, app_id)
    if app.status != "evaluated":
        raise LoanError(f"Cannot recommend an application that is {app.status}.")
    note = _note(note)
    if recommendation == "approve":
        amount = app.amount_paise
        await _must_pass(session, app, user, amount, on_date, at)
    elif recommendation == "approve_modified":
        if not amount_paise or amount_paise >= app.amount_paise:
            raise Invalid("A modified amount must be below the amount asked for.")
        amount = amount_paise
        await _must_pass(session, app, user, amount, on_date, at)
    elif recommendation == "reject":
        if not note:
            raise Invalid("A note is needed to recommend a rejection.")
        amount = None
    else:
        raise Invalid("recommendation must be approve, approve_modified or reject")
    session.add(Decision(
        application_id=app.id, recommendation=recommendation, recommended_paise=amount,
        officer_id=user.id, officer_note=note, **_stamp("recommended_at", at),
    ))
    app.status = "recommended"
    if at:
        app.updated_at = at
    await session.flush()
    await _log(session, user.id, app, "recommended", {
        "recommendation": recommendation, "amount_paise": amount, "note": note,
    }, at)
    return app


async def _sign_decision(session: AsyncSession, decision: Decision, payload: dict) -> int | None:
    """HOOK(Pulkit): sign the final decision on the ledger.

    When the trust module lands, replace the body with
        entry = await ledger.append(session, "decision", payload)
        return entry.seq
    inside this same transaction. Until then nothing is signed: ledger_seq stays null and every
    page shows "Signature pending". No placeholder signature or hash is stored.
    """
    return None


async def decide(
    session: AsyncSession, user: User, app_id: uuid.UUID, outcome: str,
    amount_paise: int | None, note: str | None, on_date: date | None = None,
    at: datetime | None = None,
) -> Application:
    """outcome: approve (at the recommended amount), modify (at amount_paise) or reject."""
    app = await get_application(session, user, app_id)
    if app.status != "recommended":
        raise LoanError(f"Cannot decide an application that is {app.status}.")
    dec = await get_decision(session, app.id)
    assert dec is not None
    if dec.officer_id == user.id:
        raise SameUser("The officer who recommended cannot also decide.")
    note = _note(note)
    final_ev = None
    if outcome == "approve":
        if dec.recommendation == "reject":
            raise LoanError("The officer recommended a rejection: modify with an amount or reject.")
        amount = dec.recommended_paise or app.amount_paise
    elif outcome == "modify":
        if not note:
            raise Invalid("A note is needed to modify the amount.")
        if not amount_paise or amount_paise > app.amount_paise:
            raise Invalid("A modified amount must be positive and not above the amount asked for.")
        amount = amount_paise
    elif outcome == "reject":
        if not note:
            raise Invalid("A note is needed to reject.")
        amount = None
    else:
        raise Invalid("outcome must be approve, modify or reject")
    if amount is not None:
        final_ev = await _must_pass(session, app, user, amount, on_date, at)
    app.status = (
        "rejected" if amount is None
        else "approved" if amount == app.amount_paise else "approved_modified"
    )
    dec.outcome = app.status
    dec.approved_paise = amount
    dec.checker_id = user.id
    dec.checker_note = note
    dec.decided_at = at or datetime.now(UTC)
    if at:
        app.updated_at = at
    dec.evaluation_id = final_ev.id if final_ev else None
    await session.flush()
    dec.ledger_seq = await _sign_decision(session, dec, {
        "application": app.ref, "outcome": app.status, "approved_paise": amount,
        "evaluation_id": str(final_ev.id) if final_ev else None,
        "rules": final_ev.rules_used if final_ev else None,
        "officer_id": str(dec.officer_id), "checker_id": str(user.id),
    })
    await session.flush()
    await _log(session, user.id, app, "decided", {
        "outcome": app.status, "amount_paise": amount, "note": note,
        "signature": "pending" if dec.ledger_seq is None else "signed",
    }, at)
    return app


async def preview(session: AsyncSession, user: User, data: dict[str, Any],
                  on_date: date | None = None) -> dict[str, Any]:
    """Run the engine on a draft application without saving anything ("live checks")."""
    product = get_product(data["product"])
    if product is None:
        raise Invalid(f"Unknown product {data['product']!r}.")
    facts = {
        "product_category": product["category"],
        "amount_paise": data.get("amount_paise"),
        "tenor_months": data.get("tenor_months"),
        "rate_bps_month": product["rate_bps_month"],
        "fees": product["fees"],
        "prepayment_charge_paise": product["prepayment_charge_paise"],
        "collateral": product["collateral"],
        "household_income_annual_paise": data.get("household_income_annual_paise"),
        "existing_monthly_repayments_paise": data.get("existing_monthly_repayments_paise"),
        "offer_step_paise": product["offer_step_paise"],
    }
    result = await rules.evaluate_application(session, facts, on_date or today())
    return result.as_dict()


async def replay(session: AsyncSession, user: User, app_id: uuid.UUID) -> dict[str, Any]:
    """Re-run the stored facts of the decision's evaluation on its own date and compare.

    A real check that needs no signature: the same inputs and the rules in force that day must
    give the same result. Rules approved or retired since then change "rules in force", so a
    difference names the rules that differ."""
    app = await get_application(session, user, app_id)
    dec = await get_decision(session, app.id)
    ev = None
    if dec and dec.evaluation_id:
        ev = await session.get(Evaluation, dec.evaluation_id)
    ev = ev or await latest_evaluation(session, app)
    if ev is None:
        raise NotFound("No evaluation to replay")
    again = await rules.evaluate_application(session, ev.facts, ev.on_date)
    stored = {r["code"]: r["status"] for r in ev.results}
    now = {r.code: r.status for r in again.results}
    stored_rules = {f"{r['code']} v{r['version']}" for r in ev.rules_used}
    now_rules = {f"{r['code']} v{r['version']}" for r in again.rules_used}
    return {
        "application": _app_dict(app),
        "evaluation_id": ev.id,
        "on_date": ev.on_date,
        "amount_paise": ev.amount_paise,
        "stored_outcome": ev.outcome,
        "replayed_outcome": again.outcome,
        "same_outcome": ev.outcome == again.outcome,
        "same_results": stored == now,
        "different_results": sorted(c for c in stored.keys() | now.keys()
                                    if stored.get(c) != now.get(c)),
        "same_rules": stored_rules == now_rules,
        "rules_used": sorted(stored_rules),
        "rules_now": sorted(now_rules),
        "signature": "signed" if dec and dec.ledger_seq is not None else "pending",
        "decision": _decision_dict(dec, await identity.user_names(
            session, {dec.officer_id, dec.checker_id})) if dec else None,
    }


# ---- staff views -------------------------------------------------------------------------


async def overview(session: AsyncSession, user: User) -> dict[str, Any]:
    rows = await session.execute(
        select(Application.status, func.count()).where(Application.org_id == user.org_id)
        .group_by(Application.status)
    )
    counts = {s: 0 for s in ("evaluated", "recommended", "approved", "approved_modified",
                              "rejected")}
    counts.update(dict(rows.all()))
    waiting = await list_applications(session, user, ("evaluated",))
    return {"counts": counts, "waiting": waiting}


async def decisions_log(session: AsyncSession, user: User) -> list[dict[str, Any]]:
    """Decided applications only (a checker has decided), newest first, for the ledger and
    Verify. Each row says how many rules were checked, their versions, and which rule decided
    the outcome (the rules that failed or referred at the amount asked for)."""
    rows = (await session.execute(
        select(Decision, Application).join(Application, Application.id == Decision.application_id)
        .where(Application.org_id == user.org_id, Decision.outcome.is_not(None))
        .order_by(Decision.decided_at.desc(), Application.ref)
    )).all()
    names = await identity.user_names(
        session, {d.officer_id for d, _ in rows} | {d.checker_id for d, _ in rows if d.checker_id}
    )
    out = []
    for dec, app in rows:
        final = await session.get(Evaluation, dec.evaluation_id) if dec.evaluation_id else None
        asked = await latest_evaluation(session, app)
        basis = final or asked
        versions = {r["code"]: r["version"] for r in (basis.rules_used if basis else [])}
        checked = [r for r in (basis.results if basis else [])
                   if r["status"] in ("pass", "fail", "refer")]
        deciding = [f"{r['code']} v{r['version']}" for r in (asked.results if asked else [])
                    if r["status"] in ("fail", "refer")]
        out.append({
            "application": _app_dict(app),
            "decision": _decision_dict(dec, names),
            "final_evaluation": evaluation_dict(final),
            "rules": {
                "in_force": len(versions),
                "checked": len(checked),
                "versions": [f"{c} v{v}" for c, v in sorted(versions.items())],
                "deciding": deciding,
            },
        })
    return out


async def recent_events(session: AsyncSession, user: User, limit: int = 100) -> list[dict]:
    rows = (await session.execute(
        select(Event, Application.ref).join(Application, Application.id == Event.application_id)
        .where(Application.org_id == user.org_id)
        .order_by(Event.seq.desc()).limit(limit)
    )).all()
    names = await identity.user_names(session, {e.actor_id for e, _ in rows})
    return [
        {"id": e.id, "ref": ref, "application_id": e.application_id, "action": e.action,
         "actor_name": names.get(e.actor_id), "meta": e.meta, "created_at": e.created_at}
        for e, ref in rows
    ]


async def counts(session: AsyncSession, user: User) -> dict[str, int]:
    apps = await session.scalar(
        select(func.count()).select_from(Application).where(Application.org_id == user.org_id)
    )
    evs = await session.scalar(
        select(func.count()).select_from(Evaluation).join(Application)
        .where(Application.org_id == user.org_id)
    )
    decided = await session.scalar(
        select(func.count()).select_from(Decision).join(Application)
        .where(Application.org_id == user.org_id, Decision.outcome.is_not(None))
    )
    events = await session.scalar(
        select(func.count()).select_from(Event).join(Application)
        .where(Application.org_id == user.org_id)
    )
    signed = await session.scalar(
        select(func.count()).select_from(Decision).join(Application)
        .where(Application.org_id == user.org_id, Decision.ledger_seq.is_not(None))
    )
    return {"applications": apps or 0, "evaluations": evs or 0, "decisions": decided or 0,
            "events": events or 0, "signed": signed or 0}
