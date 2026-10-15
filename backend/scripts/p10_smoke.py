"""Local authenticated outage smoke against explicit fixtures; no live finance calls."""

import asyncio
import json
import os

import httpx


async def main() -> None:
    base = "http://127.0.0.1:8000/api/v1"
    async with httpx.AsyncClient(
        base_url=base, headers={"Origin": "http://localhost:3000"}, timeout=120
    ) as client:
        login = await client.post(
            "/auth/login",
            json={"username": os.environ["E2E_USERNAME"], "password": os.environ["E2E_PASSWORD"]},
        )
        assert login.status_code == 200
        pid = os.environ["E2E_PORTFOLIO_ID"]
        iid = os.environ["E2E_RESEARCH_INSTRUMENT_ID"]
        before = (await client.get(f"/portfolios/{pid}/transactions")).json()
        value = await client.get(f"/portfolios/{pid}/valuation")
        assert value.status_code == 200 and float(value.json()["total_value_base"]) == 10180
        runtime = (await client.get("/assistant/status")).json()
        if os.environ.get("EXPECT_LLM_DOWN"):
            assert runtime["status"] == "LLM_UNAVAILABLE"
        conv = (
            await client.post("/assistant/conversations", json={"title": "SYNTHETIC outage smoke"})
        ).json()["id"]
        result = await client.post(
            f"/assistant/conversations/{conv}/messages",
            json={"question": "Empfehlung kaufen?", "portfolio_id": pid, "instrument_id": iid},
        )
        assert result.status_code == 200 and '"type": "done"' in result.text
        assert "NO_VALIDATED_PRODUCTION_FORECAST" in result.text
        if os.environ.get("EXPECT_LLM_DOWN"):
            assert "LLM_UNAVAILABLE" in result.text
        brief = await client.post("/daily-brief/generate")
        assert brief.status_code == 200 and brief.json()["result"]["model_required"] is False
        history = await client.post(
            "/time-machine", json={"as_of": "2020-01-01T12:00:00Z", "instrument_id": iid}
        )
        assert history.status_code == 200 and "NO HISTORICAL PREDICTION" in history.text
        docs = (await client.get("/research-documents")).json()
        assert docs
        original = await client.get(f"/research-documents/{docs[0]['id']}/original")
        if os.environ.get("EXPECT_RAW_DOWN"):
            assert original.status_code == 503, original.text[:100]
        else:
            assert original.status_code == 200 and original.content.startswith(b"%PDF-")
        assert (await client.get(f"/portfolios/{pid}/transactions")).json() == before
        print(
            json.dumps(
                {
                    "portfolio_value": 10180,
                    "runtime": runtime["status"],
                    "brief_without_llm": True,
                    "historical_prediction_not_backcast": True,
                    "ledger_unchanged": True,
                    "raw_response": original.status_code,
                    "assistant_verified_response": True,
                }
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
