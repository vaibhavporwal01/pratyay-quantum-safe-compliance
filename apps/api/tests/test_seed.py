"""The seed: real PDFs, approved rules with values from the text, and safe to re-run."""

from sqlalchemy import func, select

from app.rules.models import Rule, SourceDoc
from app.rules.seed import RULES, read_header, seed

SEEDED = {s.code for s in RULES}


async def test_seed_is_idempotent_and_values_come_from_text(session) -> None:
    first = await seed(session)
    assert first.left_out == [] and first.problems == []
    assert set(first.created) == SEEDED

    second = await seed(session)
    assert second.created == [] and set(second.skipped) == SEEDED
    assert await session.scalar(select(func.count()).select_from(SourceDoc)) == 2
    assert await session.scalar(
        select(func.count()).select_from(Rule).where(Rule.code.in_(SEEDED))
    ) == len(SEEDED)

    rules = {r.code: r for r in await session.scalars(select(Rule).where(Rule.code.in_(SEEDED)))}
    assert all(r.status == "approved" for r in rules.values())
    assert all(r.made_by != r.checked_by for r in rules.values())
    assert rules["MF-01"].params["max_paise"] == 30_000_000
    assert rules["MF-02"].params["max_percent"] == "50"
    assert [x["para"] for x in rules["MF-02"].related] == ["56", "57"]
    assert rules["KF-01"].params["tiers"] == [
        {"min_days": 3, "tenor_days_min": 7}, {"min_days": 1, "tenor_days_below": 7}
    ]
    assert (rules["MF-05"].params["start"], rules["MF-05"].params["end"]) == ("09:00", "18:00")
    # RBC 81 is limited to microfinance loans, as the paragraph says.
    assert rules["MF-04"].applies_to == "microfinance"
    assert rules["MF-04"].params["scope"] == "microfinance loans"
    assert {str(r.effective_from) for r in rules.values()} == {"2025-11-28"}


def test_header_gives_reference_and_issue_date() -> None:
    from app.rules.seed import CF_FILE, SOURCES

    ref, issued = read_header((SOURCES / CF_FILE).read_bytes())
    assert ref == "RBI/DOR/2025-26/347" and str(issued) == "2025-11-28"
