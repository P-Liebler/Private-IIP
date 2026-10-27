"""Explicit local CPU warmup; not a cold-response or financial-model acceptance."""
import asyncio
import json
import time

from app.assistant.runtime import OllamaProvider
from app.core.config import get_settings


async def main():
    settings = get_settings()
    assert settings.app_env == "staging" and not settings.assistant_test_mode
    provider = OllamaProvider()
    version = await provider.version(settings.ollama_chat_model)
    assert version.startswith("ollama/0.40.11:")
    started = time.monotonic()
    result = await provider.request("/api/chat", {
        "model": settings.ollama_chat_model, "messages": [], "keep_alive": "10m",
        "options": {"num_ctx": settings.assistant_context_tokens, "num_thread": 2},
    })
    assert result.get("done") is True
    print(json.dumps({"status": "EXPLICIT_LOCAL_CPU_PRELOAD", "model_version": version,
        "preload_ms": (time.monotonic() - started) * 1000, "cold_response_acceptance": False}))


if __name__ == "__main__":
    asyncio.run(main())
