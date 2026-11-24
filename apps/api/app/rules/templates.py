"""Typed rule templates.

Each template is a Pydantic model for a rule's params. Three checks keep a rule honest:

- validate_params:   the params fit the template.
- check_against_text: every number in the params appears in the quoted paragraph (found by the
  extractor, same kind), and every `scope` phrase is copied word for word from the source.
- missing_values:    numbers the maker has not filled in yet. A rule with any cannot be approved.

`evaluate` runs one rule on a set of facts, and `boundary_tests` builds the cases either side of
each limit. Plain comparisons only; there is no eval or exec here.
"""

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.rules.extract import Kind, extract

TemplateName = Literal[
    "max_amount",
    "max_ratio",
    "min_days",
    "time_window",
    "prohibited_charge",
    "required_disclosure",
]
TEMPLATE_NAMES: tuple[str, ...] = TemplateName.__args__  # type: ignore[attr-defined]

TIME = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]


class _Params(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Words copied from the source that limit who or what the rule covers.
    scope: str | None = None


class MaxAmount(_Params):
    """subject <= max_paise (e.g. annual household income up to ₹3,00,000)."""

    subject: str = Field(min_length=1)
    max_paise: int | None = Field(default=None, ge=0)


class MaxRatio(_Params):
    """numerator / denominator <= max_percent."""

    numerator: str = Field(min_length=1)
    denominator: str = Field(min_length=1)
    max_percent: Decimal | None = Field(default=None, ge=0, le=100)
    exclude: list[str] = []


class DaysTier(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_days: int | None = Field(default=None, ge=0)
    # Optional condition on the loan tenor, in days: tenor >= tenor_days_min, tenor < below.
    tenor_days_min: int | None = Field(default=None, ge=0)
    tenor_days_below: int | None = Field(default=None, ge=0)


class MinDays(_Params):
    """subject lasts at least min_days (per tier)."""

    subject: str = Field(min_length=1)
    working_days: bool = False
    tiers: list[DaysTier] = Field(min_length=1)


class TimeWindow(_Params):
    """activity only between start and end, inclusive."""

    activity: str = Field(min_length=1)
    start: TIME | None = None
    end: TIME | None = None


class ProhibitedCharge(_Params):
    charge: str = Field(min_length=1)
    unless: str | None = None


class RequiredDisclosure(_Params):
    item: str = Field(min_length=1)
    includes: list[str] = []


MODELS: dict[str, type[_Params]] = {
    "max_amount": MaxAmount,
    "max_ratio": MaxRatio,
    "min_days": MinDays,
    "time_window": TimeWindow,
    "prohibited_charge": ProhibitedCharge,
    "required_disclosure": RequiredDisclosure,
}


class TemplateError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def validate_params(template: str, params: dict[str, Any]) -> _Params:
    model = MODELS.get(template)
    if model is None:
        raise TemplateError([f"unknown template {template!r}"])
    try:
        return model.model_validate(params)
    except ValidationError as exc:
        raise TemplateError(
            [f"{'.'.join(map(str, e['loc'])) or 'params'}: {e['msg']}" for e in exc.errors()]
        ) from exc


# ---- numbers and where they must come from ---------------------------------------------


@dataclass(frozen=True)
class NumberSlot:
    path: str
    kind: Kind
    value: int | str | None


def canon_percent(d: Decimal) -> str:
    """50, 50.0 and 50.00 all become "50"; 12.50 becomes "12.5"."""
    return format(d.normalize(), "f")


def number_slots(template: str, p: _Params) -> list[NumberSlot]:
    """Every numeric field of the params, with the extractor kind it must match."""
    match p:
        case MaxAmount():
            return [NumberSlot("max_paise", "amount", p.max_paise)]
        case MaxRatio():
            pct = None if p.max_percent is None else canon_percent(p.max_percent)
            return [NumberSlot("max_percent", "percent", pct)]
        case MinDays():
            slots = []
            for i, t in enumerate(p.tiers):
                slots.append(NumberSlot(f"tiers.{i}.min_days", "days", t.min_days))
                if t.tenor_days_min is not None:
                    slots.append(NumberSlot(f"tiers.{i}.tenor_days_min", "days", t.tenor_days_min))
                if t.tenor_days_below is not None:
                    slots.append(
                        NumberSlot(f"tiers.{i}.tenor_days_below", "days", t.tenor_days_below)
                    )
            return slots
        case TimeWindow():
            return [NumberSlot("start", "time", p.start), NumberSlot("end", "time", p.end)]
    return []


def missing_values(template: str, params: dict[str, Any]) -> list[str]:
    p = validate_params(template, params)
    return [s.path for s in number_slots(template, p) if s.value is None]


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def check_against_text(template: str, params: dict[str, Any], source_text: str) -> list[str]:
    """Problems with the params against the quoted text. Empty means every number and scope
    phrase is in the source. Missing numbers are not problems here (see missing_values)."""
    p = validate_params(template, params)
    found: dict[str, set] = {}
    for v in extract(source_text):
        found.setdefault(v.kind, set()).add(
            canon_percent(Decimal(v.value)) if v.kind == "percent" else v.value
        )
    errors = []
    for slot in number_slots(template, p):
        if slot.value is not None and slot.value not in found.get(slot.kind, set()):
            errors.append(f"{slot.path}: {slot.value} is not in the quoted text")
    if p.scope and _norm(p.scope) not in _norm(source_text):
        errors.append(f"scope: {p.scope!r} is not copied from the quoted text")
    return errors


# ---- evaluation ------------------------------------------------------------------------


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def evaluate(template: str, params: dict[str, Any], facts: dict[str, Any]) -> bool:
    """True when the facts satisfy the rule. Raises TemplateError if a value is missing."""
    p = validate_params(template, params)
    if missing := [s.path for s in number_slots(template, p) if s.value is None]:
        raise TemplateError([f"{m}: value missing" for m in missing])
    match p:
        case MaxAmount():
            return int(facts["amount_paise"]) <= p.max_paise
        case MaxRatio():
            return Decimal(str(facts["ratio_percent"])) <= p.max_percent
        case MinDays():
            tenor = facts.get("tenor_days")
            for t in p.tiers:
                if t.tenor_days_min is not None and (tenor is None or tenor < t.tenor_days_min):
                    continue
                if t.tenor_days_below is not None and (
                    tenor is None or tenor >= t.tenor_days_below
                ):
                    continue
                return int(facts["days"]) >= t.min_days
            return True  # no tier covers this tenor
        case TimeWindow():
            t = _minutes(facts["time"])
            return _minutes(p.start) <= t <= _minutes(p.end)
        case ProhibitedCharge():
            return not facts["charged"]
        case RequiredDisclosure():
            return bool(facts["disclosed"])
    raise TemplateError([f"no evaluator for {template}"])


@dataclass(frozen=True)
class BoundaryTest:
    label: str
    facts: dict[str, Any]
    expected: bool
    actual: bool

    @property
    def passed(self) -> bool:
        return self.expected == self.actual

    def as_dict(self) -> dict:
        return {**asdict(self), "passed": self.passed}


def _rupees(paise: int) -> str:
    r = paise // 100
    s = str(r)
    if len(s) > 3:  # Indian grouping: 3,00,000
        head, tail = s[:-3], s[-3:]
        head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
        s = f"{head},{tail}"
    return f"₹{s}"


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def boundary_tests(template: str, params: dict[str, Any]) -> list[BoundaryTest]:
    """Cases just inside and just outside each limit. Empty while a value is missing."""
    p = validate_params(template, params)
    if any(s.value is None for s in number_slots(template, p)):
        return []
    cases: list[tuple[str, dict, bool]] = []
    match p:
        case MaxAmount():
            for delta, ok in ((-100, True), (0, True), (100, False)):
                amt = p.max_paise + delta
                cases.append((f"{p.subject} {_rupees(amt)}", {"amount_paise": amt}, ok))
        case MaxRatio():
            step = Decimal("0.1")
            for delta, ok in ((-step, True), (Decimal(0), True), (step, False)):
                r = p.max_percent + delta
                cases.append((f"{r:.1f}% of {p.denominator}", {"ratio_percent": str(r)}, ok))
        case MinDays():
            unit = "working days" if p.working_days else "days"
            for t in p.tiers:
                tenor = t.tenor_days_min if t.tenor_days_min is not None else (
                    t.tenor_days_below - 1 if t.tenor_days_below else None
                )
                when = f", tenor {tenor} days" if tenor is not None else ""
                facts = {"tenor_days": tenor} if tenor is not None else {}
                if t.min_days > 0:
                    cases.append(
                        (f"{t.min_days - 1} {unit}{when}", {**facts, "days": t.min_days - 1},
                         False)
                    )
                cases.append((f"{t.min_days} {unit}{when}", {**facts, "days": t.min_days}, True))
        case TimeWindow():
            s, e = _minutes(p.start), _minutes(p.end)
            for m, ok in ((s - 1, False), (s, True), (e, True), (e + 1, False)):
                cases.append((f"{p.activity} at {_hhmm(m % 1440)}", {"time": _hhmm(m % 1440)}, ok))
        case ProhibitedCharge():
            cases += [
                (f"{p.charge} levied", {"charged": True}, False),
                (f"no {p.charge}", {"charged": False}, True),
            ]
        case RequiredDisclosure():
            cases += [
                (f"{p.item} given", {"disclosed": True}, True),
                (f"{p.item} not given", {"disclosed": False}, False),
            ]
    return [
        BoundaryTest(label, facts, expected, evaluate(template, params, facts))
        for label, facts, expected in cases
    ]


# ---- suggestion from a paragraph ------------------------------------------------------


def suggest(text: str) -> dict[str, Any]:
    """A first guess at template and params for a requirement paragraph. Numbers come only from
    the extractor; anything it cannot find stays None and is listed in `missing`."""
    lower = text.casefold()
    values = extract(text)
    first = {k: next((v for v in values if v.kind == k), None) for k in ("amount", "percent",
                                                                         "days", "time")}
    times = [v for v in values if v.kind == "time"]
    if len(times) >= 2:
        template, params = "time_window", {
            "activity": "contact", "start": times[0].value, "end": times[1].value}
    elif first["percent"]:
        template, params = "max_ratio", {
            "numerator": "", "denominator": "", "max_percent": first["percent"].value}
    elif first["days"]:
        template, params = "min_days", {
            "subject": "", "working_days": first["days"].unit == "working_day",
            "tiers": [{"min_days": first["days"].value}]}
    elif first["amount"]:
        template, params = "max_amount", {"subject": "", "max_paise": first["amount"].value}
    elif "charge" in lower and any(w in lower for w in ("no ", "not ", "cannot")):
        template, params = "prohibited_charge", {"charge": ""}
    else:
        template, params = "required_disclosure", {"item": ""}
    return {
        "template": template,
        "params": params,
        "missing": [k for k, v in params.items() if v is None],
        "values": [v.as_dict() for v in values],
    }
