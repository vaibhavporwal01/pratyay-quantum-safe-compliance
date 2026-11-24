"""PDF ingest against the docker Postgres, using the real RBI Directions in data/sources."""

import hashlib
import re
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.main import app
from app.rules import ingest as ingest_mod
from app.rules.ingest import FileTooLarge, IngestError, ingest_pdf
from app.rules.models import Paragraph, SourceDoc
from app.rules.service import list_paragraphs

SOURCES = Path(__file__).resolve().parents[3] / "data" / "sources"
CREDIT = SOURCES / "rbi-nbfc-credit-facilities-directions-2025.pdf"
CONDUCT = SOURCES / "rbi-nbfc-responsible-business-conduct-directions-2025.pdf"


def norm(text: str) -> str:
    """Lowercase, drop hyphens and collapse whitespace, since PDF spacing varies."""
    return " ".join(re.sub(r"[-‐-—]", "", text.lower()).split())


def mentions(text: str, *words: str) -> bool:
    t = norm(text)
    return all(norm(w) in t for w in words)


def group_text(paragraphs: list[Paragraph], top: str) -> str:
    """Text of paragraph `top` plus its sub-paragraphs, e.g. 29, 29(1), 29(2)."""
    return " ".join(p.text for p in paragraphs if re.fullmatch(rf"{top}(\(\d+\))?", p.number))


def by_number(paragraphs: list[Paragraph]) -> dict[str, Paragraph]:
    return {p.number: p for p in paragraphs}


async def test_credit_facilities_paragraphs(session: AsyncSession) -> None:
    result = await ingest_pdf(
        session, CREDIT, title="NBFC Credit Facilities Directions", ref_no="RBI/DOR/2025-26/347"
    )
    paras = await list_paragraphs(session, result.doc.id)
    numbered = by_number(paras)

    assert result.report.pages == 54
    assert result.report.paragraphs == len(paras) > 100
    assert mentions(numbered["51"].text, "collateral-free", "household", "annual income",
                    "3,00,000")
    assert mentions(numbered["55"].text, "50 per cent", "monthly household income")
    assert "56" in numbered
    assert numbered["51"].page == 34
    # Every top-level number from 1 to the last one is present.
    tops = {int(re.match(r"\d+", p.number).group()) for p in paras}
    assert tops == set(range(1, max(tops) + 1))


async def test_responsible_business_conduct_paragraphs(session: AsyncSession) -> None:
    result = await ingest_pdf(
        session, CONDUCT, title="NBFC Responsible Business Conduct Directions",
        ref_no="RBI/DOR/2025-26/362",
    )
    paras = await list_paragraphs(session, result.doc.id)
    numbered = by_number(paras)

    # Paragraph 29 refers to the Key Facts Statement by its defined abbreviation, KFS.
    assert mentions(group_text(paras, "29"), "KFS", "borrower")
    assert mentions(numbered["6(6)"].text, "Key Facts Statement (KFS)")
    assert mentions(numbered["81"].text, "prepayment charge", "microfinance")


async def test_report_lists_unmatched_lines(session: AsyncSession) -> None:
    report = (await ingest_pdf(session, CREDIT, title="Credit")).report
    reasons = {u.reason for u in report.unmatched}
    assert {"heading", "small_text", "outside_paragraph"} <= reasons
    assert any("Substituted with effect from" in u.text for u in report.unmatched)  # footnote
    assert all(r.reason == "page_number" for r in report.removed)


async def test_same_file_twice_gives_one_source_doc(session: AsyncSession) -> None:
    first = await ingest_pdf(session, CREDIT, title="Credit")
    second = await ingest_pdf(session, CREDIT.read_bytes(), title="Credit again")

    assert second.doc.id == first.doc.id
    assert second.report.duplicate and not first.report.duplicate
    assert second.report.paragraphs == first.report.paragraphs
    digest = hashlib.sha3_256(CREDIT.read_bytes()).digest()
    docs = await session.scalar(
        select(func.count()).select_from(SourceDoc).where(SourceDoc.sha3_256 == digest)
    )
    paras = await session.scalar(
        select(func.count()).select_from(Paragraph).where(Paragraph.doc_id == first.doc.id)
    )
    assert docs == 1
    assert paras == first.report.paragraphs
    assert first.doc.file == CREDIT.read_bytes()


async def test_rejects_non_pdf(session: AsyncSession) -> None:
    with pytest.raises(IngestError, match="not a PDF"):
        await ingest_pdf(session, b"hello, this is plain text", title="Not a PDF")


async def test_rejects_oversized_file(session: AsyncSession, monkeypatch, tmp_path) -> None:
    with pytest.raises(FileTooLarge):
        await ingest_pdf(session, b"%PDF-" + b"0" * (20 * 1024 * 1024), title="Too big")
    # Paths are checked by size on disk before being read.
    monkeypatch.setattr(ingest_mod, "MAX_PDF_BYTES", 1024)
    big = tmp_path / "big.pdf"
    big.write_bytes(b"%PDF-" + b"0" * 2048)
    with pytest.raises(FileTooLarge):
        await ingest_pdf(session, big, title="Too big")


# ---- API --------------------------------------------------------------------------------


@pytest.fixture
async def client(session: AsyncSession):
    async def _session():
        yield session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_api_upload_and_list_paragraphs(client: AsyncClient) -> None:
    form = {"title": "Responsible Business Conduct", "ref_no": "RBI/DOR/2025-26/362",
            "issued_on": "2025-11-28"}
    files = {"file": (CONDUCT.name, CONDUCT.read_bytes(), "application/pdf")}

    r = await client.post("/api/v1/rules/sources", data=form, files=files)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["sha3_256"] == hashlib.sha3_256(CONDUCT.read_bytes()).hexdigest()
    assert body["duplicate"] is False
    assert body["report"]["pages"] == 36
    assert body["report"]["unmatched"]

    again = await client.post("/api/v1/rules/sources", data=form, files=files)
    assert again.status_code == 200
    assert again.json()["doc_id"] == body["doc_id"]

    r = await client.get(f"/api/v1/rules/sources/{body['doc_id']}/paragraphs")
    assert r.status_code == 200
    paras = r.json()
    assert len(paras) == body["report"]["paragraphs"]
    assert paras[0]["number"] == "1"
    assert all(p["label"] is None and p["confidence"] is None for p in paras)


async def test_api_rejects_non_pdf(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/rules/sources",
        data={"title": "Notes"},
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )
    assert r.status_code == 400
    assert "not a PDF" in r.json()["detail"]


async def test_api_unknown_source_is_404(client: AsyncClient) -> None:
    r = await client.get("/api/v1/rules/sources/00000000-0000-0000-0000-000000000000/paragraphs")
    assert r.status_code == 404
