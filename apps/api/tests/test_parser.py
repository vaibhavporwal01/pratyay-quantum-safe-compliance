"""Paragraph parser on small synthetic pages (no PDF, no database)."""

from app.rules.parser import Line, parse_pages
from app.rules.service import paragraph_sort_key


def page(no: int, *texts: str, size: float = 12.0) -> list[Line]:
    return [Line(t, no, size) for t in texts]


def numbers(result) -> list[str]:
    return [p.number for p in result.paragraphs]


def test_top_level_and_sub_paragraphs() -> None:
    r = parse_pages([page(1, "1. First paragraph.", "2.", "(1) Sub one.", "(2) Sub two.")])
    assert numbers(r) == ["1", "2(1)", "2(2)"]  # "2." alone has no text of its own


def test_lettered_and_roman_items_stay_in_parent() -> None:
    r = parse_pages([page(1, "1. Applies to:", "(a) lenders;", "(i) banks;", "(ii) NBFCs.")])
    assert numbers(r) == ["1"]
    assert r.paragraphs[0].text == "Applies to: (a) lenders; (i) banks; (ii) NBFCs."


def test_paragraph_continues_across_page_break_and_keeps_start_page() -> None:
    r = parse_pages([
        page(1, "1. Starts here and", "continues", "1"),
        page(2, "onto the next page.", "2. Next.", "2"),
    ])
    assert numbers(r) == ["1", "2"]
    assert r.paragraphs[0].page == 1
    assert r.paragraphs[0].text == "Starts here and continues onto the next page."
    assert {x.reason for x in r.removed} == {"page_number"}


def test_wrapped_year_is_not_a_paragraph_number() -> None:
    r = parse_pages([page(1, "1. Registered under the RBI Act,", "1934.", "2. Next.")])
    assert numbers(r) == ["1", "2"]
    assert r.paragraphs[0].text.endswith("RBI Act, 1934.")


def test_out_of_sequence_number_is_continuation() -> None:
    r = parse_pages([page(1, "1. One.", "2. Two.", "40. not a paragraph", "3. Three.")])
    assert numbers(r) == ["1", "2", "3"]


def test_inserted_paragraph_with_letter_suffix() -> None:
    r = parse_pages([page(1, "1. One.", "2. Two.", "2A. Inserted.", "3. Three.")])
    assert numbers(r) == ["1", "2", "2A", "3"]


def test_footnotes_and_headings_are_reported_not_merged() -> None:
    r = parse_pages([
        page(1, "Chapter I - Preliminary", "A. Short Title", "1. Body text", "of paragraph one.")
        + page(1, "1 Substituted with effect from July 1, 2026.", size=8.0)
        + page(1, "1"),
        page(2, "continues here.", "B. Applicability", "Stray note line", "2. Two."),
    ])
    assert r.paragraphs[0].text == "Body text of paragraph one. continues here."
    reasons = {(u.text, u.reason) for u in r.unmatched}
    assert ("1 Substituted with effect from July 1, 2026.", "small_text") in reasons
    assert ("Chapter I - Preliminary", "heading") in reasons
    assert ("B. Applicability", "heading") in reasons
    assert ("Stray note line", "outside_paragraph") in reasons


def test_repeated_header_is_stripped() -> None:
    pages = [page(n, "RBI Directions 2025", f"{n}. Paragraph {n}.", str(n)) for n in range(1, 6)]
    r = parse_pages(pages)
    assert numbers(r) == ["1", "2", "3", "4", "5"]
    assert sum(x.reason == "repeated_header" for x in r.removed) == 5


def test_hyphenated_line_break_is_joined() -> None:
    r = parse_pages([page(1, "1. No pre-", "payment charge.")])
    assert r.paragraphs[0].text == "No pre-payment charge."


def test_paragraph_sort_key_document_order() -> None:
    nums = ["105A", "29(2)", "105", "29", "3", "29(1)", "105(1)"]
    assert sorted(nums, key=paragraph_sort_key) == [
        "3", "29", "29(1)", "29(2)", "105", "105(1)", "105A",
    ]
