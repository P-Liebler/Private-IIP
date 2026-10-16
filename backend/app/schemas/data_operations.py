from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from app.schemas.pit import StrictModel


class CollectionInput(StrictModel):
    source_slug: str = Field(max_length=60, pattern=r"^[A-Z0-9_]+$")
    kind: Literal[
        "ECB_FX", "SNB_MACRO", "SEC", "OPENFIGI", "MANUAL_PRICES", "COVERAGE", "ALPHA_PRICES"
    ]
    start: date
    end: date
    instrument_ids: list[UUID] = Field(default_factory=list, max_length=30)
    series: Literal["SNB_rate", "EUR_CHF", "USD_CHF"] = "SNB_rate"
    cik: str | None = Field(default=None, pattern=r"^\d{1,10}$")
    raw_ingestion_id: UUID | None = None
    mapping: dict[str, str] = Field(default_factory=dict, max_length=20)
    include_unlisted: bool = False

    @model_validator(mode="after")
    def bounds(self) -> CollectionInput:
        if self.end < self.start or (self.end - self.start).days > 1826:
            raise ValueError("Ordered range of at most five years required")
        if len(self.instrument_ids) != len(set(self.instrument_ids)):
            raise ValueError("Duplicate instruments")
        if self.kind in {"SEC", "OPENFIGI", "ALPHA_PRICES"} and len(self.instrument_ids) != 1:
            raise ValueError("Exactly one reviewed instrument required")
        if self.kind == "SEC" and not self.cik:
            raise ValueError("Explicit CIK required")
        if self.kind == "MANUAL_PRICES" and not self.raw_ingestion_id:
            raise ValueError("Previewed owned raw CSV required")
        if self.kind == "COVERAGE" and not self.instrument_ids:
            raise ValueError("Select instruments for the coverage audit")
        return self


class SourceReviewInput(StrictModel):
    status: Literal["APPROVED", "BLOCKED", "UNKNOWN"]
    terms_url: str | None = Field(default=None, max_length=500)
    scope: str = Field(min_length=10, max_length=2000)
    allowed_uses: list[str] = Field(max_length=20)
    decision_note: str = Field(min_length=20, max_length=4000)
    next_review_at: AwareDatetime | None = None
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=300)
