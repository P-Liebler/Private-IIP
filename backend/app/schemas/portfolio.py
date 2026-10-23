from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Currency = Literal["CHF", "EUR", "USD"]
TransactionType = Literal[
    "BUY",
    "SELL",
    "DIVIDEND",
    "INTEREST",
    "DEPOSIT",
    "WITHDRAWAL",
    "FEE",
    "TAX",
    "TRANSFER_IN",
    "TRANSFER_OUT",
    "SPLIT",
    "CASH_ADJUSTMENT",
    "OPENING_POSITION",
]


class PortfolioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    base_currency: Currency = "CHF"
    benchmark_id: UUID | None = None


class PortfolioUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    benchmark_id: UUID | None = None

    @model_validator(mode="after")
    def validate_nonnull(self) -> PortfolioUpdate:
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Name cannot be null")
        return self


class AccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    account_type: Literal["BROKER", "CASH", "MANUAL"] = "MANUAL"
    default_currency: Currency | None = None


class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    account_type: Literal["BROKER", "CASH", "MANUAL"] | None = None
    default_currency: Currency | None = None

    @model_validator(mode="after")
    def validate_nonnull(self) -> AccountUpdate:
        if any(
            key in self.model_fields_set and getattr(self, key) is None
            for key in ("name", "account_type")
        ):
            raise ValueError("Name and account type cannot be null")
        return self


class TransactionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: UUID
    instrument_id: UUID | None = None
    type: TransactionType
    trade_date: date
    settlement_date: date | None = None
    quantity: Decimal | None = None
    price: Decimal | None = None
    amount: Decimal | None = None
    currency: Currency
    fee: Decimal = Decimal(0)
    tax: Decimal = Decimal(0)
    fx_rate_to_base: Decimal | None = None
    external_id: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_accounting(self) -> TransactionInput:
        for value, precision, scale in (
            (self.quantity, 28, 8),
            (self.price, 24, 8),
            (self.amount, 28, 8),
            (self.fee, 24, 8),
            (self.tax, 24, 8),
            (self.fx_rate_to_base, 28, 12),
        ):
            if value is not None and (
                not value.is_finite()
                or abs(value) >= Decimal(10) ** (precision - scale)
                or value.scaleb(scale) != value.scaleb(scale).to_integral_value()
            ):
                raise ValueError("Unrepresentable decimal")
        if self.fee < 0 or self.tax < 0:
            raise ValueError("Fee and tax must be nonnegative")
        if self.fx_rate_to_base is not None and self.fx_rate_to_base <= 0:
            raise ValueError("FX rate must be positive")
        if self.settlement_date is not None and self.settlement_date < self.trade_date:
            raise ValueError("Settlement cannot precede trade")
        if self.type == "OPENING_POSITION":
            if not self.instrument_id or self.quantity is None or self.quantity <= 0:
                raise ValueError("Opening position needs instrument and positive quantity")
            if self.price is not None or self.fee or self.tax:
                raise ValueError("Opening position is not a trade and has no price, fee or tax")
            if self.amount is not None and self.amount < 0:
                raise ValueError("Known opening cost basis must be nonnegative")
            if not self.notes or len(self.notes.strip()) < 10:
                raise ValueError("Opening position requires statement/source provenance")
        elif self.type in {"BUY", "SELL"}:
            if (
                not self.instrument_id
                or self.quantity is None
                or self.quantity <= 0
                or self.price is None
                or self.price <= 0
            ):
                raise ValueError("Buy/sell needs instrument, positive quantity and price")
            if self.amount is not None:
                raise ValueError("Buy/sell amount is derived from quantity and price")
        elif self.type == "SPLIT":
            if not self.instrument_id or self.quantity is None or self.quantity <= 0:
                raise ValueError("Split needs instrument and positive ratio")
            if self.price is not None or self.amount is not None or self.fee or self.tax:
                raise ValueError("Split has no price, cash, fee or tax")
        else:
            if self.quantity is not None or self.price is not None:
                raise ValueError("Cash event cannot have quantity or price")
            if self.amount is None:
                raise ValueError("Cash amount required")
            if self.type == "DIVIDEND" and not self.instrument_id:
                raise ValueError("Dividend needs instrument")
            if self.type not in {"DIVIDEND", "INTEREST"} and (self.fee or self.tax):
                raise ValueError("Fee and tax fields are only supported on trades and income")
            if self.type not in {"DIVIDEND", "INTEREST"} and self.instrument_id:
                raise ValueError("Cash event cannot reference an instrument")
            if self.type != "CASH_ADJUSTMENT" and self.amount < 0:
                raise ValueError("Cash amount must be nonnegative")
            if (
                self.type in {"DEPOSIT", "WITHDRAWAL", "FEE", "TAX", "TRANSFER_IN", "TRANSFER_OUT"}
                and self.amount <= 0
            ):
                raise ValueError("Cash amount must be positive")
        return self
