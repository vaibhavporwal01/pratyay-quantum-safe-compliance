"""Value extractor on real paragraphs of the two RBI Directions, plus edge cases."""

from functools import cache
from pathlib import Path

import pytest

from app.rules.extract import Missing, Value, extract, find
from app.rules.ingest import parse_pdf

SOURCES = Path(__file__).resolve().parents[3] / "data" / "sources"


@cache
def paras(name: str) -> dict[str, str]:
    data = (SOURCES / f"rbi-nbfc-{name}-directions-2025.pdf").read_bytes()
    return {p.number: p.text for p in parse_pdf(data).paragraphs}


def cf(n: str) -> str:
    return paras("credit-facilities")[n]


def rbc(n: str) -> str:
    return paras("responsible-business-conduct")[n]


def spans_match(text: str, values: list[Value]) -> bool:
    return all(text[v.start:v.end] == v.text for v in values)


def test_cf_51_household_income_cap_in_paise() -> None:
    text = cf("51")
    amounts = [v for v in extract(text) if v.kind == "amount"]
    assert [v.value for v in amounts] == [30_000_000, 30_000_000]  # ₹3,00,000, twice
    assert amounts[0].text == "₹3,00,000"
    assert spans_match(text, amounts)


@pytest.mark.parametrize("n", ["55", "56", "57"])
def test_cf_55_to_57_fifty_per_cent(n: str) -> None:
    v = find(cf(n), "percent")
    assert isinstance(v, Value) and v.value == "50" and "per cent" in v.text


def test_rbc_29_2_working_days_and_tenor() -> None:
    text = rbc("29(2)")
    days = [v for v in extract(text) if v.kind == "days"]
    assert [(v.value, v.unit) for v in days] == [
        (3, "working_day"), (7, "day"), (1, "working_day"), (7, "day"),
    ]
    assert days[0].text == "three working days"
    assert spans_match(text, days)


def test_rbc_91_2_call_hours() -> None:
    times = [v for v in extract(rbc("91(2)")) if v.kind == "time"]
    assert [v.value for v in times] == ["09:00", "18:00"]
    assert [v.text for v in times] == ["9:00 a.m.", "6:00 p.m."]


def test_rbc_81_has_no_number_so_values_are_missing() -> None:
    text = rbc("81")
    assert extract(text, ("amount", "percent", "days", "time")) == []
    m = find(text, "percent")
    assert isinstance(m, Missing) and m.kind == "percent"


def test_rbc_6_1_definition_has_no_values() -> None:
    assert extract(rbc("6(1)")) == []


def test_paragraph_references_from_real_text() -> None:
    text = rbc("34(3)")
    refs = [v for v in extract(text) if v.kind == "para_ref"]
    assert [v.value for v in refs] == ["34(1)", "34(2)"]
    assert spans_match(text, refs)


@pytest.mark.parametrize(
    ("text", "paise"),
    [
        ("a loan of ₹1 lakh", 10_000_000),
        ("up to Rs. 50,000 only", 5_000_000),
        ("assets of ₹1,000 crore and above", 1_000_000_000_000),
        ("2.5 lakh rupees", 25_000_000),
    ],
)
def test_amount_forms(text: str, paise: int) -> None:
    v = find(text, "amount")
    assert isinstance(v, Value) and v.value == paise


@pytest.mark.parametrize(
    ("text", "hhmm"),
    [("after 6 p.m.", "18:00"), ("by 12:30 a.m.", "00:30"), ("from 08:00 hours", "08:00")],
)
def test_time_forms(text: str, hhmm: str) -> None:
    v = find(text, "time")
    assert isinstance(v, Value) and v.value == hhmm


def test_nth_beyond_count_is_missing_not_guessed() -> None:
    assert isinstance(find("within 15 days", "days", nth=1), Missing)
    assert find("within 15 days", "days").value == 15
