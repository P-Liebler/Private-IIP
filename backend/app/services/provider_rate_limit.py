from __future__ import annotations

from collections.abc import Awaitable
from typing import cast

from redis.exceptions import RedisError

from app.core.errors import AppError
from app.core.valkey import make_valkey_client
from app.models import DataSource

_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], 60) end
return {count, redis.call('TTL', KEYS[1])}
"""


async def check_provider_rate(source: DataSource) -> None:
    if source.rate_limit_per_minute is None or source.rate_limit_per_minute < 1:
        raise AppError(503, "SOURCE_RATE_UNCONFIGURED", "Source rate limit is not configured")
    client = make_valkey_client()
    try:
        count, ttl = await cast(
            Awaitable[list[int]], client.eval(_SCRIPT, 1, f"provider:rate:{source.slug}")
        )
    except RedisError as error:
        raise AppError(
            503, "SOURCE_RATE_UNAVAILABLE", "Source rate limiter is unavailable"
        ) from error
    finally:
        await client.aclose()
    if count > source.rate_limit_per_minute:
        raise AppError(
            429, "SOURCE_RATE_LIMITED", "Source rate limit reached", retry_after=max(ttl, 1)
        )
