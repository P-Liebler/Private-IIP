from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UniverseInput(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["US_LARGE_CAP", "CH_LARGE_CAP", "USER_WATCHLIST", "CUSTOM_UNIVERSE"] = (
        "CUSTOM_UNIVERSE"
    )


class MembershipInput(StrictModel):
    instrument_id: UUID
    valid_from: date
    valid_to: date | None = None
    known_at: AwareDatetime | None = None
    membership_status: Literal["LISTED", "DELISTED", "REMOVED"] = "LISTED"

    @model_validator(mode="after")
    def ordered(self) -> "MembershipInput":
        if self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("Invalid membership interval")
        return self


class DatasetInput(StrictModel):
    universe_id: UUID
    start: date
    end: date
    benchmark_id: UUID
    availability_mode: Literal["STRICT_PIT", "RECONSTRUCTED_HISTORICAL"] = "STRICT_PIT"
    feature_set_version: Literal["features-v1:raw-explicit-actions"] = (
        "features-v1:raw-explicit-actions"
    )
    target_horizon: Literal[30, 90] = 30
    base_currency: Literal["CHF", "USD", "EUR"] = "CHF"

    @model_validator(mode="after")
    def ordered(self) -> "DatasetInput":
        if self.start > self.end or (self.end - self.start).days > 730:
            raise ValueError("Select ordered range up to two years")
        return self


class BacktestInput(StrictModel):
    dataset_id: UUID
    strategy: Literal["EQUAL_WEIGHT", "BENCHMARK_ONLY", "MOMENTUM", "QUALITY_VALUE"] = (
        "EQUAL_WEIGHT"
    )
    initial_capital: Decimal = Field(
        default=Decimal("10000"), gt=0, le=Decimal("1000000000"), allow_inf_nan=False
    )
    execution_policy: Literal["NEXT_OPEN", "NEXT_CLOSE"] = "NEXT_OPEN"
    commission: Decimal = Field(default=Decimal("1"), ge=0, le=1000, allow_inf_nan=False)
    spread_bps: Decimal = Field(default=Decimal("5"), ge=0, le=1000, allow_inf_nan=False)
    slippage_bps: Decimal = Field(default=Decimal("5"), ge=0, le=1000, allow_inf_nan=False)
    zero_cost_comparison: bool = False
    rebalance_sessions: int = Field(default=20, ge=1, le=252)
    top_n: int = Field(default=10, ge=1, le=100)
    max_position_weight: Decimal = Field(default=Decimal("1"), gt=0, le=1, allow_inf_nan=False)
    risk_free_annual: Decimal | None = Field(default=None, gt=-1, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def explicit_zero(self) -> "BacktestInput":
        if (
            self.commission == self.spread_bps == self.slippage_bps == 0
            and not self.zero_cost_comparison
        ):
            raise ValueError("Zero costs require explicit comparison flag")
        return self
