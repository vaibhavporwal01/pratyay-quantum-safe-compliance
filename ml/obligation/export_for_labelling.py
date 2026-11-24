"""Export rules.paragraphs to a CSV for hand labelling (obligation classifier, P3).

Usage (from the repo root, with the docker Postgres up and both Directions ingested):

    uv run --project apps/api python ml/obligation/export_for_labelling.py
    uv run --project apps/api python ml/obligation/export_for_labelling.py --out /path/labels.csv

The database URL comes from DATABASE_URL (or .env) via app/core/config.py.

Writes ml/obligation/labels.csv with columns:
    paragraph_id, doc_ref, number, page, text, suggested_label, label, note

- One row per paragraph, sorted by document (ref_no) then paragraph number.
- text is the full paragraph on one line (newlines and runs of whitespace become one space).
- suggested_label is a keyword guess: requirement, definition or information.
- label and note are left empty. A person fills label with one of
  requirement / definition / information, and note with anything worth recording.

Prints the count of each suggested_label per document when done.
"""

import argparse
import asyncio
import csv
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "apps" / "api"))

# The keyword heuristic lives with the classifier so training and inference share it.
from app.rules.obligation_features import (
    LABELS,
    base_number,
    definition_sections,
    one_line,
    suggest_label,
)

COLUMNS = (
    "paragraph_id",
    "doc_ref",
    "number",
    "page",
    "text",
    "suggested_label",
    "label",
    "note",
)
DEFAULT_OUT = HERE / "labels.csv"


def build_rows(doc_ref: str, paragraphs: list) -> list[dict[str, object]]:
    """CSV rows for one document. `paragraphs` must already be in document order."""
    sections = definition_sections([(p.number, p.text) for p in paragraphs])
    rows = []
    for p in paragraphs:
        text = one_line(p.text)
        rows.append(
            {
                "paragraph_id": str(p.id),
                "doc_ref": doc_ref,
                "number": p.number or "",
                "page": "" if p.page is None else p.page,
                "text": text,
                "suggested_label": suggest_label(text, base_number(p.number) in sections),
                "label": "",
                "note": "",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def print_counts(rows: list[dict[str, object]]) -> None:
    per_doc: dict[str, Counter] = {}
    for r in rows:
        per_doc.setdefault(str(r["doc_ref"]), Counter())[str(r["suggested_label"])] += 1
    width = max((len(d) for d in per_doc), default=8)
    print(f"{'doc_ref':<{width}}  " + "  ".join(f"{lab:>11}" for lab in LABELS) + "  total")
    for doc_ref, c in per_doc.items():
        cells = "  ".join(f"{c[lab]:>11}" for lab in LABELS)
        print(f"{doc_ref:<{width}}  {cells}  {sum(c.values()):>5}")


async def export(out: Path) -> list[dict[str, object]]:
    from app.core.db import SessionLocal, engine
    from app.rules.service import list_paragraphs, list_source_docs

    rows: list[dict[str, object]] = []
    try:
        async with SessionLocal() as session:
            for doc in await list_source_docs(session):
                paragraphs = await list_paragraphs(session, doc.id)
                rows.extend(build_rows(doc.ref_no or doc.title, paragraphs))
    finally:
        await engine.dispose()
    write_csv(out, rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="CSV path to write")
    args = parser.parse_args()
    rows = asyncio.run(export(args.out))
    print(f"Wrote {len(rows)} paragraphs to {args.out}")
    print_counts(rows)


if __name__ == "__main__":
    main()
