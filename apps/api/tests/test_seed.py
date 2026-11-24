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
    # KF-03 cites the KFS duty (29(3)); the APR definition (6(1)) is related context.
    assert rules["KF-03"].source_para == "29(3)"
    assert [x["para"] for x in rules["KF-03"].related] == ["29", "6(1)"]
    # MF-05's microfinance scope comes from its section heading, stored as context.
    assert rules["MF-05"].section == "H. Conduct towards Microfinance borrowers"
    assert rules["MF-01"].section is None


async def test_sources_store_explicit_short_codes(session) -> None:
    await seed(session)
    docs = list(await session.scalars(select(SourceDoc)))
    codes = {d.short_code for d in docs}
    assert codes == {"CF", "RBC"}
    # Not derived from the title: "Non-Banking ..." would give "NCF" / "NRBC".
    assert all(not d.short_code.startswith("N") for d in docs)


async def test_seed_replaces_a_rule_whose_citation_changed(session) -> None:
    await seed(session)
    kf03 = await session.scalar(
        select(Rule).where(Rule.code == "KF-03", Rule.status == "approved")
    )
    kf03.source_para, kf03.related = "6(1)", []  # as an older seed stored it
    await session.flush()

    report = await seed(session)
    assert report.created == ["KF-03"]
    assert report.corrected == ["KF-03: para 6(1) to 29(3); related none to 29, 6(1)"]
    rows = list(await session.scalars(
        select(Rule).where(Rule.code == "KF-03").order_by(Rule.created_at)
    ))
    old, new = rows
    assert old.status == "retired" and old.review_note.startswith("Citation corrected")
    assert new.status == "approved" and new.source_para == "29(3)"
    assert new.supersedes_rule_id == old.id


def test_header_gives_reference_and_issue_date() -> None:
    from app.rules.seed import CF_FILE, SOURCES

    ref, issued = read_header((SOURCES / CF_FILE).read_bytes())
    assert ref == "RBI/DOR/2025-26/347" and str(issued) == "2025-11-28"
