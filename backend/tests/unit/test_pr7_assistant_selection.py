import asyncio
import json
from copy import deepcopy

import httpx
import pytest

from app.assistant.runtime import OllamaProvider, selection_context
from app.core.errors import AppError


def fact(identifier="a" * 64):
    return {
        "id": identifier,
        "label": "SYNTHETIC availability",
        "fact_type": "UNAVAILABLE",
        "value": "SYNTHETIC_PRIVATE_VALUE",
        "source_references": [{"original": "SYNTHETIC_PRIVATE_ORIGINAL"}],
    }


def test_compact_selection_never_sends_values_or_provenance_and_keeps_originals():
    facts = [fact(str(index).zfill(64)) for index in range(40)]
    original = deepcopy(facts)
    result = selection_context("SYNTHETIC question" * 1000, facts)
    body = json.dumps(result, ensure_ascii=False)
    assert len(body) <= 6000 and len(result["facts"]) <= 24
    assert "SYNTHETIC_PRIVATE" not in body and facts == original
    assert all(set(row) == {"id", "label", "fact_type"} for row in result["facts"])


@pytest.mark.parametrize("scenario", ["valid", "invented", "too_many", "unseen"])
def test_native_selector_enforces_the_requested_ids_and_budget(scenario):
    facts = [fact(), fact("b" * 64), fact("c" * 64)]
    if scenario == "unseen":
        facts = [fact(str(index).zfill(64)) for index in range(25)]

    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": "qwen3:0.6b", "digest": "d" * 64}]}
            )
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.40.11"})
        payload = json.loads(request.content)
        assert payload["format"]["properties"]["fact_ids"]["maxItems"] == 2
        assert "SYNTHETIC_PRIVATE" not in payload["messages"][1]["content"]
        chosen = [facts[0]["id"]]
        if scenario == "invented":
            chosen = ["invented"]
        if scenario == "too_many":
            chosen = [f["id"] for f in facts]
        if scenario == "unseen":
            chosen = [facts[-1]["id"]]
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps({"fact_ids": chosen, "explanation_keys": ["DATA_LIMITS"]})
                }
            },
        )

    async def run():
        provider = OllamaProvider(transport=httpx.MockTransport(handler))
        if scenario == "valid":
            selection, version = await provider.select("SYNTHETIC question", facts)
            assert selection.fact_ids == [facts[0]["id"]] and version.startswith("ollama/0.40.11:")
        else:
            with pytest.raises(AppError) as error:
                await provider.select("SYNTHETIC question", facts)
            assert error.value.code == "LLM_OUTPUT_REJECTED"

    asyncio.run(run())
