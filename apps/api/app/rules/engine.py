"""P5 rule engine: evaluate a loan application against the approved rules in force.

    evaluate_application(session, facts, on_date) -> Evaluation

Which rules: approved rules with effective_from <= on_date < effective_to (no effective_to:
still in force). A rule with no effective_from is not in force: the date was not verified.
Of those, only stage "origination" rules are checked; servicing and recovery rules are listed
as "not checked at this stage". Rules for "microfinance" apply only when the microfinance test
(MF-01) says the loan is one; otherwise they are "not applicable".

Every number comes from the rule's params, which were taken from the quoted paragraph. A fact
that is missing gives "refer", never a guessed pass. Arithmetic is exact (app.rules.finance).
No eval or exec: each rule code has a plain Python evaluator below.

Facts (all money in paise, rate in basis points per month):
    product_category      "microfinance" or "general"
    amount_paise, tenor_months, rate_bps_month
    fees                  [{"name", "bps" | "paise", "payable_to": "lender" | "third_party",
                            "assumed": bool}]
    prepayment_charge_paise
    collateral            bool (True if the loan is secured)
    household_income_annual_paise
    existing_monthly_repayments_paise
    offer_step_paise      the lender's step for a modified amount (product setting)
"""

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import date
from fractions import Fraction
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rules import finance as fin
from app.rules.models import Rule
from app.rules.workflow import rule_version, source_docs_by_id

# The rule that decides whether a loan is a microfinance loan, and so whether the other
# microfinance rules apply. Its numbers still come from its params.
MICROFINANCE_TEST = "MF-01"

PASS, FAIL, REFER = "pass", "fail", "refer"
NOT_CHECKED, NOT_APPLICABLE = "not_checked", "not_applicable"
HOLIDAY_NOTE = "Public holidays are not modelled: only Saturdays and Sundays are non-working."


@dataclass
class RuleResult:
    rule_id: str
    code: str
    version: int
    title: str
    stage: str
    applies_to: str
    status: str
    message: str
    anchor: str
    para_text: str
    values: dict[str, Any] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)


@dataclass
class Evaluation:
    on_date: str
    outcome: str
    microfinance: bool | None
    results: list[RuleResult]
    rules_used: list[dict[str, Any]]
    offer: dict[str, Any] | None = None
    kfs: dict[str, Any] | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def result(self, code: str) -> RuleResult | None:
        return next((r for r in self.results if r.code == code), None)


class _Missing(Exception):
    def __init__(self, names: list[str]):
        self.names = names


def _need(facts: dict[str, Any], *names: str) -> list[Any]:
    missing = [n for n in names if facts.get(n) is None]
    if missing:
        raise _Missing(missing)
    return [facts[n] for n in names]


# ---- KFS ---------------------------------------------------------------------------------


def _validity_days(params: dict[str, Any], tenor_days: int) -> int | None:
    for tier in params.get("tiers") or []:
        lo, below = tier.get("tenor_days_min"), tier.get("tenor_days_below")
        if (lo is None or tenor_days >= lo) and (below is None or tenor_days < below):
            return tier.get("min_days")
    return None


def build_kfs(facts: dict[str, Any], on_date: date, validity_rule: Rule | None,
              anchor: str | None = None) -> dict[str, Any]:
    """Key Facts Statement figures and the APR computation sheet (RBC Annex I)."""
    amount, months, rate = _need(facts, "amount_paise", "tenor_months", "rate_bps_month")
    exact = fin.emi_exact(amount, rate, months)
    emi = fin.to_rupee(exact)
    fees = [
        {"name": f["name"], "paise": fin.fee_paise(amount, f),
         "payable_to": f.get("payable_to", "lender"), "assumed": bool(f.get("assumed")),
         "basis": f"{Fraction(int(f['bps']), 100)}% of the loan" if "bps" in f else "fixed"}
        for f in facts.get("fees") or []
    ]
    fees_total = sum(f["paise"] for f in fees)
    net = amount - fees_total
    total_interest = fin.to_rupee(exact * months - amount)
    first_due = fin.add_months(on_date, 1)
    tenor_days = (fin.add_months(on_date, months) - on_date).days
    kfs: dict[str, Any] = {
        "amount_paise": amount,
        "tenor_months": months,
        "rate_bps_month": rate,
        "rate_month_percent": fin.percent(rate, fin.BPS, 2).rstrip("0").rstrip("."),
        "rate_year_percent": fin.percent(rate * 12, fin.BPS, 2),
        "emi_paise": emi,
        "emi_exact": fin.rupees(exact),
        "instalments": months,
        "first_due_on": first_due.isoformat(),
        "fees": fees,
        "fees_total_paise": fees_total,
        "net_disbursal_paise": net,
        "total_interest_paise": total_interest,
        "total_payable_paise": amount + total_interest,
        "apr_percent": str(fin.apr_percent(net, exact, months)),
        "apr_method": "12 x monthly IRR of the net disbursal against the unrounded EMI "
                      "(RBC Annex I: IRR approach, reducing balance).",
        "rounding": "EMI rounded to the nearest rupee, half up. Fees rounded to the rupee.",
        "issued_on": on_date.isoformat(),
        "valid_until": None,
        "validity_working_days": None,
        "validity_anchor": anchor,
        "notes": [HOLIDAY_NOTE],
    }
    if validity_rule is not None:
        days = _validity_days(validity_rule.params, tenor_days)
        if days is not None:
            kfs["validity_working_days"] = days
            kfs["valid_until"] = fin.add_working_days(on_date, days).isoformat()
    if any(f["assumed"] for f in fees):
        kfs["notes"].append("Fees marked assumed are product settings, not taken from a rule.")
    return kfs


# ---- evaluators ----------------------------------------------------------------------------

Outcome = tuple[str, str, dict[str, Any]]
Ctx = dict[str, Any]


def _mf01(rule: Rule, facts: dict, ctx: Ctx) -> Outcome:
    collateral, income = _need(facts, "collateral", "household_income_annual_paise")
    limit = rule.params["max_paise"]
    values = {"household_income_annual": fin.rupees(income), "limit": fin.rupees(limit),
              "collateral_free": not collateral}
    if collateral:
        return FAIL, "Secured loan: not a collateral-free microfinance loan.", values
    if income > limit:
        return FAIL, (f"Household income {fin.rupees(income)} a year is above "
                      f"{fin.rupees(limit)}: not a microfinance loan."), values
    return PASS, (f"Collateral-free, household income {fin.rupees(income)} a year, within "
                  f"{fin.rupees(limit)}."), values


def _mf02(rule: Rule, facts: dict, ctx: Ctx) -> Outcome:
    income, existing, amount, months, rate = _need(
        facts, "household_income_annual_paise", "existing_monthly_repayments_paise",
        "amount_paise", "tenor_months", "rate_bps_month",
    )
    ratio = Fraction(str(rule.params["max_percent"])) / 100
    monthly = Fraction(income, 12)
    emi = fin.emi(amount, rate, months)
    total = existing + emi
    e_max = ratio * monthly - existing
    values = {
        "monthly_income": fin.rupees(monthly),
        "existing_repayments": fin.rupees(existing),
        "new_emi": fin.rupees(emi),
        "repayments": fin.rupees(total),
        "ratio_percent": fin.percent(total, monthly),
        "limit_percent": str(rule.params["max_percent"]),
        "e_max": fin.rupees(e_max) if e_max > 0 else "₹0",
        "formula": "(existing monthly repayments + new EMI) / monthly household income",
    }
    if total <= ratio * monthly:
        return PASS, (f"{fin.rupees(total)} a month is {fin.percent(total, monthly, 2)}% of "
                      f"{fin.rupees(monthly)}, within {rule.params['max_percent']}%."), values
    step = facts.get("offer_step_paise") or fin.PAISE_PER_RUPEE
    l_exact = fin.principal_for_emi(e_max, rate, months) if e_max > 0 else Fraction(0)
    offer = fin.largest_loan(e_max, rate, months, step)
    values["l_max"] = fin.rupees(l_exact)
    if offer > 0:
        offer_emi = fin.emi(offer, rate, months)
        ctx["offer"] = {
            "amount_paise": offer,
            "emi_paise": offer_emi,
            "e_max_paise": fin.round_down(e_max, 1),
            "l_max_exact": fin.rupees(l_exact),
            "ratio_percent": fin.percent(existing + offer_emi, monthly, 2),
            "step_paise": step,
            "rounding": f"Largest loan rounded down to {fin.rupees(step)}.",
        }
    return FAIL, (f"{fin.rupees(total)} a month is {fin.percent(total, monthly)}% of "
                  f"{fin.rupees(monthly)}, above {rule.params['max_percent']}%."), values


def _prohibited_charge_at_origination(rule: Rule, facts: dict, ctx: Ctx) -> Outcome:
    (charge,) = _need(facts, "prepayment_charge_paise")
    values = {"prepayment_charge": fin.rupees(charge)}
    if charge > 0:
        return FAIL, f"The product sets a pre-payment charge of {fin.rupees(charge)}.", values
    return PASS, "No pre-payment charge in the fee schedule.", values


def _kfs_validity(rule: Rule, facts: dict, ctx: Ctx) -> Outcome:
    kfs = ctx.get("kfs")
    if kfs is None:
        raise _Missing(ctx.get("kfs_missing") or ["amount_paise"])
    if kfs["valid_until"] is None:
        return REFER, "No validity tier in this rule matches the loan's tenor.", {}
    values = {"issued_on": kfs["issued_on"], "valid_until": kfs["valid_until"],
              "working_days": kfs["validity_working_days"], "note": HOLIDAY_NOTE}
    return PASS, (f"KFS valid until {kfs['valid_until']}, {kfs['validity_working_days']} "
                  "working days after issue."), values


def _apr_sheet(rule: Rule, facts: dict, ctx: Ctx) -> Outcome:
    kfs = ctx.get("kfs")
    if kfs is None:
        raise _Missing(ctx.get("kfs_missing") or ["amount_paise"])
    values = {"apr_percent": kfs["apr_percent"], "fees_total": fin.rupees(kfs["fees_total_paise"]),
              "net_disbursal": fin.rupees(kfs["net_disbursal_paise"])}
    return PASS, f"APR computation sheet generated: APR {kfs['apr_percent']}%.", values


EVALUATORS: dict[str, Callable[[Rule, dict, Ctx], Outcome]] = {
    "MF-01": _mf01,
    "MF-02": _mf02,
    "MF-04": _prohibited_charge_at_origination,
    "KF-01": _kfs_validity,
    "KF-03": _apr_sheet,
}


# ---- engine ------------------------------------------------------------------------------


async def rules_in_force(session: AsyncSession, on_date: date) -> list[Rule]:
    rows = await session.scalars(
        select(Rule)
        .where(
            Rule.status == "approved",
            Rule.effective_from.is_not(None),
            Rule.effective_from <= on_date,
            or_(Rule.effective_to.is_(None), Rule.effective_to > on_date),
        )
        .order_by(Rule.code)
    )
    return list(rows)


def _order(rule: Rule) -> tuple[int, str]:
    return (0 if rule.code == MICROFINANCE_TEST else 1, rule.code)


async def evaluate_application(
    session: AsyncSession, facts: dict[str, Any], on_date: date, *, with_offer: bool = True
) -> Evaluation:
    rules = sorted(await rules_in_force(session, on_date), key=_order)
    docs = await source_docs_by_id(session, {r.source_doc_id for r in rules})
    versions = {r.id: await rule_version(session, r) for r in rules}

    def anchor(r: Rule) -> str:
        doc = docs.get(r.source_doc_id)
        return f"{doc.short_code if doc and doc.short_code else 'Source'} para {r.source_para}"

    ctx: Ctx = {}
    kf01 = next((r for r in rules if r.code == "KF-01" and r.stage == "origination"), None)
    try:
        ctx["kfs"] = build_kfs(facts, on_date, kf01, anchor(kf01) if kf01 else None)
    except _Missing as m:
        ctx["kfs_missing"] = m.names

    category = facts.get("product_category")
    microfinance: bool | None = None if category == "microfinance" else False
    results: list[RuleResult] = []
    for r in rules:
        base = {
            "rule_id": str(r.id), "code": r.code, "version": versions[r.id], "title": r.title,
            "stage": r.stage, "applies_to": r.applies_to, "anchor": anchor(r), "para_text": r.para_text,
        }
        if r.stage != "origination":
            results.append(RuleResult(**base, status=NOT_CHECKED,
                                      message=f"Not checked at this stage ({r.stage})."))
            continue
        if r.applies_to == "microfinance" and microfinance is False:
            results.append(RuleResult(**base, status=NOT_APPLICABLE,
                                      message="Not a microfinance loan."))
            continue
        evaluator = EVALUATORS.get(r.code)
        if evaluator is None:
            results.append(RuleResult(**base, status=REFER,
                                      message="No evaluator for this rule yet: check by hand."))
            continue
        try:
            status, message, values = evaluator(r, facts, ctx)
            results.append(RuleResult(**base, status=status, message=message, values=values))
        except _Missing as m:
            status = REFER
            results.append(RuleResult(
                **base, status=REFER, missing=m.names,
                message=f"Missing: {', '.join(n.replace('_', ' ') for n in m.names)}.",
            ))
        if r.code == MICROFINANCE_TEST and category == "microfinance":
            microfinance = {PASS: True, FAIL: False}.get(status)

    checked = [r.status for r in results if r.status in (PASS, FAIL, REFER)]
    outcome = FAIL if FAIL in checked else REFER if REFER in checked else PASS
    offer = ctx.get("offer")
    if offer and with_offer:
        # The whole rule set again at the offered amount, so the offer is known to pass.
        again = await evaluate_application(
            session, {**facts, "amount_paise": offer["amount_paise"]}, on_date, with_offer=False
        )
        offer["outcome"] = again.outcome
        offer["kfs"] = again.kfs
    return Evaluation(
        on_date=on_date.isoformat(),
        outcome=outcome,
        microfinance=microfinance,
        results=results,
        rules_used=[{"rule_id": str(r.id), "code": r.code, "version": versions[r.id]}
                    for r in rules],
        offer=offer if with_offer else None,
        kfs=ctx.get("kfs"),
        notes=[HOLIDAY_NOTE] if ctx.get("kfs") else [],
    )
