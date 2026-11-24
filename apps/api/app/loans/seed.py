"""Six fictional Lender A applications that cover every path through the loan flow.

Idempotent: an application whose ref already exists is left alone. Each one goes through the
real service (engine, snapshot, events, audit), so nothing here is a stored result. Names are
fictional. Amounts are in paise.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity import service as identity
from app.identity.deps import User
from app.loans import service
from app.loans.models import Application

R = 100  # paise per rupee


@dataclass
class Spec:
    ref: str
    name: str
    purpose: str
    amount: int
    tenor: int
    income: int | None
    existing: int | None
    # Steps after submission: ("recommend", recommendation, amount|None, note) and
    # ("decide", outcome, amount|None, note).
    steps: list[tuple] = field(default_factory=list)
    own: bool = False  # submitted by the borrower user, so it shows on the borrower pages


APPLICATIONS = [
    # The worked example: MF-02 fails at ₹80,000; approved at the largest amount that fits.
    Spec("APP-2026-0142", "Rekha K.", "Two sewing machines for a tailoring unit",
         80_000 * R, 24, 2_64_000 * R, 7_500 * R, own=True, steps=[
             ("recommend", "approve_modified", 66_000 * R,
              "MF-02 fails at the amount asked for. Offer the largest amount that fits."),
             ("decide", "modify", 66_000 * R,
              "Approved at ₹66,000, the largest amount within MF-02 at 24 months."),
         ]),
    # Clean pass, approved.
    Spec("APP-2026-0137", "Sunita D.", "Stock for a grocery shop",
         30_000 * R, 12, 1_80_000 * R, 2_000 * R, steps=[
             ("recommend", "approve", None, "All origination rules pass."),
             ("decide", "approve", None, None),
         ]),
    # Rejected: existing repayments already use the whole limit, so no amount fits.
    Spec("APP-2026-0139", "Kavita S.", "Two goats",
         25_000 * R, 12, 1_20_000 * R, 6_000 * R, steps=[
             ("recommend", "reject", None,
              "Existing repayments already exceed the MF-02 limit; no smaller loan fits."),
             ("decide", "reject", None,
              ("Rejected under MF-02. Para 57: no new loan until the household is back "
              "within the limit.")),
         ]),
    # Pass, recommended, waiting for the checker.
    Spec("APP-2026-0145", "Meena P.", "Vegetable cart",
         40_000 * R, 18, 2_40_000 * R, 3_000 * R, steps=[
             ("recommend", "approve", None, "All origination rules pass."),
         ]),
    # Refer: household income not given, waiting for the officer.
    Spec("APP-2026-0148", "Lakshmi R.", "Tea stall equipment",
         35_000 * R, 12, None, 1_500 * R),
    # Fail with an offer, waiting for the officer.
    Spec("APP-2026-0150", "Fatima B.", "Embroidery machine",
         1_00_000 * R, 24, 2_16_000 * R, 4_000 * R),
]


async def _user(session: AsyncSession, role: str) -> User:
    row = await identity.first_user_with_role(session, role)
    assert row is not None, f"no {role} user: seed users first"
    return User(row.id, row.org_id, row.role, row.name)


async def seed_loans(session: AsyncSession) -> tuple[list[str], list[str]]:
    """Returns (created refs, refs already present)."""
    borrower = await _user(session, "borrower")
    officer = await _user(session, "officer")
    checker = await _user(session, "checker")
    created, present = [], []
    for spec in APPLICATIONS:
        if await session.scalar(select(Application.id).where(Application.ref == spec.ref)):
            present.append(spec.ref)
            continue
        app = await service.create_application(session, borrower if spec.own else officer, {
            "ref": spec.ref, "product": "MFL", "amount_paise": spec.amount,
            "tenor_months": spec.tenor, "purpose": spec.purpose, "borrower_name": spec.name,
            "household_income_annual_paise": spec.income,
            "existing_monthly_repayments_paise": spec.existing,
        })
        for step in spec.steps:
            if step[0] == "recommend":
                await service.recommend(session, officer, app.id, step[1], step[2], step[3])
            else:
                await service.decide(session, checker, app.id, step[1], step[2], step[3])
        created.append(spec.ref)
    return created, present
