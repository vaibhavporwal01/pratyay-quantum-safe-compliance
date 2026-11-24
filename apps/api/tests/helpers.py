"""Shared test helpers: users and paragraphs on the rolled-back test session."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.deps import User
from app.rules.models import Paragraph, SourceDoc

ORG = uuid.uuid4()


def user(role: str, name: str | None = None) -> User:
    return User(uuid.uuid4(), ORG, role, name or role.title())


async def add_paragraphs(session: AsyncSession, paras: dict[str, str]) -> dict[str, Paragraph]:
    """A source document holding the given paragraphs (number -> text)."""
    doc = SourceDoc(title="Test Directions", short_code="CF", ref_no="RBI/TEST/1")
    session.add(doc)
    await session.flush()
    rows = {n: Paragraph(doc_id=doc.id, number=n, page=1, text=t) for n, t in paras.items()}
    session.add_all(rows.values())
    await session.flush()
    return rows


# Real text from the RBI Directions in data/sources (checked by test_extract).
CF_55 = (
    "The NBFC shall have a board-approved policy regarding the limit on the outflows on "
    "account of repayment of monthly loan obligations of a household as a percentage of the "
    "monthly household income. This shall be subject to a limit of maximum 50 per cent of the "
    "monthly household income. Explanation: Any future expected income from the asset/ "
    "activity financed by a microfinance loan shall not be included in the household income "
    "for the purpose of calculating the indebtedness of the household."
)
CF_56 = (
    "The computation of loan repayment obligations shall take into account all outstanding "
    "loans (collateral-free microfinance loans as well as any other type of collateralized "
    "loans) of the household."
)

RATIO_RULE = {
    "code": "MF-02",
    "title": "Repayments within 50% of household income",
    "template": "max_ratio",
    "params": {
        "numerator": "monthly loan repayments",
        "denominator": "monthly household income",
        "max_percent": "50",
        "scope": "microfinance loan",
    },
    "applies_to": "microfinance",
}
