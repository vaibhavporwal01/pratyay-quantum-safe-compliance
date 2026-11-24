"""Rule templates: params validation, numbers tied to the quoted text, boundary tests."""

import pytest

from app.rules import templates as t
from tests.helpers import CF_55

TIME_TEXT = "calling the borrower before 9:00 a.m. and after 6:00 p.m."


def test_unknown_template_and_bad_params_are_rejected() -> None:
    with pytest.raises(t.TemplateError, match="unknown template"):
        t.validate_params("max_speed", {})
    with pytest.raises(t.TemplateError, match="max_percent"):
        t.validate_params("max_ratio", {"numerator": "a", "denominator": "b", "max_percent": 150})
    with pytest.raises(t.TemplateError, match="start"):
        t.validate_params("time_window", {"activity": "call", "start": "9am", "end": "18:00"})
    with pytest.raises(t.TemplateError, match="amount: Extra inputs"):
        t.validate_params("prohibited_charge", {"charge": "x", "amount": 5})


def test_every_template_has_a_model() -> None:
    assert set(t.TEMPLATE_NAMES) == set(t.MODELS)


def test_number_must_appear_in_quoted_text() -> None:
    ok = {"numerator": "repayments", "denominator": "income", "max_percent": "50"}
    assert t.check_against_text("max_ratio", ok, CF_55) == []
    bad = {**ok, "max_percent": "60"}
    assert t.check_against_text("max_ratio", bad, CF_55) == [
        "max_percent: 60 is not in the quoted text"
    ]


def test_number_must_match_kind() -> None:
    # 50 is in the text as a percentage, not as an amount in rupees.
    errors = t.check_against_text("max_amount", {"subject": "x", "max_paise": 5000}, CF_55)
    assert errors == ["max_paise: 5000 is not in the quoted text"]


def test_scope_must_be_copied_word_for_word() -> None:
    params = {"charge": "pre-payment charge", "scope": "microfinance loans"}
    text = "There shall be no pre-payment charge levied on microfinance loans."
    assert t.check_against_text("prohibited_charge", params, text) == []
    widened = {**params, "scope": "all loans"}
    assert t.check_against_text("prohibited_charge", widened, text) == [
        "scope: 'all loans' is not copied from the quoted text"
    ]


def test_missing_values_are_listed_and_block_evaluation() -> None:
    params = {"activity": "call", "start": "09:00", "end": None}
    assert t.missing_values("time_window", params) == ["end"]
    assert t.boundary_tests("time_window", params) == []
    with pytest.raises(t.TemplateError, match="end: value missing"):
        t.evaluate("time_window", params, {"time": "10:00"})


@pytest.mark.parametrize(
    ("template", "params"),
    [
        ("max_amount", {"subject": "income", "max_paise": 30_000_000}),
        ("max_ratio", {"numerator": "emi", "denominator": "income", "max_percent": "50"}),
        ("min_days", {"subject": "KFS validity", "working_days": True, "tiers": [
            {"min_days": 3, "tenor_days_min": 7}, {"min_days": 1, "tenor_days_below": 7}]}),
        ("time_window", {"activity": "call", "start": "09:00", "end": "18:00"}),
        ("prohibited_charge", {"charge": "pre-payment charge"}),
        ("required_disclosure", {"item": "APR"}),
    ],
)
def test_boundary_tests_pass_for_every_template(template: str, params: dict) -> None:
    tests = t.boundary_tests(template, params)
    assert len(tests) >= 2
    assert all(x.passed for x in tests), [x.as_dict() for x in tests]
    assert {x.expected for x in tests} == {True, False}


def test_ratio_boundary_is_inclusive() -> None:
    p = {"numerator": "emi", "denominator": "income", "max_percent": "50"}
    assert t.evaluate("max_ratio", p, {"ratio_percent": "50.0"})
    assert not t.evaluate("max_ratio", p, {"ratio_percent": "50.1"})


def test_min_days_tiers_by_tenor() -> None:
    p = {"subject": "KFS", "tiers": [{"min_days": 3, "tenor_days_min": 7},
                                     {"min_days": 1, "tenor_days_below": 7}]}
    assert not t.evaluate("min_days", p, {"tenor_days": 30, "days": 2})
    assert t.evaluate("min_days", p, {"tenor_days": 30, "days": 3})
    assert t.evaluate("min_days", p, {"tenor_days": 5, "days": 1})


def test_suggest_takes_numbers_only_from_text() -> None:
    s = t.suggest(TIME_TEXT)
    assert s["template"] == "time_window"
    assert (s["params"]["start"], s["params"]["end"]) == ("09:00", "18:00")
    assert s["missing"] == []
    s = t.suggest(CF_55)
    assert s["template"] == "max_ratio" and s["params"]["max_percent"] == "50"
    s = t.suggest("There shall be no pre-payment charge levied on microfinance loans.")
    assert s["template"] == "prohibited_charge"


def test_no_eval_or_exec_in_rule_engine() -> None:
    from pathlib import Path

    rules_dir = Path(t.__file__).parent
    for f in rules_dir.glob("*.py"):
        src = f.read_text()
        assert "eval(" not in src.replace("evaluate(", "") and "exec(" not in src, f.name
