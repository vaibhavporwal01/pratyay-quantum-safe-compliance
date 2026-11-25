"""The fact catalogue: a fixed, typed list of what the engine knows about an application.

A rule names the fact(s) it checks in its params (`fact`, `numerator_fact`, ...). The engine
reads that fact here, so a rule from a new PDF runs with no code change as long as its fact is
in this list. A fact that is not in the list makes the rule "refer" ("fact not in catalogue").

Stored facts come straight from the application (money in paise). Derived facts are computed
exactly from stored ones (app.rules.finance). Document facts come from the Key Facts
Statement the engine builds. A missing input raises Missing with the stored fact names, so the
rule refers and names what to collect; it never guesses.

No eval or exec: each derived fact is a plain Python function in DERIVE.
"""

from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Literal

from app.rules import finance as fin

Unit = Literal[
    "paise",  # an amount of money
    "paise_month",  # money per month
    "paise_year",  # money per year
    "months",
    "bps_month",  # basis points per month
    "bool",
    "working_days",
    "document",  # a disclosure the engine produces (KFS parts)
]


@dataclass(frozen=True)
class Fact:
    key: str
    label: str  # for the rule builder dropdown
    unit: Unit
    # How the fact reads inside a message ("household income") and its key in result values.
    short: str
    value_key: str
    # Words in a paragraph that point to this fact; the extractor pre-selects it on a match.
    words: tuple[str, ...] = ()
    # For a sum: the facts it adds up, in order (shown in the formula and in the values).
    parts: tuple[str, ...] = ()
    # Name in a formula line, e.g. "new EMI".
    formula_name: str = ""
    # Bool facts: how true and false read ("Secured loan" / "Collateral-free").
    true_label: str = ""
    false_label: str = ""
    # This fact moves with the loan amount through the EMI, so a ratio on it can offer the
    # largest amount that fits (the part that is the new EMI).
    emi_part: str | None = None
    stored: bool = True
    note: str = ""

    @property
    def per(self) -> str:
        return {"paise_month": " a month", "paise_year": " a year"}.get(self.unit, "")

    def as_dict(self) -> dict[str, Any]:
        return {"key": self.key, "label": self.label, "unit": self.unit,
                "stored": self.stored, "note": self.note}


class Missing(Exception):
    def __init__(self, names: list[str]):
        self.names = names


class NotInCatalogue(Exception):
    def __init__(self, key: str):
        self.key = key


CATALOGUE: tuple[Fact, ...] = (
    Fact("household_income_annual_paise", "Annual household income", "paise_year",
         "Household income", "household_income_annual",
         words=("annual household income", "household income")),
    Fact("household_income_monthly_paise", "Monthly household income", "paise_month",
         "Monthly household income", "monthly_income", stored=False,
         words=("monthly household income",), formula_name="monthly household income",
         note="Annual household income divided by 12."),
    Fact("existing_monthly_repayments_paise", "Existing monthly repayments", "paise_month",
         "Existing repayments", "existing_repayments", formula_name="existing monthly repayments",
         words=("existing loan", "outstanding loans")),
    Fact("new_emi_paise", "New loan EMI", "paise_month", "New EMI", "new_emi", stored=False,
         formula_name="new EMI", note="EMI on the loan amount, tenor and rate, to the rupee."),
    Fact("monthly_repayments_paise", "Monthly repayments, all loans (existing + new EMI)",
         "paise_month", "Repayments", "repayments", stored=False,
         parts=("existing_monthly_repayments_paise", "new_emi_paise"),
         emi_part="new_emi_paise",
         words=("repayment of monthly loan obligations", "loan repayment obligations",
                "monthly loan obligations"),
         note="Existing monthly repayments plus the new loan's EMI."),
    Fact("amount_paise", "Loan amount", "paise", "Loan amount", "loan_amount",
         words=("loan amount", "amount of loan", "amount of the loan", "loans up to",
                "loan of", "sanctioned amount")),
    Fact("tenor_months", "Tenor (months)", "months", "Tenor", "tenor_months",
         words=("tenor", "tenure")),
    Fact("rate_bps_month", "Interest rate (basis points a month)", "bps_month",
         "Interest rate", "rate_bps_month", words=("rate of interest", "interest rate")),
    Fact("processing_fee_paise", "Processing fee", "paise", "Processing fee", "processing_fee",
         stored=False, words=("processing fee", "processing charge"),
         note="Sum of the product's processing fees on the loan amount."),
    Fact("fees_total_paise", "All fees and charges at disbursal", "paise", "Fees",
         "fees_total", stored=False, words=("fees and charges",)),
    Fact("prepayment_charge_paise", "Pre-payment charge", "paise", "Pre-payment charge",
         "prepayment_charge", words=("pre-payment", "prepayment", "foreclosure")),
    Fact("collateral", "Loan is secured (collateral)", "bool", "Collateral", "collateral_free",
         true_label="Secured loan", false_label="Collateral-free",
         words=("collateral",)),
    Fact("kfs_validity_working_days", "KFS validity (working days)", "working_days",
         "KFS validity", "working_days", stored=False,
         words=("validity period", "kfs"),
         note="The KFS is issued with the validity the rule requires for the loan's tenor."),
    Fact("apr_computation_sheet", "KFS: APR computation sheet", "document",
         "APR computation sheet", "apr_computation_sheet", stored=False,
         words=("annual percentage rate", "apr")),
)

BY_KEY: dict[str, Fact] = {f.key: f for f in CATALOGUE}


def get(key: str | None) -> Fact:
    if not key or key not in BY_KEY:
        raise NotInCatalogue(key or "")
    return BY_KEY[key]


def _need(facts: dict[str, Any], *names: str) -> list[Any]:
    missing = [n for n in names if facts.get(n) is None]
    if missing:
        raise Missing(missing)
    return [facts[n] for n in names]


def _kfs(ctx: dict[str, Any]) -> dict[str, Any]:
    kfs = ctx.get("kfs")
    if kfs is None:
        raise Missing(ctx.get("kfs_missing") or ["amount_paise"])
    return kfs


def _fees(facts: dict[str, Any], only: str | None = None) -> int:
    (amount,) = _need(facts, "amount_paise")
    return sum(fin.fee_paise(amount, f) for f in facts.get("fees") or []
               if only is None or only in f["name"].casefold())


DERIVE: dict[str, Callable[[dict[str, Any], dict[str, Any]], Any]] = {
    "household_income_monthly_paise": lambda f, c: Fraction(
        _need(f, "household_income_annual_paise")[0], 12),
    "new_emi_paise": lambda f, c: fin.emi(*_need(f, "amount_paise", "rate_bps_month",
                                                  "tenor_months")),
    "processing_fee_paise": lambda f, c: _fees(f, "processing"),
    "fees_total_paise": lambda f, c: _fees(f),
    "kfs_validity_working_days": lambda f, c: _kfs(c)["validity_working_days"],
    "apr_computation_sheet": lambda f, c: _kfs(c)["apr_percent"] is not None,
}


def _inputs(key: str) -> list[str]:
    """The stored facts a fact is computed from, in order (for "Missing: ..." lists)."""
    fact = BY_KEY[key]
    if fact.parts:
        return [n for p in fact.parts for n in _inputs(p)]
    return {
        "household_income_monthly_paise": ["household_income_annual_paise"],
        "new_emi_paise": ["amount_paise", "tenor_months", "rate_bps_month"],
        "processing_fee_paise": ["amount_paise"],
        "fees_total_paise": ["amount_paise"],
    }.get(key, [key] if fact.stored else [])


def value(key: str, facts: dict[str, Any], ctx: dict[str, Any]) -> Any:
    """The fact's value. Raises NotInCatalogue or Missing (with every missing input)."""
    fact = get(key)
    missing = [n for n in _inputs(key) if facts.get(n) is None]
    if missing:
        raise Missing(missing)
    if fact.parts:
        return sum(value(p, facts, ctx) for p in fact.parts)
    if fact.stored:
        return facts[key]
    return DERIVE[key](facts, ctx)


def values(keys: list[str], facts: dict[str, Any], ctx: dict[str, Any]) -> list[Any]:
    """Several facts at once; Missing lists every missing input across all of them, in order."""
    for k in keys:
        get(k)
    missing: list[str] = []
    for k in keys:
        for n in _inputs(k):
            if facts.get(n) is None and n not in missing:
                missing.append(n)
    if missing:
        raise Missing(missing)
    return [value(k, facts, ctx) for k in keys]


def show(fact: Fact, v: Any) -> Any:
    """A fact's value as shown in a result ("₹22,000", 3, true)."""
    if fact.unit.startswith("paise"):
        return fin.rupees(v)
    return v


def match(text: str, among: tuple[str, ...] | None = None) -> str | None:
    """The catalogue fact whose wording appears in the text: the longest phrase wins."""
    lower = " ".join(text.split()).casefold()
    best: tuple[int, str] | None = None
    for f in CATALOGUE:
        if among is not None and f.key not in among:
            continue
        for w in f.words:
            if w in lower and (best is None or len(w) > best[0]):
                best = (len(w), f.key)
    return best[1] if best else None


# Fields of each template that name a fact, and whether the engine needs it.
FACT_FIELDS: dict[str, dict[str, bool]] = {
    "max_amount": {"fact": True, "must_be_false": False},
    "max_ratio": {"numerator_fact": True, "denominator_fact": True},
    "min_days": {"fact": True},
    "prohibited_charge": {"fact": True},
    "required_disclosure": {"fact": True},
    "time_window": {},
}


def notes(template: str, params: dict[str, Any]) -> list[str]:
    """Why the engine will refer this rule for want of a fact. Not a bar to approval."""
    out = []
    for name, required in FACT_FIELDS.get(template, {}).items():
        key = params.get(name)
        if key and key not in BY_KEY:
            out.append(f"{name}: fact not in catalogue ({key}); the rule evaluates as refer.")
        elif not key and required:
            out.append(f"{name}: no fact chosen; the rule evaluates as refer.")
    return out
