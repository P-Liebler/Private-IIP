"""Read-only checks using an explicitly disposable local acceptance account."""

import asyncio
import json
import os
from decimal import Decimal

import httpx

from app.core.config import get_settings


async def main() -> None:
    username = os.environ.get("E2E_USERNAME", "")
    if get_settings().app_env not in {"local", "test"} or not username.startswith("restore_"):
        raise RuntimeError("Explicit local disposable account required")
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8000/api/v1",
        headers={"Origin": get_settings().frontend_origin},
        timeout=30,
    ) as client:
        login = await client.post(
            "/auth/login", json={"username": username, "password": os.environ["E2E_PASSWORD"]}
        )
        assert login.status_code == 200
        response = await client.get("/portfolios/" + os.environ["E2E_PORTFOLIO_ID"] + "/valuation")
        assert response.status_code == 200 and response.json()["status"] == "COMPLETE"
        assert Decimal(response.json()["total_value_base"]) == Decimal("10180")
        research = await client.get(
            "/research/instruments/" + os.environ["E2E_RESEARCH_INSTRUMENT_ID"]
        )
        assert research.status_code == 200
        risk = await client.get("/portfolios/" + os.environ["E2E_PORTFOLIO_ID"] + "/risk")
        assert risk.status_code == 200 and "result" in risk.json()
        assert risk.json()["result"]["exposures"]["status"] == "AVAILABLE"
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "portfolio_value": "10180",
                    "research_available": True,
                    "mlflow_required": False,
                    "risk_available": True,
                }
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
