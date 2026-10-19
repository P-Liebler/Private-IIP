from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.ml.training import TrainingInput
from app.ml.validation import FoldWindow
from app.schemas.data_operations import CollectionInput
from app.schemas.pit import StrictModel
from app.schemas.recommendations import StrategyBacktestInput


class ValidationStrategyInput(StrategyBacktestInput):
    fx_cost_bps: Decimal = Field(default=Decimal(5), gt=0, le=1000)


class SourcePolicy(StrictModel):
    source_slug: str = Field(max_length=60, pattern=r"^[A-Z0-9_]+$")
    use: Literal[
        "manual_upload",
        "fundamentals",
        "filings",
        "fx_rates",
        "prices",
        "mapping",
        "macro",
        "action_coverage",
        "corporate_actions",
        "news",
        "estimates",
        "universe_membership",
    ]


class ReadinessInput(StrictModel):
    universe_id: UUID
    instrument_ids: list[UUID] = Field(default_factory=list, max_length=5)
    benchmark_id: UUID
    start: date
    end: date
    horizon: Literal[30, 90] = 30
    availability_mode: Literal["STRICT_PIT", "RECONSTRUCTED_HISTORICAL"] = "STRICT_PIT"
    base_currency: Literal["CHF", "USD", "EUR"] = "CHF"
    dataset_id: UUID | None = None
    required_features: list[str] = Field(
        default=["momentum_20d", "volatility_20"], min_length=1, max_length=50
    )
    folds: list[FoldWindow] = Field(default_factory=list, max_length=5)
    source_policy: list[SourcePolicy] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def bounds(self) -> "ReadinessInput":
        if self.end < self.start or (self.end - self.start).days > 5844:
            raise ValueError("Ordered range up to 16 years required")
        if len(set(self.instrument_ids)) != len(self.instrument_ids):
            raise ValueError("Duplicate instruments")
        if any(f.embargo_sessions < self.horizon for f in self.folds):
            raise ValueError("INSUFFICIENT_EMBARGO")
        for previous, following in zip(self.folds, self.folds[1:], strict=False):
            if (
                previous.final_end >= following.test_start
                or previous.validation_start >= following.validation_start
            ):
                raise ValueError("OOS_FOLDS_OVERLAP_OR_UNORDERED")
        return self


class PilotInput(StrictModel):
    readiness: ReadinessInput
    collections: list[CollectionInput] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def small(self) -> "PilotInput":
        if self.readiness.base_currency != "CHF":
            raise ValueError("First real-data pilot uses CHF base currency")
        if not 3 <= len(self.readiness.instrument_ids) <= 5:
            raise ValueError("Pilot requires 3–5 explicit instruments plus benchmark")
        if self.readiness.benchmark_id in self.readiness.instrument_ids:
            raise ValueError("Benchmark must be a separate explicit instrument")
        if (self.readiness.end - self.readiness.start).days > 1826:
            raise ValueError("Pilot collection range limited to five years")
        allowed = set(self.readiness.instrument_ids) | {self.readiness.benchmark_id}
        if any(
            not set(c.instrument_ids) <= allowed
            or c.start < self.readiness.start
            or c.end > self.readiness.end
            for c in self.collections
        ):
            raise ValueError("Collection exceeds pilot scope")
        policies = {(p.source_slug, p.use) for p in self.readiness.source_policy}
        from app.services.backfill_jobs import KINDS

        if any(c.kind not in KINDS or KINDS[c.kind] not in policies for c in self.collections):
            raise ValueError("Collection outside explicit source policy")
        return self


class RawEvidenceInput(StrictModel):
    raw_ids: list[UUID] = Field(min_length=1, max_length=100)
    classification: Literal["REAL_MANUAL", "REAL_PROVIDER", "SYNTHETIC", "UNVERIFIED"]
    provenance_reference: str = Field(min_length=40, max_length=2000)
    rights_reference: str = Field(min_length=40, max_length=2000)


class RegimeRule(StrictModel):
    name: Literal[
        "bull_market",
        "bear_market",
        "high_volatility",
        "low_volatility",
        "rising_rates",
        "falling_rates",
    ]
    feature: str = Field(min_length=1, max_length=100)
    definition: str = Field(min_length=20, max_length=1000)
    comparison: Literal["GT", "LE"]
    threshold: Decimal = Field(allow_inf_nan=False)

    @model_validator(mode="after")
    def provenance_scope(self) -> "RegimeRule":
        prefix = (
            "benchmark."
            if self.name in {"bull_market", "bear_market"}
            else "macro."
            if self.name in {"rising_rates", "falling_rates"}
            else "volatility_"
        )
        if not self.feature.startswith(prefix):
            raise ValueError(
                "Use a pinned benchmark, macro or volatility feature matching the regime"
            )
        return self


class ExperimentInput(StrictModel):
    name: str = Field(min_length=5, max_length=120)
    candidates: list[TrainingInput] = Field(min_length=2, max_length=12)
    rationale: str = Field(min_length=40, max_length=2000)
    source_policy: list[SourcePolicy] = Field(min_length=1, max_length=10)
    regime_definitions: dict[str, str] = Field(default_factory=dict, max_length=6)
    regime_rules: list[RegimeRule] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def horizons(self) -> "ExperimentInput":
        if len({rule.name for rule in self.regime_rules}) != len(self.regime_rules):
            raise ValueError("Duplicate regime names")
        if {c.horizon for c in self.candidates} != {30, 90}:
            raise ValueError("Pre-register both 30 and 90 session horizons")
        for horizon in (30, 90):
            group = [c for c in self.candidates if c.horizon == horizon]
            if not {"classification", "excess_return"} <= {c.target for c in group}:
                raise ValueError(
                    "Both classification and excess-return candidates required per horizon"
                )
            if not {"LOGISTIC", "LINEAR"} <= {c.model_type for c in group}:
                raise ValueError(
                    "Start each horizon with the simple logistic and linear candidates"
                )
            reference = group[0]
            if any(
                c.dataset_id != reference.dataset_id or c.folds != reference.folds for c in group
            ):
                raise ValueError("Same-horizon comparisons require identical dataset and windows")
        identities = [c.model_dump_json() for c in self.candidates]
        if len(set(identities)) != len(identities):
            raise ValueError("Duplicate candidates")
        return self


class ForwardInput(StrictModel):
    classifier_id: UUID
    regressor_id: UUID
    instrument_ids: list[UUID] = Field(min_length=1, max_length=5)
    source_policy: list[SourcePolicy] = Field(min_length=1, max_length=10)
    scheduling_enabled: bool = False

    @model_validator(mode="after")
    def unique_instruments(self) -> "ForwardInput":
        if len(set(self.instrument_ids)) != len(self.instrument_ids):
            raise ValueError("Duplicate forward instruments")
        return self


class ChecklistInput(StrictModel):
    source_slug: str = Field(max_length=60, pattern=r"^[A-Z0-9_]+$")
    items: dict[
        Literal[
            "source_identity",
            "official_terms",
            "data_categories",
            "automated_access",
            "local_storage",
            "historical_retention",
            "derived_analysis",
            "attribution",
            "rate_limits",
            "next_review",
            "credentials",
            "exact_scopes",
        ],
        Annotated[str, Field(max_length=2000)],
    ] = Field(max_length=12)
