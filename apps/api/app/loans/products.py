"""Lender A's loan products. Product settings, not rules: the rate, the fees and the step a
modified amount is rounded down to are the lender's choices, so they live here, never in a
rule. A fee marked "assumed" is a setting chosen for the seeded data and is labelled as such on
the KFS.
"""

from typing import Any

PRODUCTS: dict[str, dict[str, Any]] = {
    "MFL": {
        "code": "MFL",
        "name": "Microfinance term loan",
        "category": "microfinance",
        "collateral": False,
        "rate_bps_month": 200,
        "tenors": [12, 18, 24],
        "fees": [
            {"name": "Processing fee", "bps": 100, "payable_to": "lender", "assumed": True},
        ],
        "prepayment_charge_paise": 0,
        "offer_step_paise": 1_000_00,
    },
    "SBL": {
        "code": "SBL",
        "name": "Small business term loan (secured)",
        "category": "general",
        "collateral": True,
        "rate_bps_month": 150,
        "tenors": [12, 24, 36],
        "fees": [
            {"name": "Processing fee", "bps": 150, "payable_to": "lender", "assumed": True},
        ],
        "prepayment_charge_paise": 0,
        "offer_step_paise": 1_000_00,
    },
}


def get_product(code: str) -> dict[str, Any] | None:
    return PRODUCTS.get(code)
