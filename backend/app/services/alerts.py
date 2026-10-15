from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.tools import ToolRegistry, saved_production_forecast
from app.core.errors import AppError
from app.models import (
    AlertEvaluation,
    AlertEvent,
    AlertRule,
    AlertRuleVersion,
    DataSource,
    Instrument,
    NewsArticle,
    NewsInstrument,
    Notification,
    ResearchSnapshot,
    RiskSnapshot,
)
from app.recommendations.portfolio_context import valuation_identity
from app.schemas.assistant import AlertRuleInput
from app.services.financial_events import FinancialEventService
from app.services.fundamentals import digest
from app.services.portfolios import PortfolioService
from app.services.risk_market import RiskMarket
from app.services.sources import SourceGate

D = Decimal
ALERT_VERSION = "typed-threshold-transitions-v1"


@dataclass
class Observation:
    value: Decimal | None
    inputs: dict[str, Any]
    reason: str | None = None
    confirmed_false: bool = False


def transition(
    config: AlertRuleInput,
    observation: Observation,
    previous_value: Decimal | None,
    previous_state: bool | None,
    last_event_at: datetime | None,
    now: datetime,
) -> dict[str, Any]:
    if observation.reason or observation.value is None and not observation.confirmed_false:
        return {
            "status": "ALERT_EVALUATION_UNAVAILABLE",
            "state": None,
            "trigger": False,
            "reason": observation.reason or "INPUT_UNAVAILABLE",
        }
    if observation.confirmed_false:
        state = False
    else:
        value = observation.value
        assert value is not None
        if not value.is_finite():
            return {
                "status": "ALERT_EVALUATION_UNAVAILABLE",
                "state": None,
                "trigger": False,
                "reason": "NONFINITE_INPUT",
            }
        if config.direction in {"ABSOLUTE_CHANGE", "INCREASE", "DECREASE"}:
            if previous_value is None:
                return {
                    "status": "BASELINE_RECORDED",
                    "state": None,
                    "trigger": False,
                    "reason": "PREVIOUS_VALID_INPUT_REQUIRED",
                }
            change = (
                abs(value - previous_value)
                if config.direction == "ABSOLUTE_CHANGE"
                else value - previous_value
                if config.direction == "INCREASE"
                else previous_value - value
            )
            state = change >= config.threshold
        else:
            state = (
                value >= config.threshold
                if config.direction == "ABOVE"
                else value <= config.threshold
            )
    changed_event = config.direction in {"ABSOLUTE_CHANGE", "INCREASE", "DECREASE"}
    crossed = state and (previous_state is not True or changed_event)
    cooldown = (
        last_event_at is not None
        and (now - last_event_at).total_seconds() < config.cooldown_seconds
    )
    return {
        "status": "AVAILABLE",
        "state": state,
        "trigger": bool(crossed and not cooldown),
        "cooldown_suppressed": bool(crossed and cooldown),
        "reason": None,
    }


class AlertEvaluationService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db, self.user_id = db, user_id

    async def owned(self, identifier: UUID, lock: bool = False) -> AlertRule:
        row = await self.db.scalar(
            select(AlertRule)
            .where(AlertRule.id == identifier, AlertRule.user_id == self.user_id)
            .with_for_update()
            if lock
            else select(AlertRule).where(
                AlertRule.id == identifier, AlertRule.user_id == self.user_id
            )
        )
        if not row:
            raise AppError(404, "ALERT_RULE_NOT_FOUND", "Alert rule not found")
        return row

    async def latest(self, identifier: UUID) -> AlertRuleVersion:
        row = await self.db.scalar(
            select(AlertRuleVersion)
            .where(AlertRuleVersion.rule_id == identifier, AlertRuleVersion.user_id == self.user_id)
            .order_by(AlertRuleVersion.created_at.desc(), AlertRuleVersion.id.desc())
            .limit(1)
        )
        if not row:
            raise AppError(409, "ALERT_CONFIGURATION_UNAVAILABLE", "No rule version exists")
        return row

    async def save(
        self, config: AlertRuleInput, identifier: UUID | None = None
    ) -> AlertRuleVersion:
        if config.instrument_id and not await self.db.get(Instrument, config.instrument_id):
            raise AppError(422, "INSTRUMENT_NOT_FOUND", "Unknown instrument")
        if config.portfolio_id:
            await PortfolioService(self.db, self.user_id).owned(config.portfolio_id)
        if config.type in {"RISK_INCREASED", "CONCENTRATION_INCREASED"} and not config.portfolio_id:
            raise AppError(422, "PORTFOLIO_SCOPE_REQUIRED", "Portfolio is required for this rule")
        if (
            config.type not in {"RISK_INCREASED", "CONCENTRATION_INCREASED"}
            and not config.instrument_id
        ):
            raise AppError(422, "INSTRUMENT_SCOPE_REQUIRED", "Instrument is required for this rule")
        if identifier:
            rule = await self.owned(identifier, lock=True)
        else:
            count = await self.db.scalar(
                select(func.count())
                .select_from(AlertRule)
                .where(AlertRule.user_id == self.user_id, AlertRule.archived.is_(False))
            )
            if (count or 0) >= 50:
                raise AppError(422, "ALERT_RULE_LIMIT", "At most 50 active rules are supported")
            rule = AlertRule(user_id=self.user_id, archived=False, created_at=datetime.now(UTC))
            self.db.add(rule)
            await self.db.flush()
        row = AlertRuleVersion(
            user_id=self.user_id,
            rule_id=rule.id,
            configuration=config.model_dump(mode="json"),
            created_at=datetime.now(UTC),
        )
        self.db.add(row)
        await self.db.commit()
        return row

    async def observe(self, config: AlertRuleInput, now: datetime) -> Observation:
        iid, pid = config.instrument_id, config.portfolio_id
        if config.type == "PRICE_THRESHOLD":
            assert iid
            market = RiskMarket(self.db, now.date() - timedelta(days=7), now.date(), now)
            prices = cast(
                list[dict[str, Any]], (await market.prices(iid, market.start, market.end))["prices"]
            )
            price = prices[-1] if prices else None
            if not price:
                return Observation(None, {}, "CURRENT_VALID_PRICE_UNAVAILABLE")
            return Observation(
                D(str(price["close"])),
                {
                    "price_version_id": str(price["id"]),
                    "raw_ingestion_id": str(price["raw_ingestion_id"]),
                    "date": str(price["date"]),
                    "currency": price["currency"],
                },
            )
        if config.type in {"FORECAST_CHANGED", "MODEL_CONFIDENCE_CHANGED"}:
            assert iid
            prediction = await saved_production_forecast(
                self.db, self.user_id, iid, config.horizon, now
            )
            if not prediction:
                return Observation(None, {}, "NO_VALIDATED_PRODUCTION_FORECAST")
            key = (
                "probability_outperform"
                if config.type == "FORECAST_CHANGED"
                else "empirical_coverage"
            )
            value = prediction.result.get(key)
            return Observation(
                D(str(value)) if value is not None else None,
                {
                    "prediction_id": str(prediction.id),
                    "model_versions": prediction.result.get("model_versions", []),
                    "metric": key,
                },
                None if value is not None else "CONFIDENCE_METRIC_UNAVAILABLE",
            )
        if config.type in {"RISK_INCREASED", "CONCENTRATION_INCREASED"}:
            assert pid
            risk = await self.db.scalar(
                select(RiskSnapshot)
                .where(
                    RiskSnapshot.user_id == self.user_id,
                    RiskSnapshot.portfolio_id == pid,
                    RiskSnapshot.created_at <= now,
                    RiskSnapshot.as_of <= now,
                )
                .order_by(RiskSnapshot.created_at.desc())
                .limit(1)
            )
            if not risk or risk.as_of < now - timedelta(hours=24):
                return Observation(None, {}, "CURRENT_RISK_UNAVAILABLE")
            current = await ToolRegistry(self.db, self.user_id).value(pid, now)
            if valuation_identity(current) != valuation_identity(risk.result["current_valuation"]):
                return Observation(None, {}, "RISK_SNAPSHOT_NO_LONGER_MATCHES_LEDGER_OR_MARKET")
            value = (
                risk.result["metrics"].get("annualized_volatility")
                if config.type == "RISK_INCREASED"
                else (risk.result["exposures"].get("concentration") or {}).get(
                    "largest_position_weight"
                )
            )
            return Observation(
                D(str(value)) if value is not None else None,
                {"risk_snapshot_id": str(risk.id), "hash": risk.content_hash},
                None if value is not None else "RISK_METRIC_UNAVAILABLE",
            )
        if config.type == "FUNDAMENTAL_DETERIORATION":
            snapshot = await self.db.scalar(
                select(ResearchSnapshot)
                .where(
                    ResearchSnapshot.instrument_id == iid,
                    ResearchSnapshot.created_at <= now,
                    ResearchSnapshot.as_of <= now,
                )
                .order_by(ResearchSnapshot.created_at.desc())
                .limit(1)
            )
            if not snapshot or snapshot.as_of < now - timedelta(days=7):
                return Observation(None, {}, "CURRENT_RESEARCH_UNAVAILABLE")
            quality = cast(dict[str, Any], snapshot.result).get("scores", {}).get("Quality", {})
            value = quality.get("score") if quality.get("status") == "AVAILABLE" else None
            return Observation(
                D(str(value)) if value is not None else None,
                {
                    "research_snapshot_id": str(snapshot.id),
                    "hash": snapshot.input_hash,
                    "metric": "Quality",
                },
                None if value is not None else "FUNDAMENTAL_SCORE_UNAVAILABLE",
            )
        if config.type == "EARNINGS_UPCOMING":
            assert iid
            events = await FinancialEventService(self.db, self.user_id).available(now, iid)
            permitted = []
            for event in events:
                source = await self.db.get(DataSource, event.source_id)
                try:
                    if not source:
                        continue
                    SourceGate.require_enabled(source, "CALENDAR_EVENTS")
                except AppError:
                    continue
                if event.event_at >= now:
                    permitted.append(event)
            if not permitted:
                return Observation(None, {}, "NO_VERIFIED_UPCOMING_EVENT_SCHEDULE")
            event = min(permitted, key=lambda e: e.event_at)
            refs = {
                "event_id": str(event.id),
                "raw_ingestion_id": str(event.raw_ingestion_id),
                "event_at": event.event_at.isoformat(),
                "status": event.status,
                "data_context": event.evidence["data_context"],
            }
            if event.status == "CANCELLED":
                return Observation(None, refs, confirmed_false=True)
            return Observation(D(str((event.event_at - now).total_seconds())) / 86400, refs)
        if config.type == "NEGATIVE_NEWS":
            rows = (
                await self.db.scalars(
                    select(NewsArticle)
                    .join(NewsInstrument, NewsInstrument.article_id == NewsArticle.id)
                    .where(
                        NewsInstrument.instrument_id == iid,
                        NewsInstrument.mapping_status == "CONFIRMED",
                        NewsArticle.known_at <= now,
                        NewsArticle.observed_at <= now,
                        NewsArticle.created_at <= now,
                        NewsArticle.known_at >= now - timedelta(days=1),
                    )
                    .order_by(NewsArticle.known_at.desc())
                    .limit(30)
                )
            ).all()
            valid = []
            for row in rows:
                sentiment = row.sentiment
                if (
                    not sentiment
                    or sentiment.get("status") != "VALIDATED"
                    or not sentiment.get("model_version")
                    or not sentiment.get("classified_at")
                ):
                    continue
                try:
                    source = await self.db.get(DataSource, row.source_id)
                    if not source:
                        continue
                    SourceGate.require_enabled(source, "news")
                    classified = datetime.fromisoformat(str(sentiment["classified_at"]))
                    probability = D(str(sentiment["negative_probability"]))
                    if (
                        classified.tzinfo is None
                        or classified > now
                        or not probability.is_finite()
                        or not 0 <= probability <= 1
                    ):
                        continue
                    valid.append((row, probability))
                except (AppError, ValueError, KeyError):
                    continue
            if not valid:
                return Observation(None, {}, "VALIDATED_NEWS_SENTIMENT_UNAVAILABLE")
            row, value = max(valid, key=lambda item: item[1])
            return Observation(
                value,
                {
                    "article_id": str(row.id),
                    "raw_ingestion_id": str(row.raw_ingestion_id),
                    "sentiment_model": str(cast(dict[str, Any], row.sentiment)["model_version"]),
                },
            )
        return Observation(None, {}, "UNSUPPORTED_ALERT_TYPE")

    async def evaluate(self, identifier: UUID) -> AlertEvaluation | None:
        rule = await self.owned(identifier, lock=True)
        version = await self.latest(identifier)
        config = AlertRuleInput.model_validate(version.configuration)
        now = datetime.now(UTC)
        rule.last_checked_at = now
        if rule.archived or not config.enabled:
            await self.db.commit()
            return None
        observation = await self.observe(config, now)
        latest = await self.db.scalar(
            select(AlertEvaluation)
            .where(AlertEvaluation.rule_version_id == version.id)
            .order_by(AlertEvaluation.created_at.desc(), AlertEvaluation.id.desc())
            .limit(1)
        )
        previous = await self.db.scalar(
            select(AlertEvaluation)
            .where(
                AlertEvaluation.rule_version_id == version.id,
                AlertEvaluation.status.in_(["AVAILABLE", "BASELINE_RECORDED"]),
            )
            .order_by(AlertEvaluation.created_at.desc(), AlertEvaluation.id.desc())
            .limit(1)
        )
        previous_value = (
            D(str(previous.result["value"]))
            if previous and previous.result.get("value") is not None
            else None
        )
        last_event = await self.db.scalar(
            select(AlertEvent)
            .where(AlertEvent.rule_id == identifier)
            .order_by(AlertEvent.created_at.desc())
            .limit(1)
        )
        calculated = transition(
            config,
            observation,
            previous_value,
            previous.state if previous else None,
            last_event.created_at if last_event else None,
            now,
        )
        identity = {
            "rule_version": str(version.id),
            "inputs": observation.inputs,
            "reason": observation.reason,
            "value": str(observation.value) if observation.value is not None else None,
            "confirmed_false": observation.confirmed_false,
        }
        if config.type == "EARNINGS_UPCOMING":
            identity["value"] = None
            identity["within_window"] = calculated["state"]
        content = digest(identity)
        if latest and latest.input_hash == content:
            await self.db.commit()
            return latest
        row = AlertEvaluation(
            user_id=self.user_id,
            rule_id=rule.id,
            rule_version_id=version.id,
            evaluated_at=now,
            input_hash=content,
            status=calculated["status"],
            state=calculated["state"],
            result={
                **calculated,
                "value": str(observation.value) if observation.value is not None else None,
                "inputs": observation.inputs,
                "rule_engine_version": ALERT_VERSION,
                "configuration": version.configuration,
            },
            created_at=now,
        )
        self.db.add(row)
        await self.db.flush()
        if calculated["trigger"]:
            fingerprint = digest(
                {
                    "rule": str(rule.id),
                    "version": str(version.id),
                    "input_hash": content,
                    "previous_evaluation": str(previous.id) if previous else None,
                }
            )
            event = AlertEvent(
                user_id=self.user_id,
                rule_id=rule.id,
                evaluation_id=row.id,
                fingerprint=fingerprint,
                result={
                    "type": config.type,
                    "name": config.name,
                    "observation": row.result,
                    "notice": "DATA_ALERT_NOT_AN_INVESTMENT_RECOMMENDATION",
                },
                created_at=now,
            )
            self.db.add(event)
            await self.db.flush()
            self.db.add(
                Notification(
                    user_id=self.user_id,
                    dedup_key="alert:" + fingerprint,
                    payload={
                        "type": "ALERT",
                        "event_id": str(event.id),
                        "title": config.name,
                        "url": "/alerts",
                    },
                    created_at=now,
                )
            )
        await self.db.commit()
        return row
