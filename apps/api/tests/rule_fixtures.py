"""Approved rules as seeded from the two RBI Directions, inserted straight into the test
database so the engine has a rule set. Params match what the seed extracts from the PDFs."""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.rules.models import Rule, SourceDoc

ISSUED = date(2025, 11, 28)
KFS_SCOPE = "all new retail and MSME term loans sanctioned on or after October 1, 2024"

RULES = [
    ("CF", "51", "MF-01", "max_amount", "microfinance", "origination",
     {"subject": "annual household income", "max_paise": 30_000_000,
      "scope": "collateral-free loan"},
     ("A microfinance loan is a collateral-free loan given to a household having annual "
     "household income up to ₹3,00,000.")),
    ("CF", "55", "MF-02", "max_ratio", "microfinance", "origination",
     {"numerator": "monthly loan repayment obligations of the household",
      "denominator": "monthly household income", "max_percent": "50",
      "scope": "microfinance loan"},
     "This shall be subject to a limit of maximum 50 per cent of the monthly household income."),
    ("RBC", "29(2)", "KF-01", "min_days", "all", "origination",
     {"subject": "KFS validity period", "working_days": True,
      "tiers": [{"min_days": 3, "tenor_days_min": 7}, {"min_days": 1, "tenor_days_below": 7}],
      "scope": KFS_SCOPE},
     ("The validity period of the KFS shall be at least three working days for loans having "
     "tenor of seven days or more, and a validity period of one working day for loans having "
     "tenor of less than seven days.")),
    ("RBC", "29(3)", "KF-03", "required_disclosure", "all", "origination",
     {"item": "computation sheet of Annual Percentage Rate (APR)", "scope": KFS_SCOPE},
     "The KFS shall also include a computation sheet of Annual Percentage Rate (APR)."),
    ("RBC", "29(5)", "KF-02", "prohibited_charge", "all", "servicing",
     {"charge": "fees or charges not mentioned in the KFS", "scope": KFS_SCOPE},
     "Any fees, charges, etc. which are not mentioned in the KFS, cannot be charged."),
    ("RBC", "81", "MF-04", "prohibited_charge", "microfinance", "origination",
     {"charge": "pre-payment charge", "scope": "microfinance loans"},
     "There shall be no pre-payment charge on microfinance loans."),
    ("RBC", "81", "MF-06", "prohibited_charge", "microfinance", "servicing",
     {"charge": "delayed payment charge on the entire loan amount",
      "scope": "microfinance loans"},
     "Penalty, if any, for delayed payment shall be applied on the overdue amount only."),
    ("RBC", "91(2)", "MF-05", "time_window", "microfinance", "recovery",
     {"activity": "calling the borrower", "start": "09:00", "end": "18:00"},
     "Calling the borrower before 9:00 a.m. and after 6:00 p.m."),
]


# Fact fields the template engine reads (added by migration 0008; the seed writes them too).
# RULES above keeps the params as they were stored before 0008.
FACT_FIELDS = {
    "MF-01": {"fact": "household_income_annual_paise", "must_be_false": "collateral",
              "decides_scope": True},
    "MF-02": {"numerator_fact": "monthly_repayments_paise",
              "denominator_fact": "household_income_monthly_paise", "offer_on_fail": True},
    "MF-04": {"fact": "prepayment_charge_paise"},
    "KF-01": {"fact": "kfs_validity_working_days"},
    "KF-03": {"fact": "apr_computation_sheet"},
}


async def add_rule_set(session: AsyncSession) -> dict[str, Rule]:
    docs = {}
    for code in ("CF", "RBC"):
        doc = SourceDoc(title=f"Test {code} Directions", short_code=code)
        session.add(doc)
        docs[code] = doc
    await session.flush()
    maker, checker = uuid.uuid4(), uuid.uuid4()
    rules = {}
    for doc, para, code, template, applies, stage, params, text in RULES:
        rule = Rule(
            code=code, title=code, template=template,
            params={**params, **FACT_FIELDS.get(code, {})}, applies_to=applies,
            stage=stage, effective_from=ISSUED, status="approved", source_doc_id=docs[doc].id,
            source_para=para, para_text=text, origin="manual", made_by=maker, checked_by=checker,
        )
        session.add(rule)
        rules[code] = rule
    await session.flush()
    return rules


# The worked example, APP-2026-0142.
REKHA = {
    "product_category": "microfinance",
    "amount_paise": 80_000_00,
    "tenor_months": 24,
    "rate_bps_month": 200,
    "fees": [{"name": "Processing fee", "bps": 100, "payable_to": "lender", "assumed": True}],
    "prepayment_charge_paise": 0,
    "collateral": False,
    "household_income_annual_paise": 2_64_000_00,
    "existing_monthly_repayments_paise": 7_500_00,
    "offer_step_paise": 1_000_00,
}
