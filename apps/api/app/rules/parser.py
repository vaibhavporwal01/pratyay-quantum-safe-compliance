"""Paragraph parser for RBI Directions.

Pure functions, no I/O: input is a list of pages of text lines (with font size), output is the
numbered paragraphs plus every line that was not placed in a paragraph, so nothing is dropped
silently.

Numbering handled:
- top-level paragraphs "1.", "2.", "51." (accepted only if they follow the previous number,
  which rejects wrapped lines such as "1934." at the start of a line), and inserted ones
  like "105A."
- sub-paragraphs "(1)", "(2)" under the current top-level paragraph, stored as "55(1)"
- lettered and roman items "(a)", "(i)" stay inside their parent paragraph
A paragraph continuing across a page break stays one paragraph and keeps its starting page.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

# How far ahead of the previous number a new number may jump (tolerates a skipped number).
MAX_TOP_GAP = 3
MAX_SUB_GAP = 2
# A line is "small text" (footnote) if its font is this many points below the body font.
SMALL_FONT_DELTA = 1.5
# A header/footer must repeat on at least this share of pages (and at least 3 pages).
REPEAT_SHARE = 0.5
EDGE_LINES = 2  # header/footer candidates: this many lines at the top and bottom of a page

# Optional amendment marker "2[" before the number; optional letter suffix for inserted
# paragraphs ("105A.").
TOP_RE = re.compile(r"^(?:\d{1,2}\[)?(\d{1,3})([A-Z]{0,2})\.(?!\d)\s*(.*)$")
SUB_RE = re.compile(r"^\((\d{1,2})\)\s*(.*)$")
PAGE_NO_RE = re.compile(r"^(?:page\s+)?\d{1,4}(?:\s+of\s+\d{1,4})?$", re.IGNORECASE)
# Chapter / annex titles, and section headings like "A. Applicability". Case-sensitive, so
# roman items ("i. Number of members") and table cells ("schedule to") are not headings.
HEADING_RE = re.compile(
    r"^(?:Chapter\s+[IVXLC]+\b|Annex(?:ure)?\b|Appendix\b|Schedule\s+[IVXLC\d]|[A-Z]\.\s+[A-Z])"
)
HEADING_MAX_LEN = 100


@dataclass(frozen=True)
class Line:
    text: str
    page: int
    size: float = 0.0


@dataclass
class Paragraph:
    number: str
    page: int
    text: str


@dataclass(frozen=True)
class SkippedLine:
    page: int
    text: str
    reason: str  # page_number | repeated_header | small_text | heading | outside_paragraph


@dataclass
class ParseResult:
    pages: int
    paragraphs: list[Paragraph] = field(default_factory=list)
    unmatched: list[SkippedLine] = field(default_factory=list)
    removed: list[SkippedLine] = field(default_factory=list)


def _normalise(text: str) -> str:
    return re.sub(r"\d+", "#", " ".join(text.split())).lower()


def _is_numbered(text: str) -> bool:
    text = text.strip()
    return bool(TOP_RE.match(text) or SUB_RE.match(text))


def strip_page_furniture(pages: list[list[Line]]) -> tuple[list[list[Line]], list[SkippedLine]]:
    """Remove bare page numbers and headers/footers repeated on most pages."""
    removed: list[SkippedLine] = []
    cleaned: list[list[Line]] = []
    for lines in pages:
        lines = [ln for ln in lines if ln.text.strip()]
        # Bare page numbers only at the very top or bottom of a page.
        for idx in (-1, 0):
            if lines and PAGE_NO_RE.match(lines[idx].text.strip()):
                ln = lines.pop(idx)
                removed.append(SkippedLine(ln.page, ln.text, "page_number"))
        cleaned.append(lines)

    counts: Counter[str] = Counter()
    for lines in cleaned:
        edge = {
            _normalise(ln.text)
            for ln in lines[:EDGE_LINES] + lines[-EDGE_LINES:]
            if not _is_numbered(ln.text)  # never strip a line that opens a paragraph
        }
        counts.update(edge)
    threshold = max(3, REPEAT_SHARE * len(cleaned))
    repeated = {key for key, n in counts.items() if n >= threshold}

    result: list[list[Line]] = []
    for lines in cleaned:
        keep = []
        last = len(lines) - 1
        for i, ln in enumerate(lines):
            at_edge = i < EDGE_LINES or i > last - EDGE_LINES
            if at_edge and _normalise(ln.text) in repeated:
                removed.append(SkippedLine(ln.page, ln.text, "repeated_header"))
            else:
                keep.append(ln)
        result.append(keep)
    return result, removed


def body_font_size(pages: list[list[Line]]) -> float:
    sizes: Counter[float] = Counter()
    for lines in pages:
        for ln in lines:
            if ln.size:
                sizes[ln.size] += len(ln.text)
    return sizes.most_common(1)[0][0] if sizes else 0.0


def _join(parts: list[str]) -> str:
    out = ""
    for part in parts:
        part = " ".join(part.split())
        if not part:
            continue
        if not out:
            out = part
        elif out.endswith("-") and not out.endswith(" -"):
            out += part  # word broken across lines: "pre-" + "payment"
        else:
            out += " " + part
    return out


def parse_pages(pages: list[list[Line]]) -> ParseResult:
    result = ParseResult(pages=len(pages))
    pages, result.removed = strip_page_furniture(pages)
    body = body_font_size(pages)

    top: int | None = None  # last accepted top-level number
    top_label = ""  # its full label, e.g. "100Y" for an inserted paragraph
    sub: int | None = None  # last accepted sub-number under `top`
    open_number: str | None = None  # paragraph currently collecting lines
    open_page = 0
    buffer: list[str] = []

    def close() -> None:
        nonlocal open_number, buffer
        if open_number is not None:
            text = _join(buffer)
            if text:  # "3." alone on a line followed by "(1)" has no text of its own
                result.paragraphs.append(Paragraph(open_number, open_page, text))
        open_number, buffer = None, []

    def start(number: str, page: int, first: str) -> None:
        nonlocal open_number, open_page, buffer
        close()
        open_number, open_page, buffer = number, page, [first]

    for lines in pages:
        for ln in lines:
            text = ln.text.strip()
            if body and ln.size and ln.size < body - SMALL_FONT_DELTA:
                result.unmatched.append(SkippedLine(ln.page, text, "small_text"))
                continue

            m = TOP_RE.match(text)
            if m:
                n, suffix = int(m.group(1)), m.group(2)
                if top is None:
                    expected = n <= 1 + MAX_TOP_GAP and not suffix
                else:
                    expected = (top < n <= top + MAX_TOP_GAP or (bool(suffix) and n == top)
                                or (suffix == "A" and n > top))
                if expected:
                    top, sub, top_label = n, None, f"{n}{suffix}"
                    start(top_label, ln.page, m.group(3))
                    continue

            m = SUB_RE.match(text)
            if m and top is not None and open_number is not None:
                n = int(m.group(1))
                expected = n == 1 if sub is None else sub < n <= sub + MAX_SUB_GAP
                if expected:
                    sub = n
                    start(f"{top_label}({n})", ln.page, m.group(2))
                    continue

            if len(text) <= HEADING_MAX_LEN and HEADING_RE.match(text):
                close()
                result.unmatched.append(SkippedLine(ln.page, text, "heading"))
                continue

            if open_number is not None:
                buffer.append(text)
            else:
                result.unmatched.append(SkippedLine(ln.page, text, "outside_paragraph"))
    close()
    return result