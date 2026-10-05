from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import Instrument, InstrumentIdentifier
from app.services.instruments import SearchHit


class InstrumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=300)
    asset_type: Literal["STOCK", "ETF"]
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    ticker: str | None = Field(default=None, max_length=40)
    isin: str | None = Field(default=None, max_length=20)
    figi: str | None = Field(default=None, max_length=20)
    exchange: str | None = Field(default=None, max_length=40)
    mic: str | None = Field(default=None, pattern=r"^[A-Z0-9]{4}$")
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    listed_at: date | None = None


class InstrumentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=300)
    active: bool | None = None
    delisted_at: date | None = None
    sector: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=100)


class IdentifierResponse(BaseModel):
    id: UUID
    type: str
    value: str
    market_key: str
    valid_from: date
    valid_to: date | None
    source_id: UUID | None
    raw_ingestion_id: UUID | None
    observed_at: datetime

    @classmethod
    def from_record(cls, item: InstrumentIdentifier) -> IdentifierResponse:
        return cls(
            id=item.id,
            type=item.type,
            value=item.value,
            market_key=item.market_key,
            valid_from=item.valid_from,
            valid_to=item.valid_to,
            source_id=item.source_id,
            raw_ingestion_id=item.raw_ingestion_id,
            observed_at=item.observed_at,
        )


class InstrumentResponse(BaseModel):
    id: UUID
    name: str
    asset_type: str
    currency: str
    ticker: str | None
    isin: str | None
    figi: str | None
    exchange: str | None
    mic: str | None
    country: str | None
    sector: str | None
    industry: str | None
    listed_at: date | None
    delisted_at: date | None
    active: bool

    @classmethod
    def from_record(cls, item: Instrument) -> InstrumentResponse:
        return cls(
            id=item.id,
            name=item.name,
            asset_type=item.asset_type,
            currency=item.currency,
            ticker=item.ticker,
            isin=item.isin,
            figi=item.figi,
            exchange=item.exchange,
            mic=item.mic,
            country=item.country,
            sector=item.sector,
            industry=item.industry,
            listed_at=item.listed_at,
            delisted_at=item.delisted_at,
            active=item.active,
        )


class InstrumentDetailResponse(InstrumentResponse):
    identifiers: list[IdentifierResponse]


class InstrumentSearchResult(BaseModel):
    instrument: InstrumentResponse
    match_type: str
    resolution_status: str
    matched_value: str
    current: bool

    @classmethod
    def from_hit(cls, hit: SearchHit) -> InstrumentSearchResult:
        return cls(
            instrument=InstrumentResponse.from_record(hit.instrument),
            match_type=hit.match_type,
            resolution_status=hit.resolution_status,
            matched_value=hit.matched_value,
            current=hit.current,
        )


class IdentifierUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["TICKER", "ISIN", "FIGI"]
    value: str = Field(min_length=1, max_length=40)
    valid_from: date
