"""P5 rule engine: evaluate a loan application against the approved rules in force.

    evaluate_application(session, facts, on_date) -> Evaluation

Which rules: approved rules with effective_from <= on_date < effective_to (no effective_to:
still in force). A rule with no effective_from is not in force: the date was not verified.
Of those, only stage "origination" rules are checked; servicing and recovery rules are listed
as "not checked at this stage". Rules for "microfinance" apply only when the microfinance test
(a rule with decides_scope, e.g. MF-01) says the loan is one; otherwise they are "not applicable".

Every number comes from the rule's params, which were taken from the quoted paragraph. A fact
that is missing gives "refer", never a guessed pass. Arithmetic is exact (app.rules.finance).
No eval or exec: each template has a plain Python evaluator below, and each reads the
fact(s) its params name from the fact catalogue (app.rules.facts). No rule code appears here.

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

from app.rules import facts as F
from app.rules import finance as fin
from app.rules.models import Rule
from app.rules.workflow import rule_version, source_docs_by_id

# Catalogue facts the KFS builder answers: the validity it is issued with (set by the min_days
# rule on this fact) and the APR computation sheet.
KFS_VALIDITY = "kfs_validity_working_days"
APR_SHEET = "apr_computation_sheet"

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


_Missing = F.Missing


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
    # What the borrower pays: the rounded EMI, every month.
    total_payable = emi * months
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
        "total_interest_paise": total_payable - amount,
        "total_payable_paise": total_payable,
        "monthly_irr_percent": str((fin.monthly_irr(net, exact, months) * 100).quantize(
            fin.Decimal("0.001"), rounding=fin.ROUND_HALF_UP)),
        "apr_percent": str(fin.apr_percent(net, exact, months)),
        "apr_method": "12 x monthly IRR of the net disbursal against the unrounded EMI "
                      "(RBC Annex I: IRR approach, reducing balance).",
        "rounding": "EMI rounded to the nearest rupee, half up; totals use the rounded EMI. "
                    "Fees rounded to the rupee. APR uses the unrounded EMI.",
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


# ---- evaluators, one per template ------------------------------------------------------
#
# Each reads the fact(s) its params name from the fact catalogue (app.rules.facts). Nothing
# here knows a rule code: a new rule from a new PDF runs as soon as it is approved.

Outcome = tuple[str, str, dict[str, Any]]
Ctx = dict[str, Any]


def _rupees(v: Any) -> str:
    return fin.rupees(v)


def _max_amount(rule: Rule, facts: dict, ctx: Ctx) -> Outcome:
    p = rule.params
    fact = F.get(p.get("fact"))
    guard = F.get(p["must_be_false"]) if p.get("must_be_false") else None
    keys = ([guard.key] if guard else []) + [fact.key]
    got = F.values(keys, facts, ctx)
    flag, v = (got[0], got[1]) if guard else (None, got[0])
    limit = p["max_paise"]
    scope = rule.applies_to if p.get("decides_scope") and rule.applies_to != "all" else None
    values: dict[str, Any] = {fact.value_key: F.show(fact, v), "limit": _rupees(limit)}
    if guard:
        values[guard.value_key] = not flag
    if guard and flag:
        why = f"not a {guard.false_label.casefold()} {scope} loan" if scope else (
            f"the rule needs it {guard.false_label.casefold()}")
        return FAIL, f"{guard.true_label}: {why}.", values
    shown = f"{F.show(fact, v)}{fact.per}"
    if v > limit:
        tail = f": not a {scope} loan." if scope else "."
        return FAIL, f"{fact.short} {shown} is above {_rupees(limit)}{tail}", values
    lead = f"{guard.false_label}, {fact.short.casefold()}" if guard else fact.short
    return PASS, f"{lead} {shown}, within {_rupees(limit)}.", values


def _ratio_text(num: Fraction | int, den: Fraction, limit: Fraction) -> str:
    """One decimal, or two when one would hide which side of the limit it is (49.95 not 50.0)."""
    one = fin.percent(num, den, 1)
    within = Fraction(num) / den <= limit
    shown = Fraction(one) / 100
    if within != (shown <= limit) or shown == limit:
        return fin.percent(num, den, 2)
    return one


def _max_ratio(rule: Rule, facts: dict, ctx: Ctx) -> Outcome:
    p = rule.params
    num_f, den_f = F.get(p.get("numerator_fact")), F.get(p.get("denominator_fact"))
    den, num = F.values([den_f.key, num_f.key], facts, ctx)
    parts = [F.get(k) for k in num_f.parts]
    part_values = [F.value(k.key, facts, ctx) for k in parts]
    ratio = Fraction(str(p["max_percent"])) / 100
    offerable = bool(p.get("offer_on_fail") and num_f.emi_part)
    e_max = None
    values: dict[str, Any] = {den_f.value_key: F.show(den_f, den)}
    values |= {f.value_key: F.show(f, x) for f, x in zip(parts, part_values, strict=True)}
    values |= {
        num_f.value_key: F.show(num_f, num),
        "ratio_percent": _ratio_text(num, den, ratio),
        "limit_percent": str(p["max_percent"]),
    }
    if offerable:
        emi = F.value(num_f.emi_part, facts, ctx)
        e_max = ratio * den - (num - emi)
        values["e_max"] = _rupees(e_max) if e_max > 0 else "₹0"
    names = " + ".join(f.formula_name for f in parts) if parts else num_f.short.casefold()
    values["formula"] = f"({names}) / {den_f.formula_name or den_f.short.casefold()}"
    head = f"{_rupees(num)}{num_f.per} is"
    if num <= ratio * den:
        return PASS, (f"{head} {fin.percent(num, den, 2)}% of {_rupees(den)}, within "
                      f"{p['max_percent']}%."), values
    if offerable:
        _offer(facts, ctx, values, e_max, num - F.value(num_f.emi_part, facts, ctx), den)
    return FAIL, (f"{head} {fin.percent(num, den)}% of {_rupees(den)}, above "
                  f"{p['max_percent']}%."), values


def _offer(facts: dict, ctx: Ctx, values: dict, e_max: Fraction, rest: Any, den: Any) -> None:
    """The largest loan whose EMI fits within e_max, rounded down to the product's step."""
    rate, months = F.values(["rate_bps_month", "tenor_months"], facts, ctx)
    step = facts.get("offer_step_paise") or fin.PAISE_PER_RUPEE
    l_exact = fin.principal_for_emi(e_max, rate, months) if e_max > 0 else Fraction(0)
    offer = fin.largest_loan(e_max, rate, months, step)
    values["l_max"] = _rupees(l_exact)
    if offer > 0:
        offer_emi = fin.emi(offer, rate, months)
        ctx["offer"] = {
            "amount_paise": offer,
            "emi_paise": offer_emi,
            "e_max_paise": fin.round_down(e_max, 1),
            "l_max_exact": _rupees(l_exact),
            "ratio_percent": fin.percent(rest + offer_emi, den, 2),
            "step_paise": step,
            "rounding": f"Largest loan rounded down to {_rupees(step)}.",
        }


def _prohibited_charge(rule: Rule, facts: dict, ctx: Ctx) -> Outcome:
    p = rule.params
    fact = F.get(p.get("fact"))
    (v,) = F.values([fact.key], facts, ctx)
    values = {fact.value_key: F.show(fact, v)}
    if v:
        what = f" of {F.show(fact, v)}" if fact.unit.startswith("paise") else ""
        return FAIL, f"The product sets a {p['charge']}{what}.", values
    return PASS, f"No {p['charge']} in the fee schedule.", values


def _tier(params: dict[str, Any], facts: dict, ctx: Ctx) -> int | None:
    """The minimum days of the tier that matches the loan's tenor, in days from on_date."""
    (months,) = F.values(["tenor_months"], facts, ctx)
    on = ctx["on_date"]
    return _validity_days(params, (fin.add_months(on, months) - on).days)


def _min_days(rule: Rule, facts: dict, ctx: Ctx) -> Outcome:
    p = rule.params
    fact = F.get(p.get("fact"))
    (v,) = F.values([fact.key], facts, ctx)
    need = _tier(p, facts, ctx)
    if need is None or v is None:
        return REFER, "No validity tier in this rule matches the loan's tenor.", {}
    unit = "working days" if p.get("working_days") else "days"
    if fact.key == KFS_VALIDITY:
        kfs = ctx["kfs"]
        values = {"issued_on": kfs["issued_on"], "valid_until": kfs["valid_until"],
                  "working_days": v, "note": HOLIDAY_NOTE}
        lead = f"KFS valid until {kfs['valid_until']}, {v} working days after issue."
    else:
        values = {fact.value_key: v, "min_days": need}
        lead = f"{fact.short} {v} {unit}."
    if v < need:
        return FAIL, f"{fact.short} {v} {unit}, below {need}.", values
    return PASS, lead, values


def _required_disclosure(rule: Rule, facts: dict, ctx: Ctx) -> Outcome:
    p = rule.params
    fact = F.get(p.get("fact"))
    (given,) = F.values([fact.key], facts, ctx)
    if not given:
        return FAIL, f"Not produced: {p['item']}.", {}
    if fact.key == APR_SHEET:
        kfs = ctx["kfs"]
        values = {"apr_percent": kfs["apr_percent"],
                  "fees_total": _rupees(kfs["fees_total_paise"]),
                  "net_disbursal": _rupees(kfs["net_disbursal_paise"])}
        return PASS, f"APR computation sheet generated: APR {kfs['apr_percent']}%.", values
    return PASS, f"{fact.short} produced.", {fact.value_key: True}


def _time_window(rule: Rule, facts: dict, ctx: Ctx) -> Outcome:
    return REFER, "Checked at the time of contact, not on an application: check by hand.", {}


EVALUATORS: dict[str, Callable[[Rule, dict, Ctx], Outcome]] = {
    "max_amount": _max_amount,
    "max_ratio": _max_ratio,
    "min_days": _min_days,
    "prohibited_charge": _prohibited_charge,
    "required_disclosure": _required_disclosure,
    "time_window": _time_window,
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


def decides_scope(rule: Rule) -> bool:
    """A rule that decides whether the loan is one its applies_to covers (e.g. microfinance)."""
    return bool(rule.params.get("decides_scope")) and rule.applies_to != "all"


def _order(rule: Rule) -> tuple[int, str]:
    # Scope-deciding rules run first, so the rules they gate know the answer.
    return (0 if decides_scope(rule) else 1, rule.code)


def _validity_rule(rules: list[Rule]) -> Rule | None:
    """The origination min_days rule on the KFS validity fact: the KFS is issued with it."""
    return next((r for r in rules if r.stage == "origination" and r.template == "min_days"
                 and r.params.get("fact") == KFS_VALIDITY), None)


async def evaluate_application(
    session: AsyncSession, facts: dict[str, Any], on_date: date, *, with_offer: bool = True
) -> Evaluation:
    rules = sorted(await rules_in_force(session, on_date), key=_order)
    docs = await source_docs_by_id(session, {r.source_doc_id for r in rules})
    versions = {r.id: await rule_version(session, r) for r in rules}

    def anchor(r: Rule) -> str:
        doc = docs.get(r.source_doc_id)
        return f"{doc.short_code if doc and doc.short_code else 'Source'} para {r.source_para}"

    ctx: Ctx = {"on_date": on_date}
    validity = _validity_rule(rules)
    try:
        ctx["kfs"] = build_kfs(facts, on_date, validity, anchor(validity) if validity else None)
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
        evaluator = EVALUATORS.get(r.template)
        if evaluator is None:
            results.append(RuleResult(**base, status=REFER,
                                      message="No evaluator for this template: check by hand."))
            continue
        try:
            status, message, values = evaluator(r, facts, ctx)
            results.append(RuleResult(**base, status=status, message=message, values=values))
        except F.NotInCatalogue as n:
            status = REFER
            message = (f"Fact not in catalogue: {n.key}." if n.key
                       else "No fact chosen for this rule.")
            results.append(RuleResult(**base, status=REFER, message=message))
        except _Missing as m:
            status = REFER
            results.append(RuleResult(
                **base, status=REFER, missing=m.names,
                message=f"Missing: {', '.join(n.replace('_', ' ') for n in m.names)}.",
            ))
        if decides_scope(r) and r.applies_to == category:
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
