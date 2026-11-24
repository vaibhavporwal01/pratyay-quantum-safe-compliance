"""Loan arithmetic: EMI, rounding, largest loan, APR (RBC Annex I) and working days."""

from datetime import date
from decimal import Decimal
from fractions import Fraction

from app.rules import finance as fin


def test_rbc_annex_i_apr_is_17_07() -> None:
    # RBC Annex I: ₹20,000 at 15% a year (1.25% a month), 24 EMIs, fees ₹400, net ₹19,600.
    exact = fin.emi_exact(20_000_00, 125, 24)
    assert fin.rupees(exact) == "₹969.73"
    assert fin.apr_percent(19_600_00, exact, 24) == Decimal("17.07")


def test_emi_rounds_to_nearest_rupee_half_up() -> None:
    assert fin.emi(80_000_00, 200, 24) == 4_230_00  # exact ₹4,229.69
    assert fin.emi(66_000_00, 200, 24) == 3_489_00  # exact ₹3,489.49
    assert fin.round_half_up(Fraction(150), 100) == 200
    assert fin.round_half_up(Fraction(149), 100) == 100


def test_largest_loan_rounds_down_to_the_step() -> None:
    assert fin.rupees(fin.principal_for_emi(3_500_00, 200, 24)) == "₹66,198.74"
    assert fin.largest_loan(3_500_00, 200, 24, 1_000_00) == 66_000_00
    assert fin.largest_loan(0, 200, 24, 1_000_00) == 0
    assert fin.largest_loan(-5_00, 200, 24, 1_000_00) == 0


def test_zero_rate_and_formatting() -> None:
    assert fin.emi_exact(12_000_00, 0, 12) == 1_000_00
    assert fin.rupees(2_64_000_00) == "₹2,64,000"
    assert fin.rupees(1_00_00_000_00) == "₹1,00,00,000"
    assert fin.percent(11_730, 22_000) == "53.3"
    assert fin.fee_paise(80_000_00, {"bps": 100}) == 800_00
    assert fin.fee_paise(80_000_00, {"paise": 250_00}) == 250_00


def test_working_days_skip_weekends() -> None:
    friday = date(2026, 11, 27)
    assert fin.add_working_days(friday, 3) == date(2026, 12, 2)
    assert fin.add_working_days(date(2026, 11, 25), 3) == date(2026, 11, 30)
    assert fin.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
