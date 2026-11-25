"""Loan arithmetic for the rule engine. Exact: integers and fractions, never floats.

Money is in paise (int). Rates are basis points per month (200 = 2% a month).

Rounding, stated once and used everywhere:
- EMI: reducing-balance formula, exact, then rounded to the nearest whole rupee, half up.
  The borrower pays the rounded EMI. Ratio checks use the rounded EMI.
- Fees given in basis points: rounded to the nearest whole rupee, half up.
- Largest loan for an EMI: exact, then rounded DOWN to the product's offer step, and stepped
  down again if the rounded EMI would still exceed the limit.
- APR: 12 x the monthly internal rate of return of the net disbursal against the UNROUNDED
  EMI, as in RBC Annex I ("computed on net disbursed amount using IRR approach and reducing
  balance method"). Shown to two decimals, half up.
- Percentages for display: one or two decimals, half up.
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction

PAISE_PER_RUPEE = 100
BPS = 10_000


def monthly_rate(rate_bps_month: int) -> Fraction:
    return Fraction(rate_bps_month, BPS)


def emi_exact(principal_paise: int, rate_bps_month: int, months: int) -> Fraction:
    """Reducing-balance EMI, exact, in paise: P r (1+r)^n / ((1+r)^n - 1)."""
    if months <= 0:
        raise ValueError("tenor must be at least one month")
    r = monthly_rate(rate_bps_month)
    if r == 0:
        return Fraction(principal_paise, months)
    f = (1 + r) ** months
    return principal_paise * r * f / (f - 1)


def round_half_up(x: Fraction, step: int = 1) -> int:
    """Nearest multiple of step, halves away from zero (inputs here are never negative)."""
    q, rem = divmod(x, step)
    return int(q * step + (step if rem * 2 >= step else 0))


def round_down(x: Fraction | int, step: int) -> int:
    return int(Fraction(x) // step) * step


def to_rupee(paise: Fraction) -> int:
    """Paise, rounded to the nearest whole rupee (half up), still in paise."""
    return round_half_up(Fraction(paise), PAISE_PER_RUPEE)


def emi(principal_paise: int, rate_bps_month: int, months: int) -> int:
    """The EMI the borrower pays: exact EMI rounded to the nearest rupee."""
    return to_rupee(emi_exact(principal_paise, rate_bps_month, months))


def principal_for_emi(emi_paise: Fraction | int, rate_bps_month: int, months: int) -> Fraction:
    """The exact principal whose EMI is emi_paise: E ((1+r)^n - 1) / (r (1+r)^n)."""
    r = monthly_rate(rate_bps_month)
    if r == 0:
        return Fraction(emi_paise) * months
    f = (1 + r) ** months
    return Fraction(emi_paise) * (f - 1) / (r * f)


def largest_loan(max_emi_paise: Fraction | int, rate_bps_month: int, months: int, step_paise: int) -> int:
    """The largest loan, in whole steps, whose rounded EMI is within max_emi_paise. 0 if none."""
    if max_emi_paise <= 0:
        return 0
    amount = round_down(principal_for_emi(max_emi_paise, rate_bps_month, months), step_paise)
    while amount > 0 and emi(amount, rate_bps_month, months) > max_emi_paise:
        amount -= step_paise
    return max(amount, 0)


def fee_paise(amount_paise: int, fee: dict) -> int:
    """A fee is either a fixed {"paise"} or a share of the loan {"bps"}, rounded to the rupee."""
    if "paise" in fee:
        return int(fee["paise"])
    return to_rupee(Fraction(amount_paise * int(fee["bps"]), BPS))


def monthly_irr(net_disbursal_paise: int, emi_paise: Fraction, months: int) -> Decimal:
    """Monthly IRR as a fraction (0.02089...). Bisection on the annuity equation."""
    if net_disbursal_paise <= 0:
        raise ValueError("net disbursal must be positive")
    with localcontext() as ctx:
        ctx.prec = 60
        net = Decimal(net_disbursal_paise)
        e = Decimal(emi_paise.numerator) / Decimal(emi_paise.denominator)
        if e * months <= net:
            return Decimal(0)

        def pv(m: Decimal) -> Decimal:
            return e * (1 - (1 + m) ** -months) / m

        lo, hi = Decimal("1e-12"), Decimal(1)
        for _ in range(200):
            mid = (lo + hi) / 2
            if pv(mid) > net:
                lo = mid
            else:
                hi = mid
        return lo


def apr_percent(net_disbursal_paise: int, emi_paise: Fraction, months: int) -> Decimal:
    """12 x monthly IRR, in percent, two decimals."""
    m = monthly_irr(net_disbursal_paise, emi_paise, months)
    return (m * 12 * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def percent(num: Fraction | int, den: Fraction | int, places: int = 1) -> str:
    """num / den as a percentage string, e.g. "53.3"."""
    value = Fraction(num) / Fraction(den) * 100
    q = Decimal(1).scaleb(-places)
    return str((Decimal(value.numerator) / Decimal(value.denominator)).quantize(q, ROUND_HALF_UP))


def rupees(paise: int | Fraction) -> str:
    """Indian grouping, whole rupees or with paise when not whole: ₹2,64,000 or ₹969.73."""
    p = Fraction(paise)
    whole, frac = divmod(round_half_up(p), PAISE_PER_RUPEE)
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join([*groups, tail])
    return f"₹{s}" if frac == 0 else f"₹{s}.{frac:02d}"


def add_working_days(start: date, days: int) -> date:
    """start plus `days` working days. Saturdays and Sundays are not working days. Public
    holidays are not modelled."""
    d, left = start, days
    while left > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            left -= 1
    return d


def add_months(start: date, months: int) -> date:
    y, m = divmod(start.month - 1 + months, 12)
    year, month = start.year + y, m + 1
    for day in (start.day, 30, 29, 28):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    raise ValueError("bad date")
