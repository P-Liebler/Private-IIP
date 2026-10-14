from copy import deepcopy
from datetime import date
from typing import cast
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import Instrument, ScenarioDefinition, ScenarioRun, WhatIfRun
from app.risk.scenarios import SCENARIOS, scenario
from app.risk.whatif import hypothetical
from app.schemas.risk import ScenarioInput, WhatIfInput
from app.services.fundamentals import digest
from app.services.pit_features import json_value
from app.services.portfolio_risk import PortfolioRiskService
from app.services.risk_market import RiskMarket


class RiskSimulationService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db, self.user_id = db, user_id

    async def scenario(self, portfolio_id: UUID, request: ScenarioInput) -> ScenarioRun:
        risk = await PortfolioRiskService(self.db, self.user_id).owned_snapshot(
            portfolio_id, request.risk_snapshot_id
        )
        config = request.model_dump(mode="json")
        definition = None
        if request.scenario_slug:
            definition = await self.db.scalar(
                select(ScenarioDefinition).where(ScenarioDefinition.slug == request.scenario_slug)
            )
            if definition is None:
                raise AppError(404, "SCENARIO_NOT_FOUND", "Versioned scenario not found")
            # Definitions pin the hypothesis. Only explicit mapping evidence is user supplied.
            config = {
                **definition.configuration,
                "benchmark_id": str(request.benchmark_id) if request.benchmark_id else None,
                "benchmark_mapping_confirmed": request.benchmark_mapping_confirmed,
            }
        result = scenario(risk.result, config)
        row = ScenarioRun(
            user_id=self.user_id,
            portfolio_id=portfolio_id,
            risk_snapshot_id=risk.id,
            scenario_id=definition.id if definition else None,
            configuration=config,
            result=result,
            content_hash=digest(
                {"risk_hash": risk.content_hash, "configuration": config, "result": result}
            ),
        )
        self.db.add(row)
        await self.db.commit()
        return row

    async def whatif(self, portfolio_id: UUID, request: WhatIfInput) -> WhatIfRun:
        risk = await PortfolioRiskService(self.db, self.user_id).owned_snapshot(
            portfolio_id, request.risk_snapshot_id
        )
        if not await self.db.scalar(text("SELECT pg_try_advisory_xact_lock(608641)")):
            raise AppError(409, "WHATIF_RESOURCE_LIMIT", "Another simulation is active")
        source = deepcopy(risk.result)
        quotes = {str(h["instrument_id"]): h for h in source["current_valuation"]["holdings"]}
        if (
            len(set(quotes) | {str(t.instrument_id) for t in request.trades})
            > get_settings().p8_max_instruments
        ):
            raise AppError(422, "WHATIF_RESOURCE_LIMIT", "Too many hypothetical instruments")
        market = RiskMarket(
            self.db, date.fromisoformat(risk.configuration["start"]), risk.as_of.date(), risk.as_of
        )
        for trade in request.trades:
            iid = str(trade.instrument_id)
            instrument = await self.db.get(Instrument, trade.instrument_id)
            if (
                instrument is None
                or not instrument.active
                or instrument.delisted_at is not None
                and instrument.delisted_at <= risk.as_of.date()
                or instrument.updated_at > risk.as_of
                or instrument.asset_type not in {"STOCK", "ETF"}
            ):
                raise AppError(
                    422,
                    "WHATIF_INSTRUMENT_INVALID",
                    "Known supported instrument required at snapshot cutoff",
                )
            if iid in quotes:
                continue
            rows = cast(
                list[dict[str, object]],
                (await market.prices(trade.instrument_id, market.start, market.end))["prices"],
            )
            price = rows[-1] if rows else None
            fx = await market.fx(
                instrument.currency, source["current_valuation"]["base_currency"], risk.as_of.date()
            )
            if (
                price is None
                or (risk.as_of.date() - cast(date, price["date"])).days > 7
                or fx["status"] != "AVAILABLE"
            ):
                raise AppError(422, "WHATIF_QUOTE_UNAVAILABLE", "Current price and FX required")
            quotes[iid] = {
                "instrument_id": iid,
                "name": instrument.name,
                "currency": instrument.currency,
                "price": str(price["close"]),
                "price_date": str(price["date"]),
                "price_version_id": str(price["id"]),
                "raw_ingestion_id": str(price["raw_ingestion_id"]),
                "price_source_id": str(price["source_id"]),
                "known_at": str(price["known_at"]),
                "observed_at": str(price["observed_at"]),
                "fx": json_value(fx),
                "valuation_status": "CURRENT",
                "sector": instrument.sector,
                "country": instrument.country,
                "industry": instrument.industry,
            }
            dates = [date.fromisoformat(o["date"]) for o in source["return_observations"]]
            returns = await market.total_returns(
                trade.instrument_id, source["current_valuation"]["base_currency"], dates
            )
            source["asset_returns"][iid] = json_value(returns["returns"])
        config = request.model_dump(mode="json")
        result = hypothetical(source, config, quotes)
        result["scenarios"] = {
            slug: {"before": scenario(source, mapped), "after": scenario(result, mapped)}
            for slug, _, definition in SCENARIOS
            for mapped in [
                {
                    **definition,
                    "benchmark_id": config["scenario_benchmark_mappings"].get(
                        definition.get("market")
                    ),
                    "benchmark_mapping_confirmed": definition.get("market")
                    in config["scenario_benchmark_mappings"],
                }
            ]
        }
        result["additional_market_versions"] = {k: sorted(v) for k, v in market.versions.items()}
        row = WhatIfRun(
            user_id=self.user_id,
            portfolio_id=portfolio_id,
            risk_snapshot_id=risk.id,
            configuration=config,
            result=result,
            content_hash=digest(
                {"risk_hash": risk.content_hash, "configuration": config, "result": result}
            ),
        )
        self.db.add(row)
        await self.db.commit()
        return row
