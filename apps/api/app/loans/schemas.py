import uuid
from typing import Literal

from pydantic import BaseModel, Field

# ₹1 crore: a sanity bound on input, not a rule.
MAX_PAISE = 1_00_00_000_00


class ApplicationIn(BaseModel):
    product: str = Field(min_length=1, max_length=10)
    amount_paise: int = Field(gt=0, le=MAX_PAISE)
    tenor_months: int = Field(gt=0, le=120)
    purpose: str | None = Field(default=None, max_length=300)
    borrower_name: str | None = Field(default=None, max_length=120)
    borrower_id: uuid.UUID | None = None
    household_income_annual_paise: int | None = Field(default=None, ge=0, le=MAX_PAISE)
    existing_monthly_repayments_paise: int | None = Field(default=None, ge=0, le=MAX_PAISE)


class FactsIn(BaseModel):
    household_income_annual_paise: int | None = Field(default=None, ge=0, le=MAX_PAISE)
    existing_monthly_repayments_paise: int | None = Field(default=None, ge=0, le=MAX_PAISE)
    purpose: str | None = Field(default=None, max_length=300)


class RecommendIn(BaseModel):
    recommendation: Literal["approve", "approve_modified", "reject"]
    amount_paise: int | None = Field(default=None, gt=0, le=MAX_PAISE)
    note: str | None = Field(default=None, max_length=2000)


class DecideIn(BaseModel):
    outcome: Literal["approve", "modify", "reject"]
    amount_paise: int | None = Field(default=None, gt=0, le=MAX_PAISE)
    note: str | None = Field(default=None, max_length=2000)
