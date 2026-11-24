"""Seed Lender A's users, the two RBI Directions in data/sources, and their approved rules.

    uv run python -m app.rules.seed

Safe to run again: users are keyed on email, documents on their SHA3-256 hash, and rules on
(document, code) while live. Nothing is duplicated.

Every number in a seeded rule is read from the stored paragraph by the extractor; the script
only says which value to take (e.g. "the first percentage"). If the extractor cannot find it,
the value is left out and reported, and the rule stays a draft. The issue date and reference
number come from each PDF's first page. Effective dates are the issue dates, because paragraph 2
of both Directions says they apply from the date of issuance.
"""

import asyncio
import io
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pdfplumber
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.identity import service as identity
from app.identity.deps import User
from app.rules import service
from app.rules.extract import Kind, Missing, find

SOURCES = Path(__file__).resolve().parents[4] / "data" / "sources"
CF_FILE = "rbi-nbfc-credit-facilities-directions-2025.pdf"
RBC_FILE = "rbi-nbfc-responsible-business-conduct-directions-2025.pdf"


@dataclass(frozen=True)
class Pick:
    """Take the nth value of a kind from the rule's own paragraph."""

    kind: Kind
    nth: int = 0


@dataclass
class RuleSpec:
    doc: str
    para: str
    code: str
    title: str
    template: str
    params: dict[str, Any]
    applies_to: str
    related: list[dict[str, str]] = field(default_factory=list)


CF_TITLE = (
    "Reserve Bank of India (Non-Banking Financial Companies – Credit Facilities) Directions, 2025"
)
RBC_TITLE = (
    "Reserve Bank of India (Non-Banking Financial Companies – Responsible Business Conduct) "
    "Directions, 2025"
)
DOCS = {"CF": (CF_FILE, CF_TITLE), "RBC": (RBC_FILE, RBC_TITLE)}

KFS_SCOPE = "all new retail and MSME term loans sanctioned on or after October 1, 2024"
KFS_SCOPE_NOTE = "Scope of paragraph 29: credit card receivables are exempted."

RULES: list[RuleSpec] = [
    RuleSpec(
        "CF", "51", "MF-01", "Microfinance loan: household income up to ₹3,00,000",
        "max_amount",
        {"subject": "annual household income", "max_paise": Pick("amount"),
         "scope": "collateral-free loan"},
        "microfinance",
    ),
    RuleSpec(
        "CF", "55", "MF-02", "Repayments within 50% of monthly household income",
        "max_ratio",
        {"numerator": "monthly loan repayment obligations of the household",
         "denominator": "monthly household income", "max_percent": Pick("percent"),
         "exclude": ["future expected income from the asset/ activity financed"],
         "scope": "microfinance loan"},
        "microfinance",
        related=[
            {"para": "56", "note": "All outstanding loans of the household, collateral-free and "
                                   "collateralised, plus the loan under consideration, count "
                                   "towards the limit, principal and interest."},
            {"para": "57", "note": "Existing loans over the limit may run to maturity, but no "
                                   "new loan until the household is back within the limit."},
        ],
    ),
    RuleSpec(
        "RBC", "6(1)", "KF-03", "APR includes the interest rate and all other charges",
        "required_disclosure",
        {"item": "Annual Percentage Rate (APR)",
         "includes": ["interest rate", "all other charges associated with the credit facility"]},
        "all",
    ),
    RuleSpec(
        "RBC", "29(2)", "KF-01", "KFS valid for at least 3 working days",
        "min_days",
        {"subject": "KFS validity period", "working_days": True,
         "tiers": [
             {"min_days": Pick("days", 0), "tenor_days_min": Pick("days", 1)},
             {"min_days": Pick("days", 2), "tenor_days_below": Pick("days", 3)},
         ],
         "scope": KFS_SCOPE},
        "all",
        related=[{"para": "29", "note": KFS_SCOPE_NOTE}],
    ),
    RuleSpec(
        "RBC", "29(5)", "KF-02", "No charge outside the KFS without explicit consent",
        "prohibited_charge",
        {"charge": "fees or charges not mentioned in the KFS",
         "unless": "explicit consent of the borrower", "scope": KFS_SCOPE},
        "all",
        related=[{"para": "29", "note": KFS_SCOPE_NOTE}],
    ),
    RuleSpec(
        "RBC", "81", "MF-04", "No pre-payment charge on microfinance loans",
        "prohibited_charge",
        {"charge": "pre-payment charge", "scope": "microfinance loans"},
        "microfinance",
    ),
    RuleSpec(
        "RBC", "81", "MF-06", "Delayed payment charge on the overdue amount only",
        "prohibited_charge",
        {"charge": "delayed payment charge on the entire loan amount",
         "unless": "applied on the overdue amount", "scope": "microfinance loans"},
        "microfinance",
    ),
    RuleSpec(
        "RBC", "91(2)", "MF-05", "Recovery calls only between 9:00 a.m. and 6:00 p.m.",
        "time_window",
        {"activity": "calling the borrower", "start": Pick("time", 0), "end": Pick("time", 1)},
        "microfinance",
        related=[{"para": "91", "note": "Section H, Conduct towards Microfinance borrowers: "
                                        "these practices are deemed harsh in recovery."}],
    ),
]

_HEADER_RE = re.compile(r"(RBI/[A-Z]+/\d{4}-\d{2}/\d+)")
_DATE_RE = re.compile(r"DOR\.[^\s]+\s+([A-Z][a-z]+ \d{1,2}, \d{4})")


def read_header(data: bytes) -> tuple[str | None, date | None]:
    """RBI reference and issue date from the first page, or None where not found."""
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        text = pdf.pages[0].extract_text() or ""
    ref = _HEADER_RE.search(text)
    when = _DATE_RE.search(text)
    issued = datetime.strptime(when.group(1), "%B %d, %Y").date() if when else None
    return (ref.group(1) if ref else None, issued)


def resolve(value: Any, text: str, path: str, missing: list[str]) -> Any:
    if isinstance(value, Pick):
        found = find(text, value.kind, value.nth)
        if isinstance(found, Missing):
            missing.append(f"{path}: {found.reason}")
            return None
        return found.value
    if isinstance(value, dict):
        return {k: resolve(v, text, f"{path}.{k}" if path else k, missing)
                for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, text, f"{path}.{i}", missing) for i, v in enumerate(value)]
    return value


@dataclass
class SeedReport:
    users_added: int = 0
    docs: dict[str, str] = field(default_factory=dict)
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    left_out: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


async def seed(session: AsyncSession, sources: Path = SOURCES) -> SeedReport:
    report = SeedReport(users_added=await identity.seed_dev_users(session))
    maker_row = await identity.first_user_with_role(session, "maker")
    checker_row = await identity.first_user_with_role(session, "checker")
    maker = User(maker_row.id, maker_row.org_id, maker_row.role, maker_row.name)
    checker = User(checker_row.id, checker_row.org_id, checker_row.role, checker_row.name)

    doc_ids, issued = {}, {}
    for key, (filename, title) in DOCS.items():
        data = (sources / filename).read_bytes()
        ref_no, issued_on = read_header(data)
        result = await service.ingest_pdf(
            session, data, title=title, ref_no=ref_no, issued_on=issued_on, uploaded_by=maker.id
        )
        doc = result.doc
        # A copy stored before this seed may lack header details: fill only what is empty.
        doc.ref_no = doc.ref_no or ref_no
        doc.issued_on = doc.issued_on or issued_on
        doc.pages = doc.pages or result.report.pages
        doc_ids[key] = doc.id
        issued[key] = doc.issued_on
        state = "already stored" if result.report.duplicate else "stored"
        report.docs[key] = f"{state}, ref {ref_no or 'not found'}, issued {issued_on or 'not found'}"
        if issued[key] is None:
            report.left_out.append(f"{key}: issue date not found on page 1; effective_from left empty")
        if not result.report.duplicate:
            try:
                await service.classify_paragraphs(session, result.doc.id)
            except service.ModelNotFound:
                report.problems.append(f"{key}: classifier model not found; labels left empty")

    for spec in RULES:
        doc_id = doc_ids[spec.doc]
        if await service.find_rule(session, doc_id, spec.code):
            report.skipped.append(spec.code)
            continue
        para = await service.get_paragraph_by_number(session, doc_id, spec.para)
        if para is None:
            report.problems.append(f"{spec.code}: {spec.doc} para {spec.para} not found")
            continue
        missing: list[str] = []
        params = resolve(spec.params, para.text, "", missing)
        report.left_out += [f"{spec.code} ({spec.doc} para {spec.para}) {m}" for m in missing]
        rule = await service.create_draft(session, maker, {
            "code": spec.code, "title": spec.title, "template": spec.template,
            "params": params, "applies_to": spec.applies_to,
            "effective_from": issued[spec.doc], "paragraph_id": para.id,
            "related": spec.related, "origin": "manual",
        })
        if missing:
            report.created.append(f"{spec.code} (draft: values missing)")
            continue
        await service.approve(session, checker, rule.id, "Seeded from the source PDF.")
        report.created.append(spec.code)
    return report


async def main() -> int:
    async with SessionLocal() as session:
        report = await seed(session)
        await session.commit()
    print(f"Users added: {report.users_added}")
    for key, line in report.docs.items():
        print(f"{key}: {line}")
    print(f"Rules created: {', '.join(report.created) or 'none'}")
    print(f"Rules already present: {', '.join(report.skipped) or 'none'}")
    for line in report.left_out:
        print(f"Left out: {line}")
    for line in report.problems:
        print(f"Problem: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
