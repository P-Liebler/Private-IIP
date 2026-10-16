"""Small Prometheus exposition for the single-process V1 API."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Awaitable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from sqlalchemy import Integer, func, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.dialects.postgresql import JSONPATH

from app.assistant.metrics import exposition as intelligence_exposition
from app.core.valkey import make_valkey_client
from app.db.session import check_database, get_session_factory
from app.models import (
    AlertEvaluation,
    AlertEvent,
    AssistantMessage,
    BacktestRun,
    ChunkEmbedding,
    DailyBrief,
    DataQuarantine,
    DatasetVersion,
    FundamentalFact,
    MLTrainingRun,
    ModelPromotionReview,
    NewsArticle,
    OptimizerRun,
    PITJob,
    Prediction,
    PriceDaily,
    RawIngestion,
    Recommendation,
    ResearchDocument,
    RiskSnapshot,
    ScenarioRun,
    WhatIfRun,
)
from app.services.collection_audit import collection_metrics

router = APIRouter()
_request_count: Counter[tuple[str, str, int]] = Counter()
_duration_sum: dict[tuple[str, str], float] = defaultdict(float)
_valuation_failures = 0
_risk_failures = 0
BACKUP_STATUS_PATH = Path("/app/runtime/backup-status.json")


def observe(method: str, route: str, status: int, duration: float) -> None:
    global _valuation_failures, _risk_failures
    key = (method, route, status)
    _request_count[key] += 1
    _duration_sum[(method, route)] += duration
    if route.endswith("/valuation") and status >= 500:
        _valuation_failures += 1
    if method == "POST" and route.endswith("/risk") and status >= 400:
        _risk_failures += 1


@router.get("/internal/metrics", include_in_schema=False)
async def metrics() -> PlainTextResponse:
    lines = [
        "# TYPE private_iip_http_requests_total counter",
        "# TYPE private_iip_http_duration_seconds_sum counter",
        "# TYPE private_iip_db_ready gauge",
        "# TYPE private_iip_risk_calculation_failures_total counter",
        f"private_iip_risk_calculation_failures_total {_risk_failures}",
        "# TYPE private_iip_failed_imports gauge",
        "# TYPE private_iip_quarantined_rows gauge",
        "# TYPE private_iip_stale_prices gauge",
        "# TYPE private_iip_valuation_failures_total counter",
        "# TYPE private_iip_backup_success gauge",
        "# TYPE private_iip_backup_timestamp_seconds gauge",
        "# TYPE private_iip_queue_depth gauge",
        "# TYPE private_iip_queue_ready gauge",
    ]
    for (method, route, status), count in sorted(_request_count.items()):
        safe_route = route.replace('"', "").replace("\\", "")
        labels = f'method="{method}",route="{safe_route}",status="{status}"'
        lines.append(f"private_iip_http_requests_total{{{labels}}} {count}")
    for (method, route), duration in sorted(_duration_sum.items()):
        safe_route = route.replace('"', "").replace("\\", "")
        labels = f'method="{method}",route="{safe_route}"'
        lines.append(f"private_iip_http_duration_seconds_sum{{{labels}}} {duration:.6f}")
    try:
        await check_database()
        lines.append("private_iip_db_ready 1")
        async with get_session_factory()() as db:
            for name, model, condition in [
                (
                    "assistant_messages_total",
                    AssistantMessage,
                    AssistantMessage.role == "ASSISTANT",
                ),
                (
                    "assistant_unavailable_total",
                    AssistantMessage,
                    (AssistantMessage.role == "ASSISTANT")
                    & (AssistantMessage.status != "AVAILABLE"),
                ),
                ("rag_documents_total", ResearchDocument, None),
                ("rag_embeddings_total", ChunkEmbedding, None),
                ("alert_evaluations_total", AlertEvaluation, None),
                (
                    "alert_unavailable_total",
                    AlertEvaluation,
                    AlertEvaluation.status == "ALERT_EVALUATION_UNAVAILABLE",
                ),
                ("alert_events_total", AlertEvent, None),
                ("daily_briefs_total", DailyBrief, None),
                ("optimizer_runs_total", OptimizerRun, None),
                (
                    "optimizer_unavailable_total",
                    OptimizerRun,
                    OptimizerRun.result["status"].astext != "AVAILABLE",
                ),
                ("ml_training_jobs_total", MLTrainingRun, None),
                ("risk_snapshots_total", RiskSnapshot, None),
                (
                    "risk_snapshots_partial_total",
                    RiskSnapshot,
                    RiskSnapshot.result["status"].astext == "PARTIAL",
                ),
                (
                    "var_unavailable_total",
                    RiskSnapshot,
                    RiskSnapshot.result["metrics"]["var"]["var"].astext.is_(None),
                ),
                ("scenario_runs_total", ScenarioRun, None),
                ("what_if_runs_total", WhatIfRun, None),
                ("ml_training_failures_total", MLTrainingRun, MLTrainingRun.status == "FAILED"),
                (
                    "prediction_abstentions_total",
                    Prediction,
                    Prediction.result["confidence_status"].astext == "NO RELIABLE FORECAST",
                ),
                (
                    "prediction_generation_failures_total",
                    Prediction,
                    Prediction.result["reason"].astext == "INFERENCE_FAILED",
                ),
            ]:
                statement = select(func.count()).select_from(model)
                if condition is not None:
                    statement = statement.where(condition)
                persisted_count = await db.scalar(statement)
                lines.extend(
                    [
                        f"# TYPE private_iip_{name} counter",
                        f"private_iip_{name} {persisted_count or 0}",
                    ]
                )
            ranked_status = select(
                ModelPromotionReview.status,
                func.row_number()
                .over(
                    partition_by=ModelPromotionReview.model_id,
                    order_by=(
                        ModelPromotionReview.created_at.desc(),
                        ModelPromotionReview.id.desc(),
                    ),
                )
                .label("rank"),
            ).subquery()
            status_rows = (
                await db.execute(
                    select(ranked_status.c.status, func.count())
                    .where(ranked_status.c.rank == 1)
                    .group_by(ranked_status.c.status)
                )
            ).all()
            status_counts = {str(status): int(number) for status, number in status_rows}
            lines.append("# TYPE private_iip_model_status gauge")
            for model_status in ("EXPERIMENT", "VALIDATION", "SHADOW", "PRODUCTION", "RETIRED"):
                lines.append(
                    f'private_iip_model_status{{status="{model_status}"}} '
                    f"{status_counts.get(model_status, 0)}"
                )
            drift_reviews = (
                await db.scalars(
                    select(ModelPromotionReview)
                    .where(ModelPromotionReview.evidence["origin"].astext == "MODEL_DEGRADED")
                    .order_by(ModelPromotionReview.created_at.desc())
                    .limit(10)
                )
            ).all()
            drift_value = (
                str(max(float(r.evidence["metrics"]["ece"]) for r in drift_reviews))
                if drift_reviews
                else "NaN"
            )
            lines.extend(
                [
                    "# TYPE private_iip_calibration_drift gauge",
                    f"private_iip_calibration_drift {drift_value}",
                ]
            )
            for kind, prefix in [("DATASET_BUILD", "dataset_build"), ("BACKTEST", "backtest")]:
                job_count = await db.scalar(
                    select(func.count()).select_from(PITJob).where(PITJob.kind == kind)
                )
                failures = await db.scalar(
                    select(func.count())
                    .select_from(PITJob)
                    .where(PITJob.kind == kind, PITJob.status == "FAILED")
                )
                duration = await db.scalar(
                    select(
                        func.sum(func.extract("epoch", PITJob.completed_at - PITJob.started_at))
                    ).where(PITJob.kind == kind)
                )
                lines.extend(
                    [
                        f"# TYPE private_iip_{prefix}_total counter",
                        f"private_iip_{prefix}_total {job_count or 0}",
                        f"private_iip_{prefix}_failures_total {failures or 0}",
                        f"private_iip_{prefix}_duration_seconds_sum {duration or 0}",
                    ]
                )
            exclusions = await db.scalar(
                select(
                    func.sum(
                        sql_cast(DatasetVersion.quality["excluded_observations"].astext, Integer)
                    )
                )
            )
            no_fill = await db.scalar(
                select(
                    func.sum(
                        func.jsonb_array_length(
                            func.jsonb_path_query_array(
                                BacktestRun.result,
                                sql_cast('$.orders[*] ? (@.status == "NO_FILL")', JSONPATH),
                            )
                        )
                    )
                )
            )
            lines.extend(
                [
                    f"private_iip_pit_exclusions_total {exclusions or 0}",
                    f"private_iip_execution_unavailable_total {no_fill or 0}",
                ]
            )
            lines.extend(await collection_metrics(db))
            failed = await db.scalar(
                select(func.count())
                .select_from(RawIngestion)
                .where(RawIngestion.status == "FAILED")
            )
            quarantined = await db.scalar(select(func.count()).select_from(DataQuarantine))
            latest = (
                select(
                    PriceDaily.instrument_id, func.max(PriceDaily.trading_date).label("last_date")
                )
                .group_by(PriceDaily.instrument_id)
                .subquery()
            )
            stale = await db.scalar(
                select(func.count())
                .select_from(latest)
                .where(latest.c.last_date < datetime.now(UTC).date() - timedelta(days=7))
            )
            lines.extend(
                [
                    f"private_iip_failed_imports {failed or 0}",
                    f"private_iip_quarantined_rows {quarantined or 0}",
                    f"private_iip_stale_prices {stale or 0}",
                ]
            )
            rejected = await db.scalar(
                select(func.count())
                .select_from(FundamentalFact)
                .where(FundamentalFact.validation_status == "REJECTED")
            )
            recommendation_counts = (
                await db.execute(
                    select(
                        func.count(Recommendation.id),
                        func.count(Recommendation.id).filter(
                            Recommendation.category.in_(["INSUFFICIENT_DATA", "INELIGIBLE"])
                        ),
                        func.sum(
                            func.jsonb_array_length(Recommendation.eligibility["missing_inputs"])
                            + func.jsonb_array_length(Recommendation.eligibility["violations"])
                        ),
                    )
                )
            ).one()
            for name, number in zip(
                ("evaluations", "abstentions", "gate_failures"), recommendation_counts, strict=True
            ):
                lines.append(f"private_iip_recommendation_{name}_total {number or 0}")
            news_duplicates = await db.scalar(
                select(func.count())
                .select_from(NewsArticle)
                .where(NewsArticle.duplicate_of_id.is_not(None))
            )
            lines.extend(
                [
                    "# TYPE private_iip_research_rejected_facts gauge",
                    f"private_iip_research_rejected_facts {rejected or 0}",
                    "# TYPE private_iip_news_duplicates gauge",
                    f"private_iip_news_duplicates {news_duplicates or 0}",
                ]
            )
    except Exception:
        lines.append("private_iip_db_ready 0")
    lines.append(f"private_iip_valuation_failures_total {_valuation_failures}")
    valkey = make_valkey_client()
    try:
        heartbeat = await valkey.get("intelligence:last-dispatch")
        if heartbeat:
            dispatch = json.loads(heartbeat)
            lines.append(
                "private_iip_intelligence_scheduler_timestamp_seconds "
                f"{float(dispatch['completed_at'])}"
            )
            lines.append(
                f"private_iip_intelligence_scheduler_last_failures {int(dispatch['failed'])}"
            )
        else:
            lines.append("private_iip_intelligence_scheduler_timestamp_seconds 0")
        depth = await cast(Awaitable[int], valkey.llen("celery"))
        lines.extend(["private_iip_queue_ready 1", f"private_iip_queue_depth {depth}"])
    except Exception:
        lines.append("private_iip_queue_ready 0")
    finally:
        await valkey.aclose()
    if BACKUP_STATUS_PATH.exists():
        try:
            status = json.loads(BACKUP_STATUS_PATH.read_text(encoding="utf-8"))
            lines.append(f"private_iip_backup_success {1 if status['success'] else 0}")
            lines.append(
                f"private_iip_backup_timestamp_seconds {int(status['completed_timestamp'])}"
            )
        except (OSError, ValueError, KeyError, TypeError):
            lines.append("private_iip_backup_success 0")
    lines.extend(intelligence_exposition())
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
