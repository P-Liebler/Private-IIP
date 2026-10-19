from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.pit import StrictModel


class InvestmentPreferences(StrictModel):
    confirmed: bool = False
    base_currency: Literal["CHF", "EUR", "USD"] = "CHF"
    investment_horizon: Literal[30, 90] = 90
    risk_tolerance: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    max_single_position_weight: Decimal = Field(default=Decimal(".15"), gt=0, le=1)
    max_sector_weight: Decimal = Field(default=Decimal(".30"), gt=0, le=1)
    max_country_weight: Decimal = Field(default=Decimal(".60"), gt=0, le=1)
    max_currency_exposure: Decimal = Field(default=Decimal(".60"), gt=0, le=1)
    minimum_liquidity: Decimal = Field(default=Decimal("100000"), gt=0, le=1e12)
    maximum_portfolio_volatility: Decimal = Field(default=Decimal(".20"), gt=0, le=2)
    minimum_cash_reserve: Decimal = Field(default=Decimal(".05"), ge=0, le=1)
    maximum_new_investment: Decimal = Field(default=Decimal("1000"), gt=0, le=1e9)
    maximum_turnover: Decimal = Field(default=Decimal(".10"), gt=0, le=1)
    commission_base: Decimal = Field(default=Decimal(1), ge=0, le=1000)
    spread_bps: Decimal = Field(default=Decimal(5), gt=0, le=1000)
    slippage_bps: Decimal = Field(default=Decimal(5), gt=0, le=1000)
    excluded_instruments: list[UUID] = Field(default_factory=list, max_length=100)
    excluded_sectors: list[str] = Field(default_factory=list, max_length=30)
    preferred_universe: UUID | None = None


class ProfileUpdate(StrictModel):
    expected_version_id: UUID | None = None
    preferences: InvestmentPreferences


class RecommendationInput(StrictModel):
    portfolio_id: UUID
    risk_snapshot_id: UUID
    instrument_ids: list[UUID] = Field(default_factory=list, max_length=20)
    watchlist_id: UUID | None = None
    universe_id: UUID | None = None
    amount_mode: Literal["FIXED", "NAV_FRACTION", "TARGET_WEIGHT"] = "FIXED"
    side: Literal["BUY", "SELL"] = "BUY"
    amount: Decimal = Field(default=Decimal(100), gt=0, le=1e9, allow_inf_nan=False)
    scenario_benchmark_mappings: dict[Literal["SP500", "NASDAQ"], UUID] = Field(
        default_factory=dict, max_length=2
    )

    @model_validator(mode="after")
    def fractional(self) -> "RecommendationInput":
        if self.amount_mode != "FIXED" and self.amount > 1:
            raise ValueError("Fraction and target weight must be <= 1")
        return self


class StrategyBacktestInput(StrictModel):
    dataset_id: UUID
    portfolio_id: UUID
    recommendation_ids: list[UUID] = Field(min_length=1, max_length=1000)
    initial_capital: Decimal = Field(default=Decimal(10000), gt=0, le=1e9)
    commission_base: Decimal = Field(default=Decimal(1), ge=0, le=1000)
    spread_bps: Decimal = Field(default=Decimal(5), gt=0, le=1000)
    slippage_bps: Decimal = Field(default=Decimal(5), gt=0, le=1000)
    fx_cost_bps: Decimal = Field(default=Decimal(0), ge=0, le=1000)


class StrategyReviewInput(StrictModel):
    backtest_id: UUID
    status: Literal["SHADOW", "PRODUCTION", "RETIRED"]
    rationale: str = Field(min_length=40, max_length=4000)
