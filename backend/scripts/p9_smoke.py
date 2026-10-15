"""Explicit local synthetic acceptance fixture; safe to run with MLflow stopped."""

import asyncio
import os
from decimal import Decimal

import httpx


async def main() -> None:
    portfolio = os.environ["E2E_PORTFOLIO_ID"]
    instrument = os.environ["E2E_RESEARCH_INSTRUMENT_ID"]
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=120) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"username": os.environ["E2E_USERNAME"], "password": os.environ["E2E_PASSWORD"]},
        )
        assert login.status_code == 200
        value = await client.get(f"/api/v1/portfolios/{portfolio}/valuation")
        assert value.status_code == 200 and value.json()["status"] == "COMPLETE"
        assert Decimal(value.json()["total_value_base"]) == Decimal("10180")
        ledger = (await client.get(f"/api/v1/portfolios/{portfolio}/transactions")).json()
        assert (await client.get(f"/api/v1/research/instruments/{instrument}")).status_code == 200
        risk = await client.get(f"/api/v1/portfolios/{portfolio}/risk")
        assert risk.status_code == 200 and risk.json().get("id")
        result = await client.post(
            "/api/v1/recommendations/evaluate",
            json={
                "portfolio_id": portfolio,
                "risk_snapshot_id": risk.json()["id"],
                "instrument_ids": [instrument],
            },
        )
        assert result.status_code == 200, result.text
        assert result.json() and all(
            row["category"] in ("INSUFFICIENT_DATA", "INELIGIBLE") for row in result.json()
        )
        assert all(
            "NO_VALIDATED_PRODUCTION_FORECAST" in row["eligibility"]["missing_inputs"]
            for row in result.json()
        )
        assert (await client.get(f"/api/v1/portfolios/{portfolio}/transactions")).json() == ledger
        metrics = await client.get("/internal/metrics")
        assert (
            metrics.status_code == 200
            and "private_iip_recommendation_abstentions_total" in metrics.text
        )
    print(
        "P9 local outage smoke PASSED: portfolio 10180, research/risk, "
        "gated recommendations, unchanged ledger, aggregate metrics"
    )


if __name__ == "__main__":
    asyncio.run(main())
