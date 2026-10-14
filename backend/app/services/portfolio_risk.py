import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import (
    Benchmark,
    Instrument,
    RawIngestion,
    ResearchSnapshot,
    RiskSnapshot,
    Transaction,
)
from app.risk.exposure import exposures, health, liquidity_score
from app.risk.statistics import RISK_VERSION, correlations, risk_metrics
from app.schemas.risk import RiskInput
from app.services.fundamentals import digest
from app.services.market_queries import pit_cutoff
from app.services.pit_evidence import ENTITIES
from app.services.pit_features import json_value
from app.services.portfolio_engine import ledger_state
from app.services.portfolio_performance import PortfolioPerformanceService, twr_period
from app.services.portfolio_snapshots import PortfolioSnapshotService
from app.services.portfolio_valuation import PortfolioValuationService
from app.services.portfolios import PortfolioService
from app.services.risk_market import RiskMarket


class PortfolioRiskService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db, self.user_id = db, user_id

    async def owned_snapshot(self, portfolio_id: UUID, snapshot_id: UUID) -> RiskSnapshot:
        await PortfolioService(self.db, self.user_id).owned(portfolio_id)
        snapshot = await self.db.get(RiskSnapshot, snapshot_id)
        if (
            snapshot is None
            or snapshot.user_id != self.user_id
            or snapshot.portfolio_id != portfolio_id
        ):
            raise AppError(404, "RISK_SNAPSHOT_NOT_FOUND", "Risk snapshot not found")
        return snapshot

    async def calculate(self, portfolio_id: UUID, config: RiskInput) -> RiskSnapshot:
        cutoff = pit_cutoff(config.as_of)
        if cutoff > datetime.now(UTC):
            raise AppError(
                422, "FUTURE_RISK_REJECTED", "Risk requires already available observations"
            )
        portfolio = await PortfolioService(self.db, self.user_id).owned(portfolio_id)
        snapshot = await PortfolioSnapshotService(self.db, self.user_id).rebuild(
            portfolio_id, cutoff.date(), cutoff
        )
        if not await self.db.scalar(text("SELECT pg_try_advisory_xact_lock(608640)")):
            raise AppError(409, "RISK_RESOURCE_LIMIT", "Another risk calculation is active")
        async with asyncio.timeout(get_settings().p8_timeout_seconds):
            end = cutoff.date()
            transactions = list(
                (
                    await self.db.scalars(
                        select(Transaction).where(Transaction.portfolio_id == portfolio_id)
                    )
                ).all()
            )
            visible = [
                t
                for t in transactions
                if t.created_at <= cutoff
                and (t.voided_at is None or t.voided_at > cutoff)
                and t.trade_date <= end
            ]
            first = min((t.trade_date for t in visible), default=end)
            start = max(end - timedelta(days=config.window * 3), first)
            state = ledger_state(transactions, start, cutoff)
            ids = {p.instrument_id for p in state.positions.values() if p.quantity} | {
                t.instrument_id for t in visible if t.instrument_id and t.trade_date >= start
            }
            portfolio_ids = set(ids)
            benchmark = (
                await self.db.get(Benchmark, config.benchmark_id or portfolio.benchmark_id)
                if config.benchmark_id or portfolio.benchmark_id
                else None
            )
            if benchmark:
                ids.add(benchmark.instrument_id)
            if len(ids) > get_settings().p8_max_instruments:
                raise AppError(422, "RISK_RESOURCE_LIMIT", "Too many instruments")
            instruments = {iid: await self.db.get(Instrument, iid) for iid in ids}
            market = RiskMarket(self.db, start, end, cutoff)
            valuation = PortfolioValuationService(self.db, self.user_id)
            valuation.market = market  # type: ignore[assignment]  # same P3 contract, cached for this run
            current = await valuation.value(portfolio_id, end, cutoff)
            for holding in cast(list[dict[str, Any]], current["holdings"]):
                instrument = instruments.get(holding["instrument_id"]) or await self.db.get(
                    Instrument, holding["instrument_id"]
                )
                if instrument:
                    holding["metadata_provenance"] = {
                        "instrument_id": str(instrument.id),
                        "observed_at": instrument.updated_at.isoformat(),
                        "quality": "USER_RECORDED_CLASSIFICATION",
                    }
                    for key in ("country", "sector", "industry"):
                        holding[key] = (
                            getattr(instrument, key) if instrument.updated_at <= cutoff else None
                        )
            calendar_missing = [
                str(iid)
                for iid in portfolio_ids
                if instruments[iid] is None or not cast(Instrument, instruments[iid]).exchange
            ]
            sessions: list[date] = []
            reference_exchange = None
            if not calendar_missing:
                reference_instrument = (
                    instruments.get(benchmark.instrument_id) if benchmark else None
                )
                reference_exchange = (
                    reference_instrument.exchange
                    if reference_instrument and reference_instrument.exchange
                    else next(
                        (
                            cast(Instrument, instruments[i]).exchange
                            for i in sorted(portfolio_ids)
                            if instruments[i]
                        ),
                        None,
                    )
                )
                if reference_exchange is None and not portfolio_ids:
                    reference_exchange = "NYSE" if portfolio.base_currency == "USD" else "SIX"
                try:
                    sessions = [
                        d
                        for d in market.calendar.sessions_between(
                            reference_exchange or "", start, end
                        )
                        if market.calendar.session_close(reference_exchange or "", d) <= cutoff
                        and all(
                            not market.calendar.is_session(
                                cast(Instrument, instruments[i]).exchange or "", d
                            )
                            or market.calendar.session_close(
                                cast(Instrument, instruments[i]).exchange or "", d
                            )
                            <= cutoff
                            for i in portfolio_ids
                            if instruments[i]
                        )
                    ][-(config.window + 1) :]
                except (ValueError, AppError):
                    calendar_missing = [str(iid) for iid in portfolio_ids] or ["REFERENCE_CALENDAR"]
            if sessions:
                market.start = min(
                    [sessions[0]]
                    + [
                        market.calendar.previous_session(
                            cast(Instrument, instruments[i]).exchange or "", sessions[0]
                        )
                        for i in portfolio_ids
                        if instruments[i]
                        and not market.calendar.is_session(
                            cast(Instrument, instruments[i]).exchange or "", sessions[0]
                        )
                    ]
                )
                market.end = sessions[-1]
            asset_results = {}
            for iid in sorted(ids):
                try:
                    asset_results[str(iid)] = await market.total_returns(
                        iid, portfolio.base_currency, sessions
                    )
                except (ValueError, AppError):
                    asset_results[str(iid)] = {"status": "CALENDAR_UNAVAILABLE", "returns": {}}
            asset_series = {iid: item["returns"] for iid, item in asset_results.items()}
            performance = PortfolioPerformanceService(self.db, self.user_id)
            performance.valuation = valuation
            prior_valuation = None
            fx_contribution = Decimal(0)
            fx_complete = bool(sessions)
            history: list[tuple[str, Decimal]] = []
            observations = []
            previous = None
            complete = bool(sessions)
            flow_events = ledger_state(transactions, end, cutoff).external_flows
            factor, interval_valid = Decimal(1), True
            if sessions:
                day = sessions[0]
                while day <= sessions[-1]:
                    value = await valuation.value(portfolio_id, day, cutoff)
                    valid = value["status"] == "COMPLETE"
                    for holding in cast(list[dict[str, Any]], value["holdings"]):
                        instrument = instruments.get(holding["instrument_id"])
                        if instrument is None or not instrument.exchange:
                            valid = False
                            continue
                        expected_day = (
                            day
                            if market.calendar.is_session(instrument.exchange, day)
                            else market.calendar.previous_session(instrument.exchange, day)
                        )
                        if holding["price_date"] != expected_day or not asset_results[
                            str(instrument.id)
                        ].get("coverage_id"):
                            valid = False
                    amount = cast(Decimal | None, value["total_value_base"]) if valid else None
                    flow, flow_valid = Decimal(0), True
                    for event_day, currency, event_amount in flow_events:
                        if event_day == day:
                            fx = await market.fx(currency, portfolio.base_currency, event_day)
                            if fx["status"] != "AVAILABLE":
                                flow_valid = False
                            else:
                                flow += event_amount * cast(Decimal, fx["rate"])
                    if prior_valuation is not None and previous is not None:
                        effect = await performance._opening_exposure_fx_effect(
                            prior_valuation, day, portfolio.base_currency, cutoff
                        )
                        if effect is None:
                            fx_complete = False
                        else:
                            fx_contribution += effect
                    elif day > sessions[0]:
                        fx_complete = False
                    daily: Decimal | None = (
                        twr_period(previous, amount, flow)
                        if previous is not None and amount is not None and flow_valid
                        else None
                    )
                    if day > sessions[0]:
                        if daily is None:
                            interval_valid, complete = False, False
                        else:
                            factor *= 1 + daily
                    realized = None
                    if day in sessions:
                        if day > sessions[0] and interval_valid:
                            realized = factor - 1
                            history.append((day.isoformat(), realized))
                        observations.append(
                            {
                                "date": day.isoformat(),
                                "value_base": str(amount) if amount is not None else None,
                                "return": str(realized) if realized is not None else None,
                                "status": "AVAILABLE"
                                if valid and interval_valid
                                else "DATA_UNAVAILABLE",
                            }
                        )
                        factor, interval_valid = Decimal(1), True
                    prior_valuation = value
                    previous = amount
                    day += timedelta(days=1)
            benchmark_returns = (
                asset_series.get(str(benchmark.instrument_id), {}) if benchmark else {}
            )
            metrics = risk_metrics(
                history, benchmark_returns, complete, sessions[0].isoformat() if sessions else None
            )
            total = cast(Decimal | None, current["total_value_base"])
            exposure = exposures(
                cast(list[dict[str, Any]], current["holdings"]),
                cast(list[dict[str, Any]], current["cash"]),
                total,
            )
            position_ids = {
                str(h["instrument_id"]) for h in cast(list[dict[str, Any]], current["holdings"])
            }
            position_beta = {
                iid: risk_metrics(
                    sorted(asset_series.get(iid, {}).items())[-config.window :],
                    benchmark_returns,
                    asset_results.get(iid, {}).get("status") == "AVAILABLE"
                    and len(asset_series.get(iid, {})) == max(0, len(sessions) - 1),
                )
                for iid in position_ids
            }
            matrices = {
                str(window): correlations(
                    {iid: asset_series.get(iid, {}) for iid in position_ids},
                    window,
                    [d.isoformat() for d in sessions[1:]],
                )
                for window in (30, 90, 252)
            }
            cash_fx_returns = {}
            for currency in {c["currency"] for c in cast(list[dict[str, Any]], current["cash"])}:
                values, previous_rate = {}, None
                for day in sessions:
                    fx = await market.fx(currency, portfolio.base_currency, day)
                    rate = cast(Decimal, fx["rate"]) if fx["status"] == "AVAILABLE" else None
                    if rate is not None and previous_rate is not None:
                        values[day.isoformat()] = rate / previous_rate - 1
                    previous_rate = rate
                cash_fx_returns[currency] = values
            quality_inputs, quality_sum, security_sum, quality_complete = (
                [],
                Decimal(0),
                Decimal(0),
                bool(position_ids),
            )
            for position_id in position_ids:
                research = await self.db.scalar(
                    select(ResearchSnapshot)
                    .where(
                        ResearchSnapshot.instrument_id == UUID(position_id),
                        ResearchSnapshot.as_of <= cutoff,
                        ResearchSnapshot.created_at <= cutoff,
                    )
                    .order_by(ResearchSnapshot.as_of.desc())
                    .limit(1)
                )
                score = (
                    cast(dict[str, Any], research.result.get("scores", {})).get("Quality", {})
                    if research and cutoff - research.as_of <= timedelta(days=7)
                    else {}
                )
                weight = sum(
                    (
                        Decimal(str(h["market_value_base"]))
                        for h in cast(list[dict[str, Any]], current["holdings"])
                        if str(h["instrument_id"]) == position_id
                        and h["market_value_base"] is not None
                    ),
                    Decimal(0),
                )
                security_sum += weight
                if score.get("status") != "AVAILABLE" or score.get("score") is None:
                    quality_complete = False
                else:
                    quality_sum += Decimal(str(score["score"])) * weight
                quality_inputs.append(
                    {
                        "instrument_id": position_id,
                        "research_snapshot_id": str(research.id) if research else None,
                        "input_hash": research.input_hash if research else None,
                        "weight_base": str(weight),
                        "quality": score,
                    }
                )
            quality = {
                "score": str(quality_sum / security_sum)
                if quality_complete and security_sum > 0
                else None,
                "inputs": quality_inputs,
                "policy": "COMPLETE_SECURITIES_WEIGHTED_P5_QUALITY_MAX_SNAPSHOT_AGE_7_DAYS",
            }
            liquidity_evidence = {}
            for position_id in position_ids:
                instrument = instruments.get(UUID(position_id))
                if instrument is None or not instrument.exchange:
                    continue
                try:
                    prices = [
                        p
                        for p in await market.load(instrument.id)
                        if market.calendar.is_session(instrument.exchange, cast(date, p["date"]))
                        and market.calendar.session_close(
                            instrument.exchange, cast(date, p["date"])
                        )
                        <= cutoff
                    ][-20:]
                    expected = (
                        market.calendar.sessions_between(
                            instrument.exchange,
                            cast(date, prices[0]["date"]),
                            cast(date, prices[-1]["date"]),
                        )
                        if prices
                        else []
                    )
                    actions, proof = (
                        await self._actions(
                            market,
                            instrument.id,
                            cast(date, prices[0]["date"]),
                            cast(date, prices[-1]["date"]),
                            cutoff,
                        )
                        if prices
                        else ([], None)
                    )
                    valid = (
                        len(prices) == 20
                        and [p["date"] for p in prices] == expected
                        and proof is not None
                        and not any(a["type"] == "SPLIT" for a in actions)
                        and all(
                            p.get("volume") is not None and Decimal(str(p["volume"])) > 0
                            for p in prices
                        )
                    )
                    liquidity_evidence[position_id] = {
                        "average_volume": str(
                            sum((Decimal(str(p["volume"])) for p in prices), Decimal(0)) / 20
                        )
                        if valid
                        else None,
                        "observations": len(prices),
                        "price_version_ids": [str(p["id"]) for p in prices],
                        "coverage_id": proof,
                        "quality": "EXACT_20_CLOSED_SESSIONS_SAME_SHARE_UNIT",
                    }
                except (ValueError, AppError):
                    liquidity_evidence[position_id] = {
                        "average_volume": None,
                        "reason": "CALENDAR_OR_COVERAGE_UNAVAILABLE",
                    }
            liquidity = (
                liquidity_score(cast(list[dict[str, Any]], current["holdings"]), liquidity_evidence)
                if total is not None
                else None
            )
            version_hashes: dict[str, dict[str, str]] = {}
            raw_ids: set[UUID] = set()
            for kind, pinned in market.versions.items():
                versions = (
                    (
                        await self.db.scalars(
                            select(ENTITIES[kind]).where(
                                ENTITIES[kind].id.in_([UUID(v) for v in pinned])
                            )
                        )
                    ).all()
                    if pinned
                    else []
                )
                version_hashes[kind] = {
                    str(v.id): digest(
                        json_value(
                            {column.name: getattr(v, column.name) for column in v.__table__.columns}
                        )
                    )
                    for v in versions
                }
                raw_ids.update(
                    v.raw_ingestion_id for v in versions if getattr(v, "raw_ingestion_id", None)
                )
            raw_hashes = (
                {
                    str(r.id): r.sha256
                    for r in (
                        await self.db.scalars(
                            select(RawIngestion).where(RawIngestion.id.in_(raw_ids))
                        )
                    ).all()
                }
                if raw_ids
                else {}
            )
            result = json_value(
                {
                    "risk_rule_version": RISK_VERSION,
                    "status": "AVAILABLE"
                    if metrics["status"] == "AVAILABLE" and exposure["status"] == "AVAILABLE"
                    else "PARTIAL",
                    "metrics": metrics,
                    "exposures": exposure,
                    "health": health(
                        exposure, metrics, quality, portfolio.base_currency, liquidity
                    ),
                    "security_quality": quality,
                    "liquidity_evidence": liquidity_evidence,
                    "cash_fx_returns": cash_fx_returns,
                    "fx_contribution": {
                        "value_base": str(fx_contribution) if complete and fx_complete else None,
                        "status": "AVAILABLE" if complete and fx_complete else "INSUFFICIENT_DATA",
                        "method": "P4_OPENING_EXPOSURE_DAILY_FX_TRANSLATION",
                    },
                    "correlations": matrices,
                    "position_beta": position_beta,
                    "benchmark": {
                        "benchmark_id": str(benchmark.id),
                        "instrument_id": str(benchmark.instrument_id),
                        "name": benchmark.name,
                    }
                    if benchmark
                    else None,
                    "current_valuation": current,
                    "return_observations": observations,
                    "asset_returns": asset_series,
                    "asset_quality": asset_results,
                    "quality": {
                        "calendar_missing": calendar_missing,
                        "reference_exchange": reference_exchange,
                        "expected_return_observations": max(0, len(sessions) - 1),
                        "valid_return_observations": len(history),
                        "complete_return_series": complete,
                        "valuation_status": current["status"],
                    },
                    "returns_policy": "P4_DAILY_TWR_COMPOUNDED_REFERENCE_SESSIONS-v1",
                    "fx_policy": "P3_REFERENCE_DIRECT_INVERSE_CROSS_MAX_CARRY",
                    "calendar_version": market.calendar.version,
                    "warnings": [
                        "Historical risk estimates are not maximum-loss guarantees.",
                        "Economic currency exposure and liquidity require separate evidence.",
                    ],
                    "market_data_versions": {k: sorted(v) for k, v in market.versions.items()},
                    "market_version_hashes": version_hashes,
                    "raw_hashes": raw_hashes,
                    "historical_data_context": (
                        "EX_POST_LEDGER_CURRENT_KNOWLEDGE_NOT_ORIGINAL_PIT_ARCHIVE"
                    ),
                    "portfolio_snapshot_id": str(snapshot.id),
                }
            )
            configuration = {
                **config.model_dump(mode="json"),
                "as_of": cutoff.isoformat(),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "base_currency": portfolio.base_currency,
            }
            content = digest({"configuration": configuration, "result": result})
            existing = await self.db.scalar(
                select(RiskSnapshot).where(
                    RiskSnapshot.portfolio_id == portfolio_id, RiskSnapshot.content_hash == content
                )
            )
            if existing:
                return existing
            risk = RiskSnapshot(
                user_id=self.user_id,
                portfolio_id=portfolio_id,
                portfolio_snapshot_id=snapshot.id,
                as_of=cutoff,
                configuration=configuration,
                result=result,
                content_hash=content,
            )
            self.db.add(risk)
            await self.db.commit()
            return risk

    async def _actions(
        self, market: RiskMarket, instrument_id: UUID, start: date, end: date, cutoff: datetime
    ) -> tuple[list[dict[str, Any]], str | None]:
        from app.services.pit_features import FeatureSnapshotService

        actions, proof = await FeatureSnapshotService(self.db).actions(
            instrument_id, start, end, cutoff, "STRICT_PIT"
        )
        if proof:
            market.versions["coverage"].add(proof)
            market.versions["action"].update(a["id"] for a in actions)
        return actions, proof
