"""The public worked example: APP-2026-0142 (fictional) run through the engine.

Read only: it takes the fictional application's facts from the loan seed, runs the same
preview path the borrower's live checks use, and saves nothing. The landing page renders every
figure from this, so no number is typed into the page. Cached for five minutes so the public
page cannot drive the engine.
"""

import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.loans import service
from app.loans.products import get_product
from app.loans.seed import APPLICATIONS, IST

REF = "APP-2026-0142"
PRODUCT = "MFL"
TTL_SECONDS = 300

_cache: dict[str, tuple[float, dict[str, Any]]] = {}


async def build(session: AsyncSession) -> dict[str, Any]:
    spec = next(a for a in APPLICATIONS if a.ref == REF)
    product = get_product(PRODUCT)
    on_date = spec.at.astimezone(IST).date()
    data = {
        "product": PRODUCT, "amount_paise": spec.amount, "tenor_months": spec.tenor,
        "household_income_annual_paise": spec.income,
        "existing_monthly_repayments_paise": spec.existing,
    }
    asked = await service.preview(session, None, data, on_date)
    offer = asked.get("offer")
    at_offer = None
    if offer:
        at_offer = await service.preview(
            session, None, {**data, "amount_paise": offer["amount_paise"]}, on_date)
    return {
        "ref": REF,
        "purpose": spec.purpose,
        "on_date": on_date.isoformat(),
        "facts": {**data, "product_name": product["name"],
                  "rate_bps_month": product["rate_bps_month"]},
        "asked": asked,
        "at_offer": at_offer,
    }


async def cached(session: AsyncSession, now: float | None = None) -> dict[str, Any]:
    t = time.monotonic() if now is None else now
    hit = _cache.get(REF)
    if hit and t - hit[0] < TTL_SECONDS:
        return hit[1]
    body = await build(session)
    _cache[REF] = (t, body)
    return body


def clear() -> None:
    _cache.clear()
