from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, Field, model_validator

from app.schemas.pit import StrictModel

ToolName = Literal[
    "getPortfolio",
    "getHoldings",
    "getInstrument",
    "getFinancials",
    "getForecast",
    "getRisk",
    "getNews",
    "getPredictionHistory",
    "getRecommendation",
    "getDataQuality",
]
FactType = Literal[
    "VERIFIED_FACT", "DERIVED_METRIC", "MODEL_FORECAST", "SCENARIO_ASSUMPTION", "UNAVAILABLE"
]


class ToolInput(StrictModel):
    name: ToolName
    portfolio_id: UUID | None = None
    instrument_id: UUID | None = None
    as_of: AwareDatetime | None = None
    horizon: Literal[30, 90] = 30


class EvidenceFact(StrictModel):
    id: str
    fact_type: FactType
    label: str
    value: Any
    unit: str | None = None
    as_of: datetime
    source_references: list[dict[str, Any]]
    limitation: str | None = None


class ConversationCreate(StrictModel):
    title: str = Field(default="Neue Analyse", min_length=1, max_length=120)


class ChatInput(StrictModel):
    question: str = Field(min_length=1, max_length=2000)
    portfolio_id: UUID | None = None
    instrument_id: UUID | None = None
    as_of: AwareDatetime | None = None
    horizon: Literal[30, 90] = 30


class ModelSelection(StrictModel):
    fact_ids: list[str] = Field(default_factory=list, max_length=12)
    explanation_keys: list[
        Literal["DATA_LIMITS", "FORECAST_GATE", "RISK_DEFINITION", "SOURCE_QUOTE", "READ_ONLY"]
    ] = Field(default_factory=list, max_length=5)


class DocumentRightsInput(StrictModel):
    source_slug: str = Field(min_length=1, max_length=60)
    document_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    storage_allowed: bool
    indexing_allowed: bool
    retention_policy: Literal["INDEFINITE_STORAGE_APPROVED", "METADATA_ONLY"]
    attribution: str = Field(min_length=1, max_length=500)
    evidence: str = Field(min_length=40, max_length=4000)


class DocumentMetadata(StrictModel):
    title: str = Field(min_length=1, max_length=240)
    document_type: Literal[
        "SEC_FILING",
        "ANNUAL_REPORT",
        "EARNINGS_REPORT",
        "COMPANY_RELEASE",
        "USER_RESEARCH",
        "PERMITTED_NEWS",
    ] = "USER_RESEARCH"
    source_slug: str = Field(min_length=1, max_length=60)
    instrument_id: UUID | None = None
    published_at: AwareDatetime | None = None
    rights_review_id: UUID | None = None


class RetrievalInput(StrictModel):
    query: str = Field(min_length=1, max_length=2000)
    instrument_id: UUID | None = None
    document_type: str | None = Field(default=None, max_length=40)
    source_id: UUID | None = None
    published_from: AwareDatetime | None = None
    published_to: AwareDatetime | None = None
    as_of: AwareDatetime | None = None
    limit: int = Field(default=5, ge=1, le=8)


class AlertRuleInput(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    type: Literal[
        "PRICE_THRESHOLD",
        "FORECAST_CHANGED",
        "RISK_INCREASED",
        "CONCENTRATION_INCREASED",
        "EARNINGS_UPCOMING",
        "NEGATIVE_NEWS",
        "FUNDAMENTAL_DETERIORATION",
        "MODEL_CONFIDENCE_CHANGED",
    ]
    portfolio_id: UUID | None = None
    instrument_id: UUID | None = None
    horizon: Literal[30, 90] = 30
    threshold: Decimal = Field(allow_inf_nan=False, ge=-1e9, le=1e9)
    direction: Literal["ABOVE", "BELOW", "ABSOLUTE_CHANGE", "INCREASE", "DECREASE"] = "ABOVE"
    enabled: bool = True
    cooldown_seconds: int = Field(default=86400, ge=60, le=2592000)

    @model_validator(mode="after")
    def semantic_threshold(self) -> "AlertRuleInput":
        if self.threshold < 0:
            raise ValueError("Thresholds use nonnegative explicit units")
        if (
            self.type in {"FORECAST_CHANGED", "MODEL_CONFIDENCE_CHANGED"}
            and self.direction != "ABSOLUTE_CHANGE"
        ):
            raise ValueError("Forecast changes require ABSOLUTE_CHANGE")
        if (
            self.type
            in {
                "FORECAST_CHANGED",
                "MODEL_CONFIDENCE_CHANGED",
                "CONCENTRATION_INCREASED",
                "NEGATIVE_NEWS",
            }
            and self.threshold > 1
        ):
            raise ValueError("This threshold is a fraction in [0,1]")
        if self.type in {"RISK_INCREASED", "CONCENTRATION_INCREASED"} and self.direction not in {
            "ABOVE",
            "INCREASE",
        }:
            raise ValueError("Risk/concentration alerts detect levels or increases")
        if self.type == "EARNINGS_UPCOMING" and (self.direction != "BELOW" or self.threshold > 365):
            raise ValueError("Upcoming earnings use BELOW and a window in days <=365")
        if self.type == "FUNDAMENTAL_DETERIORATION" and (
            self.direction not in {"BELOW", "DECREASE"} or self.threshold > 100
        ):
            raise ValueError("Fundamentals use a score threshold or decrease in points")
        return self


class BriefConfigInput(StrictModel):
    enabled: bool = False
    local_time: str = Field(default="07:00", pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str = Field(default="Europe/Zurich", max_length=64)

    @model_validator(mode="after")
    def valid_timezone(self) -> "BriefConfigInput":
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Unknown timezone") from error
        return self


class OptimizerInput(StrictModel):
    risk_snapshot_id: UUID
    objective: Literal[
        "MINIMUM_VARIANCE",
        "RISK_BUDGET",
        "TARGET_ALLOCATION",
        "MINIMUM_CONCENTRATION",
        "EXPECTED_RETURN",
    ] = "MINIMUM_VARIANCE"
    target_weights: dict[UUID, Decimal] = Field(default_factory=dict, max_length=20)
    risk_budgets: dict[UUID, Decimal] = Field(default_factory=dict, max_length=20)
    minimum_position_weight: Decimal = Field(default=Decimal(".01"), gt=0, le=Decimal(".10"))
    scenario_benchmark_mappings: dict[Literal["SP500", "NASDAQ"], UUID] = Field(
        default_factory=dict, max_length=2
    )


class TimeMachineInput(StrictModel):
    as_of: AwareDatetime
    portfolio_id: UUID | None = None
    instrument_id: UUID | None = None
    mode: Literal["STRICT_PIT", "RECONSTRUCTED_HISTORICAL"] = "STRICT_PIT"


class FinancialEventInput(StrictModel):
    instrument_id: UUID
    event_type: Literal["EARNINGS"] = "EARNINGS"
    event_at: AwareDatetime
    announced_at: AwareDatetime | None = None
    status: Literal["SCHEDULED", "CANCELLED"] = "SCHEDULED"
    replaces_id: UUID | None = None
    evidence_note: str = Field(min_length=40, max_length=2000)
