from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

MONEY_METRICS = frozenset(
    {
        "revenue",
        "gross_profit",
        "operating_income",
        "net_income",
        "cash",
        "total_assets",
        "total_liabilities",
        "total_equity",
        "total_debt",
        "operating_cash_flow",
        "capex",
        "free_cash_flow",
        "current_assets",
        "current_liabilities",
        "inventory",
        "ebitda",
        "income_tax",
        "pretax_income",
        "preferred_equity",
        "minority_interest",
    }
)
INSTANT_METRICS = frozenset(
    {
        "cash",
        "total_assets",
        "total_liabilities",
        "total_equity",
        "total_debt",
        "current_assets",
        "current_liabilities",
        "inventory",
        "shares_outstanding",
        "preferred_equity",
        "minority_interest",
    }
)
METRICS = MONEY_METRICS | {"eps_basic", "eps_diluted", "shares_outstanding"}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FactInput(StrictModel):
    instrument_id: UUID
    metric: str
    value: Decimal = Field(max_digits=38, decimal_places=12, allow_inf_nan=False)
    unit: Literal["MONEY", "PER_SHARE", "SHARES"]
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    period_start: date | None = None
    period_end: date
    period_type: Literal["ANNUAL", "QUARTER", "YTD", "INSTANT"]
    fiscal_year: int | None = Field(default=None, ge=1900, le=2200)
    fiscal_quarter: int | None = Field(default=None, ge=1, le=4)
    filing_reference: str = Field(min_length=1, max_length=100)
    known_at: AwareDatetime | None = None
    availability_evidence: str | None = Field(default=None, max_length=2000)
    share_class: str | None = Field(default=None, max_length=100)
    split_basis_date: date | None = None
    consolidated: bool = True

    @model_validator(mode="after")
    def validate_contract(self) -> FactInput:
        if self.metric not in METRICS:
            raise ValueError("Unknown normalized metric")
        expected = (
            "SHARES"
            if self.metric == "shares_outstanding"
            else "PER_SHARE"
            if self.metric.startswith("eps_")
            else "MONEY"
        )
        if self.unit != expected or (self.currency is None) != (expected == "SHARES"):
            raise ValueError("Metric unit or currency mismatch")
        if not self.consolidated:
            raise ValueError("Nonconsolidated values require a separate mapping contract")
        if self.metric in INSTANT_METRICS:
            if self.period_type != "INSTANT" or self.period_start is not None:
                raise ValueError("Balance sheet/share count must be instant")
        else:
            if self.period_start is None or self.period_start > self.period_end:
                raise ValueError("Duration facts require an ordered start/end")
            days = (self.period_end - self.period_start).days + 1
            if (
                self.period_type == "INSTANT"
                or (self.period_type == "ANNUAL" and not 330 <= days <= 400)
                or (self.period_type == "QUARTER" and not 60 <= days <= 110)
                or (self.period_type == "YTD" and not 111 <= days <= 329)
            ):
                raise ValueError("Period type does not match duration")
        if self.known_at is not None and not self.availability_evidence:
            raise ValueError("Historical availability needs release evidence")
        if self.known_at is not None and self.known_at.date() < self.period_end:
            raise ValueError("Release precedes period end")
        return self


class ImportCommit(StrictModel):
    raw_ingestion_id: UUID
    mapping: dict[str, str] = Field(default_factory=dict)
    confirm: Literal[True]


class WatchlistInput(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class WatchlistUpdate(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    archived: bool | None = None


class WatchlistItemInput(StrictModel):
    instrument_id: UUID
    notes: str | None = Field(default=None, max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=20)


class EstimateInput(StrictModel):
    instrument_id: UUID
    estimate_type: Literal["EPS", "REVENUE", "PRICE_TARGET", "RECOMMENDATION"]
    target_period: date
    value: Decimal = Field(max_digits=38, decimal_places=12, allow_inf_nan=False)
    unit: Literal["MONEY", "PER_SHARE", "RATING"]
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def units(self) -> EstimateInput:
        expected = {
            "EPS": "PER_SHARE",
            "REVENUE": "MONEY",
            "PRICE_TARGET": "PER_SHARE",
            "RECOMMENDATION": "RATING",
        }[self.estimate_type]
        if self.unit != expected or (self.currency is None) != (expected == "RATING"):
            raise ValueError("Estimate unit mismatch")
        return self
