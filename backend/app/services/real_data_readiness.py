"""PR1/P6/P7 evidence aggregation, never a replacement for their hard gates."""

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.ml.promotion import PROMOTION_RULES
from app.ml.validation import split_rows
from app.models import (
    DataSource,
    Instrument,
    RawIngestion,
    UniverseMembershipVersion,
    ValidationRecord,
)
from app.schemas.validation import ReadinessInput, SourcePolicy
from app.services.data_coverage import DataCoverageService
from app.services.ml_readiness import P7DataReadinessService
from app.services.pit_datasets import DatasetBuilder
from app.services.pit_evidence import ENTITIES
from app.services.pit_universe import UniverseService
from app.services.sources import SourceGate, SourceService
from app.services.validation_records import ValidationRecords

CHECKLIST_FIELDS = (
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
)


async def source_preconditions(
    db: AsyncSession, policies: list[SourcePolicy]
) -> list[dict[str, Any]]:
    result = []
    for policy in policies:
        source = await SourceService(db).get(policy.source_slug)
        reason = None
        try:
            SourceGate.require_enabled(source, policy.use)
            if source.type != "MANUAL" and not source.rate_limit_per_minute:
                reason = "SOURCE_RATE_UNCONFIGURED"
        except AppError as error:
            reason = error.code
        result.append(
            {
                "source_id": str(source.id),
                "source_slug": source.slug,
                "use": policy.use,
                "approved": source.gate_status == "APPROVED",
                "enabled": source.enabled,
                "gate_reason": reason,
                "terms_url": source.terms_url,
                "checked_at": source.checked_at,
                "next_review_at": source.next_review_at,
                "scope": source.scope,
                "rate_limit_per_minute": source.rate_limit_per_minute,
                "required_credentials": "Personal provider key"
                if source.slug == "ALPHAVANTAGE"
                else "Actual SEC User-Agent/contact"
                if source.slug == "SEC_EDGAR"
                else "None mandated by adapter",
                "operator_checklist": {
                    key: "OPEN_REQUIRES_DOCUMENTED_REVIEW" for key in CHECKLIST_FIELDS
                },
            }
        )
    return result


async def dataset_origins(db: AsyncSession, dataset: Any, user_id: UUID) -> dict[str, Any]:
    raw_ids: set[UUID] = set()
    raw_kinds: dict[UUID, set[str]] = {}
    for kind, identifiers in dataset.manifest.get("versions", {}).items():
        model = ENTITIES.get(kind)
        if not model or not hasattr(model, "raw_ingestion_id") or not identifiers:
            continue
        discovered = (
            await db.scalars(
                select(model.raw_ingestion_id).where(
                    model.id.in_([UUID(i) for i in identifiers]),
                    model.raw_ingestion_id.is_not(None),
                )
            )
        ).all()
        raw_ids.update(discovered)
        for raw_id in discovered:
            raw_kinds.setdefault(raw_id, set()).add(kind)
    records = (
        await db.scalars(
            select(ValidationRecord)
            .where(ValidationRecord.user_id == user_id, ValidationRecord.kind == "RAW_EVIDENCE")
            .order_by(ValidationRecord.created_at.desc(), ValidationRecord.id.desc())
        )
    ).all()
    attestations: dict[str, dict[str, Any]] = {}
    for record in records:
        await ValidationRecords(db, user_id).owned(record.id)
        for evidence in record.result["originals"]:
            attestations.setdefault(
                evidence["raw_id"],
                {
                    **evidence,
                    "classification": record.request["classification"],
                    "record_id": str(record.id),
                },
            )
    classifications: Counter[str] = Counter()
    originals = []
    source_ids = set()
    required_sources: set[tuple[str, str]] = set()
    source_blockers = []
    for raw_id in sorted(raw_ids, key=str):
        raw = await db.get(RawIngestion, raw_id)
        source = await db.get(DataSource, raw.source_id) if raw else None
        evidence = attestations.get(str(raw_id), {})
        classification = evidence.get("classification", "UNVERIFIED")
        if not raw or evidence.get("sha256") != raw.sha256:
            classification = "UNVERIFIED"
        if source and source.slug.startswith("TEST_"):
            classification = "SYNTHETIC"
        if source:
            source_ids.add(source.id)
            for kind in raw_kinds.get(raw_id, set()):
                use = {
                    "price": "prices",
                    "fx": "fx_rates",
                    "fact": "fundamentals",
                    "action": "corporate_actions",
                    "coverage": "action_coverage",
                    "macro": "macro",
                    "membership": "universe_membership",
                    "news": "news",
                    "estimate": "estimates",
                }.get(kind)
                if source.type == "MANUAL" and kind in {"price", "fx", "action"}:
                    use = "manual_upload"
                if use:
                    required_sources.add((str(source.id), use))
                    try:
                        SourceGate.require_enabled(source, use)
                    except AppError:
                        source_blockers.append({"source_slug": source.slug, "use": use})
        classifications[classification] += 1
        originals.append(
            {
                "raw_id": str(raw_id),
                "sha256": raw.sha256 if raw else None,
                "source_slug": source.slug if source else None,
                "classification": classification,
                "evidence_id": evidence.get("record_id"),
            }
        )
    return {
        "raw_ids": [str(i) for i in sorted(raw_ids, key=str)],
        "source_ids": [str(i) for i in sorted(source_ids, key=str)],
        "classifications": dict(classifications),
        "originals": originals,
        "required_sources": [
            {"source_id": sid, "use": use} for sid, use in sorted(required_sources)
        ],
        "source_blockers": source_blockers,
        "all_real": bool(raw_ids)
        and not source_blockers
        and all(o["classification"] in {"REAL_MANUAL", "REAL_PROVIDER"} for o in originals)
        and dataset.configuration.get("data_context") == "USER_ARCHIVE",
    }


def readiness_status(reasons: list[str], mode: str) -> str:
    if "SOURCE_APPROVAL_REQUIRED" in reasons:
        return "SOURCE_APPROVAL_REQUIRED"
    if "SYNTHETIC_OR_UNVERIFIED_INPUTS" in reasons or "DATASET_REQUIRED" in reasons:
        return "BLOCKED_BY_REAL_DATA"
    for code in (
        "CORPORATE_ACTION_COVERAGE_MISSING",
        "HISTORICAL_MEMBERSHIP_MISSING",
        "INSUFFICIENT_HISTORY",
        "INSUFFICIENT_OOS",
    ):
        if code in reasons:
            return code
    if mode != "STRICT_PIT":
        return "RECONSTRUCTED_RESEARCH_ONLY"
    return "PARTIAL_REAL_DATA" if reasons else "REAL_DATA_READY"


class RealDataReadinessService:
    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db, self.user_id = db, user_id

    async def report(self, request: ReadinessInput) -> dict[str, Any]:
        now = datetime.now(UTC)
        if request.end > now.date() or any(f.final_end > now for f in request.folds):
            raise AppError(422, "FUTURE_VALIDATION_RANGE", "Observed history only")
        await UniverseService(self.db).owned(request.universe_id, self.user_id)
        members = (
            await self.db.scalars(
                select(UniverseMembershipVersion).where(
                    UniverseMembershipVersion.universe_id == request.universe_id,
                    UniverseMembershipVersion.valid_from <= request.end,
                    UniverseMembershipVersion.known_at <= now,
                    UniverseMembershipVersion.observed_at <= now,
                )
            )
        ).all()
        historical = {
            m.instrument_id for m in members if m.valid_to is None or m.valid_to >= request.start
        }
        ids = request.instrument_ids or sorted(historical, key=str)
        if len(ids) > 5:
            raise AppError(
                422, "VALIDATION_UNIVERSE_LIMIT", "Audit at most five instruments plus benchmark"
            )
        sources = await source_preconditions(self.db, request.source_policy)
        reasons = ["SOURCE_APPROVAL_REQUIRED"] if any(s["gate_reason"] for s in sources) else []
        if not set(ids) <= historical:
            reasons.append("HISTORICAL_MEMBERSHIP_MISSING")
        coverage = []
        for iid in dict.fromkeys([*ids, request.benchmark_id]):
            if await self.db.get(Instrument, iid) is None:
                raise AppError(404, "INSTRUMENT_NOT_FOUND", "Explicit instrument/benchmark missing")
            start = request.start
            while start <= request.end:
                end = min(request.end, start + timedelta(days=1826))
                coverage.append(
                    await DataCoverageService(self.db, self.user_id).inspect(
                        iid, start, end, now, base_currency=request.base_currency
                    )
                )
                start = end + timedelta(days=1)
        if not ids:
            reasons.append("HISTORICAL_MEMBERSHIP_MISSING")
        if any(c["corporate_action_coverage"]["status"] != "VERIFIED" for c in coverage):
            reasons.append("CORPORATE_ACTION_COVERAGE_MISSING")
        if any(
            c["corporate_action_coverage"]["by_type"].get("DELISTING") != "VERIFIED"
            for c in coverage
        ):
            reasons.append("DELISTING_COVERAGE_UNVERIFIED")
        if any(
            c["fundamental_coverage"]["missing_metrics"]
            for c in coverage
            if c["instrument_id"] != str(request.benchmark_id)
        ):
            reasons.append("FUNDAMENTALS_INCOMPLETE")
        if any(c["FX_coverage"]["missing_sessions"] for c in coverage):
            reasons.append("FX_COVERAGE_MISSING")
        if any(not c["verified_availability"]["dataset_ready"] for c in coverage):
            reasons.append("PIT_EVIDENCE_INCOMPLETE")
        counts: dict[str, Any] = {
            "total_instruments": len(ids),
            "eligible_instruments": 0,
            "historical_sessions": None
            if any(c["price_coverage"]["expected_sessions"] is None for c in coverage)
            else sum(c["price_coverage"]["expected_sessions"] for c in coverage),
            "valid_price_observations": sum(
                c["price_coverage"]["available_valid_sessions"] for c in coverage
            ),
            "valid_open_prices": sum(c["OHLC_coverage"]["open_available"] for c in coverage),
            "validated_fx_sessions": sum(
                c["FX_coverage"]["checked_sessions"] - c["FX_coverage"]["missing_sessions"]
                for c in coverage
            ),
            "validated_fx_observations": len(
                {identifier for c in coverage for identifier in c["FX_coverage"]["observation_ids"]}
            ),
            "partition_status": "NOT_EVALUATED",
            "eligible_training_samples": None,
            "eligible_validation_samples": None,
            "eligible_calibration_samples": None,
            "eligible_oos_samples": None,
        }
        readiness, origins, partitions = None, None, []
        if request.dataset_id:
            dataset = await DatasetBuilder(self.db).owned(request.dataset_id, self.user_id)
            expected = {
                "universe_id": str(request.universe_id),
                "benchmark_id": str(request.benchmark_id),
                "start": request.start.isoformat(),
                "end": request.end.isoformat(),
                "target_horizon": request.horizon,
                "availability_mode": request.availability_mode,
                "base_currency": request.base_currency,
            }
            if any(dataset.configuration.get(k) != v for k, v in expected.items()) or (
                ids and not {r["instrument_id"] for r in dataset.rows} <= {str(i) for i in ids}
            ):
                raise AppError(
                    422,
                    "DATASET_AUDIT_SCOPE_MISMATCH",
                    "Pinned dataset must match exact audit scope",
                )
            readiness = await P7DataReadinessService(self.db).report(
                dataset.id, self.user_id, request.required_features, request.horizon
            )
            origins = await dataset_origins(self.db, dataset, self.user_id)
            source_ids = {s["source_id"] for s in sources}
            policy_uses = {(s["source_id"], s["use"]) for s in sources}
            if (
                not set(origins["source_ids"]) <= source_ids
                or not {(s["source_id"], s["use"]) for s in origins["required_sources"]}
                <= policy_uses
            ):
                reasons.append("PINNED_SOURCE_OUTSIDE_POLICY")
            if origins["source_blockers"]:
                reasons.append("SOURCE_APPROVAL_REQUIRED")
            if not origins["all_real"]:
                reasons.append("SYNTHETIC_OR_UNVERIFIED_INPUTS")
            if readiness["survivorship_risk"]:
                reasons.append("HISTORICAL_MEMBERSHIP_MISSING")
            if not readiness["production_data_eligible"]:
                reasons.append("INSUFFICIENT_HISTORY")
            counts.update(
                {
                    "eligible_instruments": readiness["eligible_instruments"],
                    "eligible_strict_pit_observations": readiness["eligible_observations"]
                    if request.availability_mode == "STRICT_PIT"
                    else 0,
                    "distinct_signal_dates": readiness["distinct_signal_dates"],
                    "matured_labels": readiness["total_observations"] - readiness["missing_labels"],
                    "missing_features": readiness["missing_features"],
                    "unverified_labels": readiness["missing_labels"],
                }
            )
            exchanges = {}
            for row in dataset.rows:
                if row["instrument_id"] not in exchanges:
                    instrument = await self.db.get(Instrument, UUID(row["instrument_id"]))
                    exchanges[row["instrument_id"]] = (
                        instrument.exchange or instrument.mic or "" if instrument else ""
                    )
            for fold in request.folds:
                try:
                    partitions.append(
                        split_rows(
                            dataset.rows,
                            fold,
                            request.horizon,
                            exchanges,
                            readiness["eligible_row_ids"],
                        )
                    )
                except ValueError as error:
                    raise AppError(422, "VALIDATION_SPLIT_INVALID", str(error)) from error
            if partitions:
                for name, output in (
                    ("training", "training"),
                    ("validation", "validation"),
                    ("calibration", "calibration"),
                ):
                    counts[f"eligible_{output}_samples"] = min(len(p[name]) for p in partitions)
                oos = {i for p in partitions for i in p["test"]}
                dates = sorted({dataset.rows[int(i)]["date"] for i in oos})
                counts.update(
                    {
                        "partition_status": "PINNED_CHRONOLOGICAL_SPLITS",
                        "eligible_oos_samples": len(oos),
                        "oos_distinct_signal_dates": len(dates),
                        "walk_forward_folds": len(partitions),
                        "effective_sample_size": {
                            "value": len(dates[:: request.horizon]),
                            "method": "nonoverlapping-date-proxy; not an independence guarantee",
                        },
                    }
                )
                if counts["eligible_training_samples"] < int(
                    str(PROMOTION_RULES["minimum_training_observations"])
                ):
                    reasons.append("INSUFFICIENT_HISTORY")
                if (
                    len(oos) < int(str(PROMOTION_RULES["minimum_oos_observations"]))
                    or len(dates) < int(str(PROMOTION_RULES["minimum_oos_signal_dates"]))
                    or len(partitions) < int(str(PROMOTION_RULES["minimum_folds"]))
                ):
                    reasons.append("INSUFFICIENT_OOS")
            else:
                reasons.append("EXPERIMENT_WINDOWS_REQUIRED")
        else:
            reasons.append("DATASET_REQUIRED")
        if any(
            c["price_coverage"]["missing_sessions"]
            or c["price_coverage"]["quarantined_rows"]
            or c["price_coverage"]["expected_sessions"] is None
            for c in coverage
        ):
            reasons.append("PRICE_COVERAGE_INCOMPLETE")
        reasons = sorted(set(reasons))
        return {
            "contract": "pr2-real-readiness-v1",
            "readiness_status": readiness_status(reasons, request.availability_mode),
            "blocking_reasons": reasons,
            "counts": counts,
            "sources": sources,
            "coverage": coverage,
            "p7": readiness,
            "origins": origins,
            "partitions": partitions,
            "promotion_rules": PROMOTION_RULES,
            "recommendations": "V3 RECOMMENDATIONS GATED",
            "evaluated_at": now.isoformat(),
            "financial_validation": "NOT_ESTABLISHED",
        }
