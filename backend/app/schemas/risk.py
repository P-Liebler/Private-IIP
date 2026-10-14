from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from app.schemas.pit import StrictModel


class RiskInput(StrictModel):
    window: Literal[30, 90, 252] = 252
    as_of: AwareDatetime | None = None
    benchmark_id: UUID | None = None


class ScenarioInput(StrictModel):
    risk_snapshot_id: UUID
    scenario_slug: str | None = Field(default=None, max_length=80)
    calculation_type: (
        Literal[
            "DIRECT_POSITION_SHOCK",
            "CURRENCY_TRANSLATION_SHOCK",
            "BETA_BASED_MARKET_SHOCK",
            "RISK_PARAMETER_STRESS",
        ]
        | None
    ) = None
    shock: Decimal | None = Field(default=None, ge=-1, le=1, allow_inf_nan=False)
    instrument_ids: list[UUID] = Field(default_factory=list, max_length=30)
    currency: Literal["CHF", "EUR", "USD"] | None = None
    volatility_multiplier: Decimal = Field(default=Decimal(2), ge=1, le=5, allow_inf_nan=False)
    benchmark_id: UUID | None = None
    benchmark_mapping_confirmed: bool = False

    @model_validator(mode="after")
    def selected(self) -> "ScenarioInput":
        if (self.scenario_slug is None) == (self.calculation_type is None):
            raise ValueError("Select a versioned scenario or a custom calculation type")
        return self


class HypotheticalTrade(StrictModel):
    instrument_id: UUID
    side: Literal["BUY", "SELL"]
    amount_base: Decimal | None = Field(
        default=None, gt=0, le=Decimal("1000000000"), allow_inf_nan=False
    )
    sell_fraction: Decimal | None = Field(default=None, gt=0, le=1, allow_inf_nan=False)
    cash_currency: Literal["CHF", "EUR", "USD"] | None = None

    @model_validator(mode="after")
    def amount(self) -> "HypotheticalTrade":
        if self.side == "BUY" and (self.amount_base is None or self.sell_fraction is not None):
            raise ValueError("Buy requires amount_base")
        if self.side == "SELL" and (self.sell_fraction is None or self.amount_base is not None):
            raise ValueError("Sell requires sell_fraction")
        return self


class WhatIfInput(StrictModel):
    risk_snapshot_id: UUID
    trades: list[HypotheticalTrade] = Field(min_length=1, max_length=20)
    commission_base: Decimal = Field(default=Decimal(1), ge=0, le=1000, allow_inf_nan=False)
    spread_bps: Decimal = Field(default=Decimal(5), ge=0, le=1000, allow_inf_nan=False)
    slippage_bps: Decimal = Field(default=Decimal(5), ge=0, le=1000, allow_inf_nan=False)
    zero_cost_comparison: bool = False
    scenario_benchmark_mappings: dict[Literal["SP500", "NASDAQ"], UUID] = Field(
        default_factory=dict, max_length=2
    )

    @model_validator(mode="after")
    def costs(self) -> "WhatIfInput":
        if (
            self.commission_base == self.spread_bps == self.slippage_bps == 0
            and not self.zero_cost_comparison
        ):
            raise ValueError("Zero costs require an explicit comparison")
        return self
