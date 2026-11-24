"""Tests for the labelling export. Run: uv run --project apps/api pytest ml/obligation -q"""

import csv
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import export_for_labelling as ex


def para(number, text, page=1):
    return SimpleNamespace(id=uuid.uuid4(), number=number, page=page, text=text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("An NBFC shall convey in writing to the borrower.", "requirement"),
        ("An NBFC shall not charge penal interest.", "requirement"),
        ("The LTV ratio must be maintained.", "requirement"),
        ("The ratio shall not exceed 75 per cent.", "requirement"),
        ("Maintain at least 15 per cent.", "requirement"),
        ("The NBFC is required to disclose the APR.", "requirement"),
        ("APR means the annual cost of credit.", "definition"),
        ("EPI mean an equated amount of repayments.", "definition"),
        ("REs shall mean scheduled banks.", "definition"),
        ("Jewellery shall have the same meaning as defined in the Directions.", "definition"),
        ("For the purpose of these Directions, following definitions apply.", "definition"),
        ("Notice by means of letter shall be given.", "requirement"),
        ("Use of violence or other similar means to harm the borrower.", "information"),
        ("Lending against gold and silver collateral", "information"),
    ],
)
def test_suggest_label(text, expected):
    assert ex.suggest_label(text) == expected


def test_definitions_section_marks_children():
    paragraphs = [
        para("6", "In these Directions the terms shall bear the meaning assigned to them below:"),
        para("6(5)", "Key Facts are legally significant facts."),
        para("7", "An NBFC shall have Board approved policies."),
        para("7(1)", "Fair Practices Code"),
    ]
    labels = [r["suggested_label"] for r in ex.build_rows("RBI/X", paragraphs)]
    assert labels == ["definition", "definition", "requirement", "information"]


def test_build_rows_one_line_and_empty_label():
    p = para("4(1)", "An NBFC\nshall   comply\r\nwith this.", page=None)
    (row,) = ex.build_rows("RBI/X", [p])
    assert row["text"] == "An NBFC shall comply with this."
    assert row["label"] == "" and row["note"] == "" and row["page"] == ""
    assert row["paragraph_id"] == str(p.id)


def test_write_csv_round_trip(tmp_path):
    rows = ex.build_rows("RBI/X", [para("1", 'Text with "quotes", commas\nand a newline.')])
    out = tmp_path / "labels.csv"
    ex.write_csv(out, rows)
    with out.open(newline="", encoding="utf-8") as f:
        read = list(csv.DictReader(f))
    assert list(read[0].keys()) == list(ex.COLUMNS)
    assert read[0]["text"] == 'Text with "quotes", commas and a newline.'
    assert len(out.read_text(encoding="utf-8").splitlines()) == 2


def test_print_counts(capsys):
    rows = ex.build_rows("RBI/A", [para("1", "X shall do Y."), para("2", "Heading")])
    ex.print_counts(rows)
    out = capsys.readouterr().out
    assert "RBI/A" in out and out.splitlines()[1].split()[1:] == ["1", "0", "1", "2"]
