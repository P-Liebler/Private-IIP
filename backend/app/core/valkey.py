from __future__ import annotations

from typing import cast

from redis.asyncio import Redis

from app.core.config import get_settings


def make_valkey_client() -> Redis:
    return cast(
        Redis,
        Redis.from_url(get_settings().valkey_url, socket_connect_timeout=2, socket_timeout=2),
    )


async def check_valkey() -> None:
    client = make_valkey_client()
    try:
        await client.ping()
    finally:
        await client.aclose()
