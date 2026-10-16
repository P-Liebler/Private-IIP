from __future__ import annotations

from collections.abc import Awaitable
from typing import cast
from uuid import uuid4

from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.valkey import make_valkey_client
from app.models import DataSource

_SCRIPT = """
local t = redis.call('TIME')
local now = tonumber(t[1])*1000000+tonumber(t[2])
local day = math.floor(tonumber(t[1])/86400)
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now-60000000)
local count = redis.call('ZCARD', KEYS[1])
if count >= tonumber(ARGV[1]) then return {count+1,60} end
redis.call('ZREMRANGEBYSCORE', KEYS[3], '-inf', now-86400000000)
if redis.call('ZCARD', KEYS[3]) >= tonumber(ARGV[4]) then
  return {tonumber(ARGV[1])+1,86400}
end
if redis.call('HGET', KEYS[2], 'day') ~= tostring(day) then
  redis.call('HSET', KEYS[2], 'day', day, 'count', 0)
end
if tonumber(redis.call('HGET', KEYS[2], 'count') or '0') >= tonumber(ARGV[2]) then
  return {tonumber(ARGV[1])+1,86400-(tonumber(t[1])%86400)}
end
redis.call('HINCRBY', KEYS[2], 'count', 1)
redis.call('EXPIRE', KEYS[2], 172800)
redis.call('ZADD', KEYS[1], now, ARGV[3])
redis.call('ZADD', KEYS[3], now, ARGV[3])
redis.call('EXPIRE', KEYS[3], 86401)
redis.call('EXPIRE', KEYS[1], 61)
return {count+1,60}
"""


async def check_provider_rate(source: DataSource) -> None:
    if source.rate_limit_per_minute is None or source.rate_limit_per_minute < 1:
        raise AppError(503, "SOURCE_RATE_UNCONFIGURED", "Source rate limit is not configured")
    client = make_valkey_client()
    limit = min(source.rate_limit_per_minute, 25 if source.slug == "OPENFIGI" else 300)
    try:
        count, ttl = await cast(
            Awaitable[list[int]],
            client.eval(
                _SCRIPT,
                3,
                f"provider:rate:{source.slug}",
                "provider:daily:test"
                if source.slug.startswith("TEST_")
                else "provider:daily:global",
                f"provider:daily:{source.slug}",
                str(limit),
                str(get_settings().max_daily_provider_requests),
                uuid4().hex,
                "25" if source.slug == "ALPHAVANTAGE" else "10000",
            ),
        )
    except RedisError as error:
        raise AppError(
            503, "SOURCE_RATE_UNAVAILABLE", "Source rate limiter is unavailable"
        ) from error
    finally:
        await client.aclose()
    if count > limit:
        raise AppError(
            429, "SOURCE_RATE_LIMITED", "Source rate limit reached", retry_after=max(ttl, 1)
        )
