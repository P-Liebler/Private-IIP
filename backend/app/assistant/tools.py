import asyncio
from datetime import datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.documents import cutoff_time
from app.assistant.news import archived_news
from app.assistant.safety import safe_value
from app.core.errors import AppError
from app.models import (
    DataSource,
    Instrument,
    MLModelVersion,
    ModelPromotionReview,
    Prediction,
    PredictionOutcome,
    Recommendation,
    RiskSnapshot,
)
from app.recommendations.portfolio_context import valuation_identity
from app.schemas.assistant import EvidenceFact, FactType, ToolInput
from app.services.fundamentals import digest
from app.services.pit_features import json_value
from app.services.portfolio_valuation import PortfolioValuationService
from app.services.portfolios import PortfolioService
from app.services.research import ResearchService
from app.services.risk_market import RiskMarket
from app.services.sources import SourceGate


def evidence(
    label: str,
    value: Any,
    kind: FactType,
    cutoff: datetime,
    references: list[dict[str, Any]],
    unit: str | None = None,
    limitation: str | None = None,
) -> EvidenceFact:
    clean = safe_value(json_value(value))
    identity = digest(
        {"label": label, "value": clean, "cutoff": cutoff.isoformat(), "references": references}
    )
    return EvidenceFact(
        id=identity,
        label=label,
        value=clean,
        fact_type=kind,
        as_of=cutoff,
        source_references=references,
        unit=unit,
        limitation=limitation,
    )


async def saved_production_forecast(
    db: AsyncSession, user_id: UUID, instrument_id: UUID, horizon: int, cutoff: datetime
) -> Prediction | None:
    row = await db.scalar(
        select(Prediction)
        .where(
            Prediction.user_id == user_id,
            Prediction.instrument_id == instrument_id,
            Prediction.horizon == horizon,
            Prediction.created_at <= cutoff,
            Prediction.generated_at <= cutoff,
            Prediction.information_cutoff_at <= cutoff,
        )
        .order_by(Prediction.generated_at.desc(), Prediction.id.desc())
        .limit(1)
    )
    if (
        not row
        or row.result.get("confidence_status") != "VALIDATED"
        or row.generated_at < cutoff - timedelta(hours=24)
    ):
        return None
    model_ids = row.result.get("model_versions", [])
    if not model_ids:
        return None
    for identifier in model_ids:
        model = await db.get(MLModelVersion, UUID(identifier))
        review = await db.scalar(
            select(ModelPromotionReview)
            .where(
                ModelPromotionReview.model_id == UUID(identifier),
                ModelPromotionReview.created_at <= cutoff,
            )
            .order_by(ModelPromotionReview.created_at.desc(), ModelPromotionReview.id.desc())
            .limit(1)
        )
        if (
            not model
            or model.user_id != user_id
            or model.created_at > cutoff
            or not review
            or review.status != "PRODUCTION"
        ):
            return None
    return row


class ToolRegistry:
    """Typed allowlist. Tool inputs cannot carry user IDs, SQL, URLs or commands."""

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db, self.user_id = db, user_id

    async def call(self, request: ToolInput) -> list[EvidenceFact]:
        cutoff = cutoff_time(request.as_of)
        if request.portfolio_id:
            portfolio = await PortfolioService(self.db, self.user_id).owned(request.portfolio_id)
            if portfolio.created_at > cutoff:
                return [
                    evidence(
                        request.name,
                        {"reason": "PORTFOLIO_NOT_ARCHIVED_AT_SELECTED_DATE"},
                        "UNAVAILABLE",
                        cutoff,
                        [],
                    )
                ]
        try:
            async with asyncio.timeout(8):
                facts = await self._call(request, cutoff)
            if len(json_value([f.model_dump(mode="json") for f in facts]).__str__()) > 60000:
                raise AppError(422, "TOOL_OUTPUT_LIMIT", "Tool response exceeded its limit")
            return facts[:25]
        except (AppError, TimeoutError) as error:
            if isinstance(error, AppError) and error.status_code in (401, 403, 404):
                raise
            code = error.code if isinstance(error, AppError) else "TOOL_TIMEOUT"
            return [
                evidence(
                    request.name,
                    {"reason": code},
                    "UNAVAILABLE",
                    cutoff,
                    [],
                    limitation="Ich kann das mit den verfügbaren Daten nicht verifizieren.",
                )
            ]

    async def value(self, portfolio_id: UUID, cutoff: datetime) -> dict[str, Any]:
        valuation = PortfolioValuationService(self.db, self.user_id)
        valuation.market = RiskMarket(
            self.db, cutoff.date() - timedelta(days=7), cutoff.date(), cutoff
        )  # type: ignore[assignment]
        return cast(dict[str, Any], await valuation.value(portfolio_id, as_of=cutoff))

    async def _call(self, request: ToolInput, cutoff: datetime) -> list[EvidenceFact]:
        name, pid, iid = request.name, request.portfolio_id, request.instrument_id

        def unavailable(reason: str) -> list[EvidenceFact]:
            return [
                evidence(
                    name,
                    {"reason": reason},
                    "UNAVAILABLE",
                    cutoff,
                    [],
                    limitation="Ich kann das mit den verfügbaren Daten nicht verifizieren.",
                )
            ]

        if name in {"getPortfolio", "getHoldings"}:
            if not pid:
                return unavailable("PORTFOLIO_SCOPE_REQUIRED")
            value = await self.value(pid, cutoff)
            refs = [
                {
                    "entity_type": "portfolio_ledger",
                    "id": str(pid),
                    "url": f"/portfolios/{pid}",
                    "transaction_ids": value["transaction_ids"],
                    "input_hash": digest(value),
                }
            ]
            if name == "getHoldings":
                return [
                    evidence(
                        "Bestand",
                        {
                            k: h.get(k)
                            for k in (
                                "instrument_id",
                                "name",
                                "quantity",
                                "market_value_base",
                                "weight",
                                "price_date",
                                "valuation_status",
                            )
                        },
                        "DERIVED_METRIC" if h["market_value_base"] is not None else "UNAVAILABLE",
                        cutoff,
                        refs,
                        value["base_currency"],
                    )
                    for h in value["holdings"][:20]
                ] or unavailable("NO_SECURITIES_POSITIONS")
            return [
                evidence(
                    "Portfolio-Wert aus bekannten Kursen",
                    value["total_value_base"],
                    "DERIVED_METRIC" if value["status"] == "COMPLETE" else "UNAVAILABLE",
                    cutoff,
                    refs,
                    value["base_currency"],
                    None
                    if value["status"] == "COMPLETE"
                    else (
                        "Bewertung ist unvollständig; fehlende Kurse oder FX sind keine Nullwerte."
                    ),
                ),
                evidence(
                    "Cash in Basiswährung",
                    value["cash_value_base"],
                    "DERIVED_METRIC" if value["cash_value_base"] is not None else "UNAVAILABLE",
                    cutoff,
                    refs,
                    value["base_currency"],
                ),
                evidence(
                    "Bewertungsqualität",
                    {"status": value["status"], "issues": value["issues"]},
                    "VERIFIED_FACT",
                    cutoff,
                    refs,
                ),
            ]
        if name == "getRisk":
            if not pid:
                return unavailable("PORTFOLIO_SCOPE_REQUIRED")
            row = await self.db.scalar(
                select(RiskSnapshot)
                .where(
                    RiskSnapshot.user_id == self.user_id,
                    RiskSnapshot.portfolio_id == pid,
                    RiskSnapshot.as_of <= cutoff,
                    RiskSnapshot.created_at <= cutoff,
                )
                .order_by(RiskSnapshot.created_at.desc(), RiskSnapshot.id.desc())
                .limit(1)
            )
            if not row or row.as_of < cutoff - timedelta(hours=24):
                return unavailable("NO_CURRENT_VALIDATED_RISK_SNAPSHOT")
            current = await self.value(pid, cutoff)
            if valuation_identity(current) != valuation_identity(row.result["current_valuation"]):
                return unavailable("RISK_SNAPSHOT_NO_LONGER_MATCHES_LEDGER_OR_MARKET")
            refs = [
                {
                    "entity_type": "risk_snapshot",
                    "id": str(row.id),
                    "hash": row.content_hash,
                    "url": f"/portfolios/{pid}",
                }
            ]
            result = []
            for key, label in (
                ("annualized_volatility", "Jahresvolatilität"),
                ("maximum_drawdown", "Historischer Maximum Drawdown"),
            ):
                metric = row.result["metrics"].get(key)
                result.append(
                    evidence(
                        label,
                        metric,
                        "DERIVED_METRIC" if metric is not None else "UNAVAILABLE",
                        row.as_of,
                        refs,
                        "fraction",
                        "Historische Beobachtung, keine Zukunftsgarantie.",
                    )
                )
            concentration = row.result["exposures"].get("concentration")
            result.append(
                evidence(
                    "Konzentration",
                    concentration,
                    "DERIVED_METRIC" if concentration else "UNAVAILABLE",
                    row.as_of,
                    refs,
                )
            )
            result.append(
                evidence(
                    "Netto-Währungsexposure einschließlich Cash",
                    row.result["exposures"].get("currency"),
                    "DERIVED_METRIC",
                    row.as_of,
                    refs,
                )
            )
            return result
        if name == "getRecommendation":
            statement = select(Recommendation).where(
                Recommendation.user_id == self.user_id,
                Recommendation.generated_at <= cutoff,
                Recommendation.created_at <= cutoff,
            )
            if pid:
                statement = statement.where(Recommendation.portfolio_id == pid)
            if iid:
                statement = statement.where(Recommendation.instrument_id == iid)
            row = await self.db.scalar(
                statement.order_by(
                    Recommendation.generated_at.desc(), Recommendation.id.desc()
                ).limit(1)
            )
            if not row:
                return unavailable("NO_VALIDATED_PRODUCTION_FORECAST_AND_STRATEGY_EVIDENCE")
            refs = [
                {
                    "entity_type": "recommendation",
                    "id": str(row.id),
                    "hash": row.input_manifest_hash,
                    "url": "/recommendations",
                }
            ]
            return [
                evidence(
                    "Recommendation-Gate",
                    {
                        "category": row.category,
                        "eligibility": row.eligibility,
                        "generated_at": row.generated_at,
                        "current_action_permission": False,
                        "notice": "READ_ONLY_ARCHIVED_RESULT_REQUIRES_FRESH_P9_EVALUATION",
                    },
                    "UNAVAILABLE" if not row.eligibility["permitted"] else "DERIVED_METRIC",
                    cutoff,
                    refs,
                    limitation=(
                        "Der Assistent erteilt keine neue Empfehlung und überstimmt "
                        "keine P9-Sperre."
                    ),
                )
            ]
        if name == "getDataQuality":
            if pid:
                value = await self.value(pid, cutoff)
                return [
                    evidence(
                        "Datenqualität",
                        {
                            "valuation_status": value["status"],
                            "issues": value["issues"],
                            "price_dates": [
                                {
                                    "instrument_id": str(h["instrument_id"]),
                                    "date": h["price_date"],
                                    "status": h["valuation_status"],
                                }
                                for h in value["holdings"][:20]
                            ],
                            "production_forecast_and_strategy_required": True,
                        },
                        "VERIFIED_FACT",
                        cutoff,
                        [
                            {
                                "entity_type": "portfolio_ledger",
                                "id": str(pid),
                                "url": f"/portfolios/{pid}",
                            }
                        ],
                    )
                ]
            return unavailable("PORTFOLIO_SCOPE_REQUIRED")
        if not iid:
            return unavailable("INSTRUMENT_SCOPE_REQUIRED")
        instrument = await self.db.get(Instrument, iid)
        if not instrument or instrument.created_at > cutoff:
            raise AppError(404, "INSTRUMENT_NOT_FOUND", "Instrument not found at this cutoff")
        refs = [{"entity_type": "instrument", "id": str(iid), "url": f"/instrument/{iid}"}]
        if name == "getInstrument":
            market = RiskMarket(self.db, cutoff.date() - timedelta(days=7), cutoff.date(), cutoff)
            prices = cast(
                list[dict[str, Any]], (await market.prices(iid, market.start, market.end))["prices"]
            )
            price = prices[-1] if prices else None
            metadata = {
                "id": str(iid),
                "name": instrument.name
                if instrument.updated_at <= cutoff
                else "NOT_ARCHIVED_AT_SELECTED_DATE",
                "currency": instrument.currency if instrument.updated_at <= cutoff else None,
            }
            return [
                evidence("Instrument", metadata, "VERIFIED_FACT", cutoff, refs),
                evidence(
                    "Letzter gespeicherter Schlusskurs",
                    price,
                    "VERIFIED_FACT" if price else "UNAVAILABLE",
                    cutoff,
                    refs,
                    instrument.currency,
                    "Gespeicherter datierter Schlusskurs; kein Live- oder Ausführungskurs.",
                ),
            ]
        if name == "getFinancials":
            research = await ResearchService(self.db).calculate(iid, cutoff)
            facts = []
            for label, metric in {**research["metrics"], **research["valuation"]}.items():
                facts.append(
                    evidence(
                        label,
                        {
                            "value": metric.get("value"),
                            "status": metric["status"],
                            "inputs": metric.get("inputs", []),
                        },
                        "DERIVED_METRIC" if metric.get("status") == "AVAILABLE" else "UNAVAILABLE",
                        cutoff,
                        refs,
                    )
                )
            return facts[:20]
        if name == "getForecast":
            prediction = await saved_production_forecast(
                self.db, self.user_id, iid, request.horizon, cutoff
            )
            if not prediction:
                return unavailable("NO_VALIDATED_PRODUCTION_FORECAST")
            values = {
                k: prediction.result.get(k)
                for k in (
                    "probability_outperform",
                    "expected_excess_return",
                    "lower_bound",
                    "upper_bound",
                    "confidence_status",
                    "model_versions",
                )
            }
            return [
                evidence(
                    "Validierte archivierte Modellprognose",
                    values,
                    "MODEL_FORECAST",
                    prediction.generated_at,
                    [
                        *refs,
                        {
                            "entity_type": "prediction",
                            "id": str(prediction.id),
                            "url": f"/instrument/{iid}",
                        },
                    ],
                    limitation="Modellschätzung mit Unsicherheit; keine Handlungsempfehlung.",
                )
            ]
        if name == "getPredictionHistory":
            predictions = (
                await self.db.scalars(
                    select(Prediction)
                    .where(
                        Prediction.user_id == self.user_id,
                        Prediction.instrument_id == iid,
                        Prediction.generated_at <= cutoff,
                        Prediction.created_at <= cutoff,
                    )
                    .order_by(Prediction.generated_at.desc(), Prediction.id.desc())
                    .limit(10)
                )
            ).all()
            result = []
            for prediction in predictions:
                outcomes = (
                    await self.db.scalars(
                        select(PredictionOutcome)
                        .where(
                            PredictionOutcome.prediction_id == prediction.id,
                            PredictionOutcome.created_at <= cutoff,
                        )
                        .order_by(PredictionOutcome.created_at, PredictionOutcome.id)
                    )
                ).all()
                result.append(
                    evidence(
                        "Archivierte Prognose einschließlich Ablehnungen",
                        {
                            "id": prediction.id,
                            "generated_at": prediction.generated_at,
                            "forecast": {
                                k: prediction.result.get(k)
                                for k in (
                                    "confidence_status",
                                    "reason",
                                    "probability_outperform",
                                    "expected_excess_return",
                                    "lower_bound",
                                    "upper_bound",
                                    "model_versions",
                                )
                            },
                            "outcomes": [
                                {"id": str(o.id), "created_at": o.created_at, "result": o.result}
                                for o in outcomes[-5:]
                            ],
                        },
                        "MODEL_FORECAST",
                        cutoff,
                        [
                            *refs,
                            {
                                "entity_type": "prediction",
                                "id": str(prediction.id),
                                "url": f"/instrument/{iid}",
                            },
                        ],
                        limitation=(
                            "Historischer Record; ein Shadow- oder abgelöstes Modell ist"
                            " keine heutige Produktionsfreigabe."
                        ),
                    )
                )
            return result or unavailable("NO_HISTORICAL_PREDICTION")
        if name == "getNews":
            rows = await archived_news(self.db, iid, cutoff, 10)
            facts = []
            for news in rows:
                source = await self.db.get(DataSource, news.source_id)
                try:
                    if not source:
                        continue
                    SourceGate.require_enabled(source, "news")
                except AppError:
                    continue
                facts.append(
                    evidence(
                        "Archivierte Nachrichtenmetadaten",
                        {"title": news.title, "published_at": news.published_at},
                        "VERIFIED_FACT",
                        cutoff,
                        [
                            {
                                "entity_type": "news_article",
                                "id": str(news.id),
                                "raw_ingestion_id": str(news.raw_ingestion_id),
                                "url": "/news",
                            }
                        ],
                        limitation=(
                            "Headline-Metadaten; keine ungeprüfte Sentiment- oder "
                            "Volltextauswertung."
                        ),
                    )
                )
            return facts or unavailable("NO_PERMITTED_NEWS_METADATA_AT_CUTOFF")
        raise AppError(422, "TOOL_NOT_ALLOWED", "Unsupported read-only tool")
