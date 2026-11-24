"""PDF ingest: store a source document and its numbered paragraphs.

CLI:
    uv run python -m app.rules.ingest data/sources/<file>.pdf --title "..." --ref "..."
"""

import argparse
import asyncio
import hashlib
import io
import json
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import pdfplumber
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rules.models import Paragraph, SourceDoc
from app.rules.parser import Line, ParseResult, SkippedLine, parse_pages

MAX_PDF_BYTES = 20 * 1024 * 1024
PDF_MAGIC = b"%PDF-"


class IngestError(ValueError):
    """The upload is not acceptable (not a PDF, too large, unreadable)."""


class FileTooLarge(IngestError):
    pass


@dataclass
class IngestReport:
    doc_id: uuid.UUID
    sha3_256: str
    duplicate: bool
    pages: int
    paragraphs: int
    unmatched: list[SkippedLine] = field(default_factory=list)
    removed: list[SkippedLine] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "doc_id": str(self.doc_id),
            "sha3_256": self.sha3_256,
            "duplicate": self.duplicate,
            "pages": self.pages,
            "paragraphs": self.paragraphs,
            "unmatched": len(self.unmatched),
            "unmatched_by_reason": dict(Counter(u.reason for u in self.unmatched)),
            "removed": len(self.removed),
            "removed_by_reason": dict(Counter(r.reason for r in self.removed)),
        }


@dataclass
class IngestResult:
    doc: SourceDoc
    report: IngestReport


def read_source(source: str | Path | bytes) -> bytes:
    if isinstance(source, bytes):
        data = source
    else:
        path = Path(source)
        if path.stat().st_size > MAX_PDF_BYTES:
            raise FileTooLarge(f"File is larger than {MAX_PDF_BYTES // (1024 * 1024)} MB")
        data = path.read_bytes()
    validate_pdf(data)
    return data


def validate_pdf(data: bytes) -> None:
    if len(data) > MAX_PDF_BYTES:
        raise FileTooLarge(f"File is larger than {MAX_PDF_BYTES // (1024 * 1024)} MB")
    if not data.startswith(PDF_MAGIC):
        raise IngestError("File is not a PDF (missing %PDF- header)")


def extract_lines(data: bytes) -> list[list[Line]]:
    """Text lines per page, with page number and the line's dominant font size."""
    pages: list[list[Line]] = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                lines = []
                for raw in page.extract_text_lines():
                    sizes = Counter(round(c["size"], 1) for c in raw.get("chars", []))
                    size = sizes.most_common(1)[0][0] if sizes else 0.0
                    lines.append(Line(raw["text"], page_no, size))
                pages.append(lines)
    except Exception as exc:  # pdfminer raises many types for damaged files
        raise IngestError(f"Could not read PDF: {exc}") from exc
    return pages


def parse_pdf(data: bytes) -> ParseResult:
    return parse_pages(extract_lines(data))


async def ingest_pdf(
    session: AsyncSession,
    source: str | Path | bytes,
    title: str,
    ref_no: str | None = None,
    issued_on: date | None = None,
    url: str | None = None,
    uploaded_by: uuid.UUID | None = None,
) -> IngestResult:
    """Store the PDF and its paragraphs. Flushes but does not commit: the caller owns the
    transaction. A file already stored (same SHA3-256) is returned as is, with no new rows."""
    data = read_source(source)
    digest = hashlib.sha3_256(data).digest()
    parsed = parse_pdf(data)

    existing = await session.scalar(select(SourceDoc).where(SourceDoc.sha3_256 == digest))
    if existing is not None:
        stored = await session.scalar(
            select(func.count(Paragraph.id)).where(Paragraph.doc_id == existing.id)
        )
        report = IngestReport(
            existing.id, digest.hex(), True, parsed.pages, stored or 0,
            parsed.unmatched, parsed.removed,
        )
        return IngestResult(existing, report)

    doc = SourceDoc(
        title=title,
        ref_no=ref_no,
        issued_on=issued_on,
        url=url,
        file=data,
        sha3_256=digest,
        uploaded_by=uploaded_by,
    )
    session.add(doc)
    await session.flush()
    session.add_all(
        Paragraph(doc_id=doc.id, number=p.number, page=p.page, text=p.text)
        for p in parsed.paragraphs
    )
    await session.flush()
    report = IngestReport(
        doc.id, digest.hex(), False, parsed.pages, len(parsed.paragraphs),
        parsed.unmatched, parsed.removed,
    )
    return IngestResult(doc, report)


# ---- CLI --------------------------------------------------------------------------------


async def _cli_ingest(args: argparse.Namespace) -> IngestReport:
    from app.core.db import SessionLocal, engine

    try:
        async with SessionLocal() as session:
            result = await ingest_pdf(
                session, args.path, title=args.title, ref_no=args.ref,
                issued_on=args.issued_on, url=args.url,
            )
            await session.commit()
            return result.report
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest an RBI Directions PDF.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--ref", default=None, help="Reference number, e.g. RBI/DOR/2025-26/347")
    parser.add_argument("--issued-on", type=date.fromisoformat, default=None)
    parser.add_argument("--url", default=None)
    parser.add_argument(
        "--dry-run", action="store_true", help="Parse and print the report without saving"
    )
    parser.add_argument(
        "--show-unmatched", action="store_true", help="Also print every unmatched line"
    )
    args = parser.parse_args(argv)

    if args.dry_run:
        data = read_source(args.path)
        parsed = parse_pdf(data)
        summary = {
            "sha3_256": hashlib.sha3_256(data).hexdigest(),
            "pages": parsed.pages,
            "paragraphs": len(parsed.paragraphs),
            "unmatched": len(parsed.unmatched),
            "unmatched_by_reason": dict(Counter(u.reason for u in parsed.unmatched)),
            "removed": len(parsed.removed),
        }
        unmatched = parsed.unmatched
    else:
        report = asyncio.run(_cli_ingest(args))
        summary, unmatched = report.summary(), report.unmatched

    print(json.dumps(summary, indent=2))
    if args.show_unmatched:
        for u in unmatched:
            print(json.dumps(asdict(u), ensure_ascii=False))


if __name__ == "__main__":
    main()
