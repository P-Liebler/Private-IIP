from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.tools import ToolRegistry, evidence
from app.core.errors import AppError
from app.models import (
    DailyBrief,
    DailyBriefConfig,
    DataSource,
    MacroObservation,
    Notification,
    RiskSnapshot,
    User,
)
from app.recommendations.portfolio_context import valuation_identity
from app.schemas.assistant import BriefConfigInput, EvidenceFact, ToolInput
from app.services.financial_events import FinancialEventService
from app.services.fundamentals import digest
from app.services.market_calendar import MarketCalendarService
from app.services.portfolios import PortfolioService
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate

BRIEF_VERSION = "structured-daily-brief-v1"


def scheduled_utc(day: date, local_time: str, timezone: str) -> datetime:
    zone = ZoneInfo(timezone)
    hour, minute = map(int, local_time.split(":"))
    local = datetime.combine(day, time(hour, minute), zone).replace(fold=0)
    # Missing spring hour rolls forward; ambiguous autumn hour uses first fold.
    normalized = local.astimezone(UTC).astimezone(zone)
    return normalized.astimezone(UTC)


def due_period(now: datetime, config: BriefConfigInput) -> tuple[date, datetime]:
    local_day = now.astimezone(ZoneInfo(config.timezone)).date()
    scheduled = scheduled_utc(local_day, config.local_time, config.timezone)
    if scheduled > now:
        local_day -= timedelta(days=1)
        scheduled = scheduled_utc(local_day, config.local_time, config.timezone)
    return local_day, scheduled


def fact_key(fact: dict[str, Any]) -> str:
    refs = fact.get("source_references", [])
    scopes = sorted({str(r.get("url", "")) for r in refs})
    return str(fact["label"]) + "|" + "|".join(scopes)


class DailyBriefService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db, self.user_id = db, user_id

    async def configuration(self) -> BriefConfigInput:
        row = await self.db.get(DailyBriefConfig, self.user_id)
        user = await self.db.get(User, self.user_id)
        assert user
        return (
            BriefConfigInput(enabled=row.enabled, local_time=row.local_time, timezone=row.timezone)
            if row
            else BriefConfigInput(timezone=user.timezone)
        )

    async def configure(self, request: BriefConfigInput) -> DailyBriefConfig:
        row = await self.db.get(DailyBriefConfig, self.user_id)
        if not row:
            row = DailyBriefConfig(user_id=self.user_id)
            self.db.add(row)
        row.enabled, row.local_time, row.timezone = (
            request.enabled,
            request.local_time,
            request.timezone,
        )
        row.updated_at = datetime.now(UTC)
        await self.db.commit()
        return row

    async def owned(self, identifier: UUID) -> DailyBrief:
        row = await self.db.get(DailyBrief, identifier)
        if not row or row.user_id != self.user_id:
            raise AppError(404, "BRIEF_NOT_FOUND", "Daily brief not found")
        return row

    async def generate(self, now: datetime | None = None) -> DailyBrief:
        now = now or datetime.now(UTC)
        config = await self.configuration()
        local_day, nominal = due_period(now, config)
        # User lock serializes manual generation with scheduler/restart recovery.
        await self.db.get(User, self.user_id, with_for_update=True)
        existing = await self.db.scalar(
            select(DailyBrief).where(
                DailyBrief.user_id == self.user_id, DailyBrief.local_date == local_day
            )
        )
        if existing:
            return existing
        previous = await self.db.scalar(
            select(DailyBrief)
            .where(DailyBrief.user_id == self.user_id)
            .order_by(DailyBrief.period_end.desc())
            .limit(1)
        )
        start = (
            previous.period_end
            if previous and previous.period_end < now
            else scheduled_utc(local_day - timedelta(days=1), config.local_time, config.timezone)
        )
        start = max(start, now - timedelta(hours=48))
        portfolios = await PortfolioService(self.db, self.user_id).portfolios()
        facts: list[EvidenceFact] = []
        scopes = []
        registry = ToolRegistry(self.db, self.user_id)
        for portfolio in portfolios[:10]:
            scopes.append(str(portfolio.id))
            for tool in ("getPortfolio", "getRisk", "getDataQuality", "getRecommendation"):
                facts.extend(
                    await registry.call(ToolInput(name=tool, portfolio_id=portfolio.id, as_of=now))
                )
            risk = await self.db.scalar(
                select(RiskSnapshot)
                .where(
                    RiskSnapshot.portfolio_id == portfolio.id,
                    RiskSnapshot.user_id == self.user_id,
                    RiskSnapshot.created_at <= now,
                    RiskSnapshot.as_of <= now,
                )
                .order_by(RiskSnapshot.created_at.desc())
                .limit(1)
            )
            value = await registry.value(portfolio.id, now)
            returns = []
            if (
                risk
                and risk.result["quality"].get("complete_return_series")
                and risk.as_of >= now - timedelta(hours=24)
                and valuation_identity(value)
                == valuation_identity(risk.result["current_valuation"])
            ):
                exchange = risk.result["quality"].get("reference_exchange")
                if exchange:
                    calendar = MarketCalendarService()
                    for observation in risk.result["return_observations"]:
                        day = date.fromisoformat(observation["date"])
                        if (
                            observation.get("return") is not None
                            and calendar.is_session(exchange, day)
                            and start < calendar.session_close(exchange, day) <= now
                        ):
                            returns.append(Decimal(str(observation["return"])))
            performance = None
            if returns:
                wealth = Decimal(1)
                for daily_return in returns:
                    wealth *= 1 + daily_return
                performance = str(wealth - 1)
            facts.append(
                evidence(
                    "Validierte Portfolio-Performance im Berichtsfenster",
                    performance,
                    "DERIVED_METRIC" if performance is not None else "UNAVAILABLE",
                    now,
                    [{"risk_snapshot_id": str(risk.id), "url": f"/portfolios/{portfolio.id}"}]
                    if risk
                    else [],
                    "fraction",
                    None
                    if performance is not None
                    else "Keine vollständige validierte Renditekette für dieses Fenster verfügbar.",
                )
            )
            for holding in value["holdings"][:10]:
                iid = UUID(str(holding["instrument_id"]))
                facts.extend(
                    await registry.call(ToolInput(name="getNews", instrument_id=iid, as_of=now))
                )
                facts.extend(
                    await registry.call(ToolInput(name="getForecast", instrument_id=iid, as_of=now))
                )
                events = await FinancialEventService(self.db, self.user_id).available(now, iid)
                upcoming = [
                    event
                    for event in events
                    if event.status == "SCHEDULED"
                    and now <= event.event_at <= now + timedelta(days=7)
                ]
                facts.append(
                    evidence(
                        "Belegte bevorstehende Termine",
                        [
                            {"id": str(e.id), "event_at": e.event_at, "provenance": e.evidence}
                            for e in upcoming
                        ],
                        "VERIFIED_FACT" if upcoming else "UNAVAILABLE",
                        now,
                        [
                            {
                                "event_id": str(e.id),
                                "raw_ingestion_id": str(e.raw_ingestion_id),
                                "url": "/alerts",
                            }
                            for e in upcoming
                        ],
                        limitation=None
                        if upcoming
                        else "Keine freigegebene Terminquelle für diese Position verfügbar.",
                    )
                )
        macros = (
            await self.db.scalars(
                select(MacroObservation)
                .where(
                    MacroObservation.known_at >= start,
                    MacroObservation.known_at <= now,
                    MacroObservation.observed_at <= now,
                    MacroObservation.created_at <= now,
                )
                .order_by(MacroObservation.known_at.desc())
                .limit(10)
            )
        ).all()
        verified_macros = []
        for macro in macros:
            source = await self.db.get(DataSource, macro.source_id)
            try:
                if not source:
                    continue
                SourceGate.require_enabled(source, "macro")
                await RawIngestionService(self.db).get_verified(macro.raw_ingestion_id)
            except AppError:
                continue
            verified_macros.append(macro)
        macros = verified_macros
        facts.append(
            evidence(
                "Archivierte Makro-Beobachtungen im Berichtsfenster",
                [
                    {
                        "series": m.series,
                        "value": m.value,
                        "unit": m.unit,
                        "observation_date": m.observation_date,
                    }
                    for m in macros
                ],
                "VERIFIED_FACT" if macros else "UNAVAILABLE",
                now,
                [
                    {
                        "macro_id": str(m.id),
                        "raw_ingestion_id": str(m.raw_ingestion_id),
                        "url": "/backtests",
                    }
                    for m in macros
                ],
                limitation=None
                if macros
                else "Keine verifizierbaren neuen Makro-Beobachtungen verfügbar.",
            )
        )
        changes = []
        if previous:
            prior = {fact_key(f): f for f in previous.result.get("facts", [])}
            for fact in facts:
                key = fact_key(fact.model_dump(mode="json"))
                old = prior.get(key)
                if (
                    old
                    and old["fact_type"] != "UNAVAILABLE"
                    and fact.fact_type != "UNAVAILABLE"
                    and old["value"] != fact.model_dump(mode="json")["value"]
                ):
                    changes.append(
                        {
                            "label": fact.label,
                            "previous": old["value"],
                            "current": fact.model_dump(mode="json")["value"],
                            "source_references": fact.source_references,
                        }
                    )
        result = {
            "rule_version": BRIEF_VERSION,
            "status": "AVAILABLE_WITH_LIMITATIONS"
            if any(f.fact_type == "UNAVAILABLE" for f in facts)
            else "AVAILABLE",
            "facts": [f.model_dump(mode="json") for f in facts],
            "validated_changes": changes,
            "change_status": "COMPARED_ARCHIVED_REPORTS" if previous else "NO_PRIOR_BRIEF_BASELINE",
            "portfolio_ids": scopes,
            "scope_truncated": len(portfolios) > 10,
            "model_required": False,
            "notice": "NO_INVENTED_CHANGES_NO_INVESTMENT_RECOMMENDATIONS",
            "nominal_scheduled_at": nominal.isoformat(),
        }
        row = DailyBrief(
            user_id=self.user_id,
            local_date=local_day,
            period_start=start,
            period_end=now,
            configuration=config.model_dump(mode="json"),
            result=result,
            content_hash=digest(result),
            created_at=now,
        )
        self.db.add(row)
        await self.db.flush()
        self.db.add(
            Notification(
                user_id=self.user_id,
                dedup_key=f"brief:{local_day}",
                payload={
                    "type": "DAILY_BRIEF",
                    "brief_id": str(row.id),
                    "title": f"Daily Brief {local_day}",
                    "url": "/daily-brief",
                },
                created_at=now,
            )
        )
        await self.db.commit()
        return row
