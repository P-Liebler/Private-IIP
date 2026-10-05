from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ProviderPayload:
    source_id: UUID
    body: bytes
    content_type: str
    requested_at: datetime
    http_status: int


class MarketDataProvider(Protocol):
    """Future price providers return original bytes for raw persistence before parsing."""

    async def fetch(self, instrument_id: UUID, as_of: datetime) -> ProviderPayload: ...


@dataclass(frozen=True)
class MappingCandidate:
    figi: str
    ticker: str | None
    name: str | None
    exch_code: str | None
    security_type: str | None
    market_sector: str | None


@dataclass(frozen=True)
class MappingResult:
    status: str
    candidates: tuple[MappingCandidate, ...]
    raw_ingestion_id: UUID | None = None


class InstrumentMappingProvider(Protocol):
    async def map_identifier(
        self,
        *,
        kind: str,
        value: str,
        exchange: str | None = None,
    ) -> MappingResult: ...
