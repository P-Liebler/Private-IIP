import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.models import PriceDailyVersion
from app.services.market_queries import MarketQueryService


def test_price_chart_marks_missing_closed_sessions_but_not_weekends_or_open_session():
    async def run(exchange):
        rows = [
            PriceDailyVersion(
                id=uuid4(),
                trading_date=day,
                close=Decimal("100"),
                source_id=uuid4(),
                raw_ingestion_id=uuid4(),
                known_at=datetime(2026, 10, 21, tzinfo=UTC),
                resolution="ACCEPTED",
            )
            for day in (date(2026, 10, 16), date(2026, 10, 20))
        ]

        class DB:
            async def scalars(self, statement):
                return SimpleNamespace(all=lambda: rows)

            async def get(self, model, identifier):
                return SimpleNamespace(mic=exchange, exchange=exchange)

        return await MarketQueryService(DB()).prices(
            uuid4(), date(2026, 10, 16), date(2026, 10, 23), datetime(2026, 10, 23, 10, tzinfo=UTC)
        )

    result = asyncio.run(run("XSWX"))
    assert result["calendar_status"] == "AVAILABLE"
    series = {row["date"]: row["value"] for row in result["chart_series"]}
    assert series[date(2026, 10, 19)] is None
    assert series[date(2026, 10, 20)] == Decimal("100")
    assert date(2026, 10, 17) not in series
    assert date(2026, 10, 18) not in series
    assert date(2026, 10, 23) not in series  # session has not closed at the cutoff
    unknown = asyncio.run(run("UNSUPPORTED"))
    assert unknown["calendar_status"] == "UNAVAILABLE"
    assert len(unknown["chart_series"]) == 2
