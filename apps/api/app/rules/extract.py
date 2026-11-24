"""Value extraction: find the numbers a rule can use in a paragraph, with their text spans.

Kinds:
- amount:   "₹3,00,000", "Rs. 50,000", "₹1 lakh", "₹1,000 crore"  -> value in paise (int)
- percent:  "50 per cent", "12.5%"                                -> Decimal as str
- days:     "15 days", "three working days", "one working day"   -> int, unit day | working_day
- time:     "9:00 a.m.", "6 p.m.", "19:00 hours"                  -> "HH:MM" (24 hour)
- para_ref: "paragraph 34(1)", "paras 55 to 57"                   -> "34(1)", "55", "57"

Only regular expressions and lookup tables: nothing is evaluated. A value that is not in the
text comes back as Missing, never as a guess.
"""

import re
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Literal

Kind = Literal["amount", "percent", "days", "time", "para_ref"]
KINDS: tuple[Kind, ...] = ("amount", "percent", "days", "time", "para_ref")


@dataclass(frozen=True)
class Value:
    kind: Kind
    value: int | str
    text: str
    start: int
    end: int
    unit: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Missing:
    kind: Kind
    reason: str

    def as_dict(self) -> dict:
        return {"kind": self.kind, "missing": True, "reason": self.reason}


WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45, "sixty": 60, "ninety": 90,
}
MULTIPLIERS = {"lakh": 100_000, "lakhs": 100_000, "crore": 10_000_000, "crores": 10_000_000}

_NUM = r"\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_AMOUNT_RE = re.compile(
    rf"(?:₹|\bRs\.?|\bINR)\s?(?P<num>{_NUM})(?:\s*(?P<mult>lakhs?|crores?)\b)?"
    rf"|\b(?P<num2>{_NUM})\s*(?P<mult2>lakhs?|crores?)\b",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(r"\b(?P<num>\d+(?:\.\d+)?)\s*(?:per\s?cent\b|percent\b|%)", re.IGNORECASE)
_WORDS = "|".join(sorted(map(re.escape, WORD_NUMBERS), key=len, reverse=True))
_DAYS_RE = re.compile(
    rf"\b(?P<num>\d+|{_WORDS})\s+(?P<working>working\s+|business\s+)?days?\b", re.IGNORECASE
)
_TIME_RE = re.compile(
    r"\b(?P<h>\d{1,2})(?:[:.](?P<m>\d{2}))?\s*(?P<ampm>a\.m\.|p\.m\.|am\b|pm\b)"
    r"|\b(?P<h24>[01]\d|2[0-3]):(?P<m24>[0-5]\d)\s*(?:hours|hrs)\b",
    re.IGNORECASE,
)
_PARA_NUM = r"\d+[A-Z]*(?:\(\d+\))*"
_PARA_RE = re.compile(
    rf"\b(?:paragraphs?|paras?)\s+(?P<list>{_PARA_NUM}(?:\s*(?:,|and|to|-|–)\s*{_PARA_NUM})*)",
    re.IGNORECASE,
)
_PARA_ITEM_RE = re.compile(_PARA_NUM)


def _to_number(raw: str) -> Decimal:
    return Decimal(raw.replace(",", ""))


def _amounts(text: str) -> list[Value]:
    out = []
    for m in _AMOUNT_RE.finditer(text):
        num = m.group("num") or m.group("num2")
        mult = (m.group("mult") or m.group("mult2") or "").lower()
        rupees = _to_number(num) * MULTIPLIERS.get(mult, 1)
        out.append(Value("amount", int(rupees * 100), m.group(0), m.start(), m.end(), "paise"))
    return out


def _percents(text: str) -> list[Value]:
    return [
        Value("percent", str(_to_number(m.group("num"))), m.group(0), m.start(), m.end(), "%")
        for m in _PERCENT_RE.finditer(text)
    ]


def _days(text: str) -> list[Value]:
    out = []
    for m in _DAYS_RE.finditer(text):
        raw = m.group("num").lower()
        n = int(raw) if raw.isdigit() else WORD_NUMBERS[raw]
        unit = "working_day" if m.group("working") else "day"
        out.append(Value("days", n, m.group(0), m.start(), m.end(), unit))
    return out


def _times(text: str) -> list[Value]:
    out = []
    for m in _TIME_RE.finditer(text):
        if m.group("h24"):
            hh, mm = int(m.group("h24")), int(m.group("m24"))
        else:
            hh, mm = int(m.group("h")), int(m.group("m") or 0)
            if hh < 1 or hh > 12 or mm > 59:
                continue
            pm = m.group("ampm").lower().startswith("p")
            hh = (hh % 12) + (12 if pm else 0)
        out.append(Value("time", f"{hh:02d}:{mm:02d}", m.group(0), m.start(), m.end()))
    return out


def _para_refs(text: str) -> list[Value]:
    out = []
    for m in _PARA_RE.finditer(text):
        base = m.start("list")
        for item in _PARA_ITEM_RE.finditer(m.group("list")):
            s, e = base + item.start(), base + item.end()
            out.append(Value("para_ref", item.group(0), text[s:e], s, e))
    return out


_FINDERS = {
    "amount": _amounts,
    "percent": _percents,
    "days": _days,
    "time": _times,
    "para_ref": _para_refs,
}


def extract(text: str, kinds: tuple[Kind, ...] = KINDS) -> list[Value]:
    """Every value of the given kinds in document order. Spans index into `text`."""
    values = [v for k in kinds for v in _FINDERS[k](text)]
    return sorted(values, key=lambda v: (v.start, v.kind))


def find(text: str, kind: Kind, nth: int = 0) -> Value | Missing:
    """The nth value of one kind, or Missing when the text has no such value."""
    values = _FINDERS[kind](text)
    if nth < len(values):
        return values[nth]
    return Missing(kind, f"no {kind.replace('_', ' ')} found in the paragraph text")
