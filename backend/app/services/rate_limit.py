from __future__ import annotations

import hashlib
from collections.abc import Awaitable
from typing import cast

from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.valkey import make_valkey_client

_INCREMENT_WITH_EXPIRY = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('TTL', KEYS[1])}
"""


def _key(kind: str, identifier: str) -> str:
    digest = hashlib.sha256(identifier.encode()).hexdigest()
    return f"auth:{kind}:{digest}"


class RateLimiter:
    async def _check(self, kind: str, identifier: str) -> None:
        settings = get_settings()
        client = make_valkey_client()
        try:
            raw = await cast(
                Awaitable[list[int]],
                client.eval(
                    _INCREMENT_WITH_EXPIRY,
                    1,
                    _key(kind, identifier),
                    str(settings.auth_login_window_seconds),
                ),
            )
            count, ttl = int(raw[0]), int(raw[1])
        except RedisError as error:
            raise AppError(
                503, "AUTH_UNAVAILABLE", "Authentication is temporarily unavailable"
            ) from error
        finally:
            await client.aclose()
        if count > settings.auth_login_max_attempts:
            raise AppError(429, "RATE_LIMITED", "Too many attempts", retry_after=max(ttl, 1))

    async def _clear(self, kind: str, identifier: str) -> None:
        client = make_valkey_client()
        try:
            await client.delete(_key(kind, identifier))
        except RedisError:
            # A successful login remains valid if only counter cleanup fails.
            pass
        finally:
            await client.aclose()

    async def check_login(self, ip_address: str, username: str) -> None:
        await self._check("login", f"{ip_address}|{username}")

    async def clear_login(self, ip_address: str, username: str) -> None:
        await self._clear("login", f"{ip_address}|{username}")

    async def check_totp(self, ip_address: str) -> None:
        await self._check("totp", ip_address)

    async def clear_totp(self, ip_address: str) -> None:
        await self._clear("totp", ip_address)


rate_limiter = RateLimiter()
