"""Six fictional Lender A applications that cover every path through the loan flow.

Each one goes through the real service (engine, snapshot, events, audit) at fixed dates, so
nothing here is a stored result and the engine runs on the day of each step (KFS validity counts
KF-01's working days from that day). Names are fictional. Amounts are in paise.

Idempotent: an application whose ref exists with the same submission time is left alone. One
seeded earlier with another time is deleted and taken through the flow again (reported as
re-dated), so every machine ends up with the same dates.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity import service as identity
from app.identity.deps import User
from app.loans import service
from app.loans.models import Application

R = 100  # paise per rupee
IST = ZoneInfo("Asia/Kolkata")


def ist(month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=IST)


@dataclass
class Spec:
    ref: str
    name: str
    purpose: str
    amount: int
    tenor: int
    income: int | None
    existing: int | None
    # Submitted (and checked by the engine) at this time.
    at: datetime
    # Steps after submission, each at its own time: ("recommend", recommendation, amount|None,
    # note, at) and ("decide", outcome, amount|None, note, at).
    steps: list[tuple] = field(default_factory=list)
    own: bool = False  # submitted by the borrower user, so it shows on the borrower pages


APPLICATIONS = [
    # The worked example: MF-02 fails at ₹80,000; approved at the largest amount that fits.
    Spec("APP-2026-0142", "Rekha K.", "Two sewing machines for a tailoring unit",
         80_000 * R, 24, 2_64_000 * R, 7_500 * R, ist(10, 12, 10, 12), own=True, steps=[
             ("recommend", "approve_modified", 66_000 * R,
              "MF-02 fails at the amount asked for. Offer the largest amount that fits.",
              ist(10, 12, 11, 30)),
             ("decide", "modify", 66_000 * R,
              "Approved at ₹66,000, the largest amount within MF-02 at 24 months.",
              ist(10, 12, 11, 42)),
         ]),
    # Clean pass, approved.
    Spec("APP-2026-0137", "Sunita D.", "Stock for a grocery shop",
         30_000 * R, 12, 1_80_000 * R, 2_000 * R, ist(10, 20, 9, 40), steps=[
             ("recommend", "approve", None, "All origination rules pass.", ist(10, 20, 10, 5)),
             ("decide", "approve", None, None, ist(10, 20, 10, 18)),
         ]),
    # Rejected: existing repayments already use the whole limit, so no amount fits.
    Spec("APP-2026-0139", "Kavita S.", "Two goats",
         25_000 * R, 12, 1_20_000 * R, 6_000 * R, ist(10, 28, 14, 5), steps=[
             ("recommend", "reject", None,
              "Existing repayments already exceed the MF-02 limit; no smaller loan fits.",
              ist(10, 28, 14, 31)),
             ("decide", "reject", None,
              ("Rejected under MF-02. Para 57: no new loan until the household is back "
              "within the limit."), ist(10, 28, 15, 2)),
         ]),
    # Pass, recommended, waiting for the checker.
    Spec("APP-2026-0145", "Meena P.", "Vegetable cart",
         40_000 * R, 18, 2_40_000 * R, 3_000 * R, ist(11, 9, 11, 15), steps=[
             ("recommend", "approve", None, "All origination rules pass.", ist(11, 9, 11, 48)),
         ]),
    # Refer: household income not given, waiting for the officer.
    Spec("APP-2026-0148", "Lakshmi R.", "Tea stall equipment",
         35_000 * R, 12, None, 1_500 * R, ist(11, 16, 12, 20)),
    # Fail with an offer, waiting for the officer.
    Spec("APP-2026-0150", "Fatima B.", "Embroidery machine",
         1_00_000 * R, 24, 2_16_000 * R, 4_000 * R, ist(11, 23, 16, 45)),
]


async def _user(session: AsyncSession, role: str) -> User:
    row = await identity.first_user_with_role(session, role)
    assert row is not None, f"no {role} user: seed users first"
    return User(row.id, row.org_id, row.role, row.name)


async def seed_loans(session: AsyncSession) -> tuple[list[str], list[str]]:
    """Returns (created or re-dated refs, refs already present)."""
    borrower = await _user(session, "borrower")
    officer = await _user(session, "officer")
    checker = await _user(session, "checker")
    created, present = [], []
    for spec in APPLICATIONS:
        old = await session.scalar(select(Application).where(Application.ref == spec.ref))
        if old is not None and abs(old.created_at - spec.at) < timedelta(seconds=1):
            present.append(spec.ref)
            continue
        if old is not None:
            await session.delete(old)  # its evaluations, decision and events go with it
            await session.flush()
        app = await service.create_application(session, borrower if spec.own else officer, {
            "ref": spec.ref, "product": "MFL", "amount_paise": spec.amount,
            "tenor_months": spec.tenor, "purpose": spec.purpose, "borrower_name": spec.name,
            "household_income_annual_paise": spec.income,
            "existing_monthly_repayments_paise": spec.existing,
        }, at=spec.at)
        for kind, choice, amount, note, at in spec.steps:
            if kind == "recommend":
                await service.recommend(session, officer, app.id, choice, amount, note, at=at)
            else:
                await service.decide(session, checker, app.id, choice, amount, note, at=at)
        created.append(f"{spec.ref} (re-dated)" if old is not None else spec.ref)
    return created, present
