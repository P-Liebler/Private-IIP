"""Bounded provider transport. DNS is resolved once, checked, then connected by IP.

TLS still verifies the original host. No proxy environment, redirects or decompression.
The httpcore backend extension uses the already pinned httpx/httpcore runtime.
"""

from __future__ import annotations

import asyncio
import ipaddress
import random
import socket
import ssl
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

import httpcore
import httpx
from httpcore._backends.anyio import AnyIOBackend
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import DataSource, RawIngestion
from app.services.provider_rate_limit import check_provider_rate
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate

MAX_BYTES = 16 * 1024 * 1024


async def public_addresses(host: str) -> list[str]:
    try:
        entries = await asyncio.wait_for(
            asyncio.to_thread(socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM), 5
        )
    except (OSError, TimeoutError):
        raise AppError(503, "SOURCE_UNAVAILABLE", "Provider DNS unavailable") from None
    addresses = list(dict.fromkeys(str(e[4][0]) for e in entries))
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise AppError(422, "SOURCE_ORIGIN_INVALID", "Public provider address required")
    return addresses


class PinnedBackend(AnyIOBackend):
    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Any = None,
    ) -> Any:
        if port != 443:
            raise AppError(422, "SOURCE_ORIGIN_INVALID", "HTTPS port required")
        addresses = await public_addresses(host)
        # Numeric IP passed directly to the socket backend: no second hostname lookup.
        return await super().connect_tcp(addresses[0], port, timeout, local_address, socket_options)


def provider_client() -> httpx.AsyncClient:
    transport = httpx.AsyncHTTPTransport(retries=0, trust_env=False)
    transport._pool = httpcore.AsyncConnectionPool(
        ssl_context=ssl.create_default_context(),
        network_backend=PinnedBackend(),
        max_connections=2,
        max_keepalive_connections=0,
    )
    return httpx.AsyncClient(
        transport=transport,
        timeout=httpx.Timeout(20, connect=8),
        follow_redirects=False,
        trust_env=False,
    )


def retry_delay(value: str | None, attempt: int) -> int:
    seconds = 0
    if value:
        try:
            seconds = (
                int(value)
                if value.isdigit()
                else max(0, int((parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds()))
            )
        except (ValueError, TypeError, OverflowError):
            seconds = 0
    return int(max(seconds, 2**attempt))


async def fetch_response(
    db: AsyncSession,
    raw_service: RawIngestionService,
    source: DataSource,
    *,
    use: str,
    url: str,
    allowed_host: str,
    resource: str,
    client: httpx.AsyncClient | None = None,
    method: str = "GET",
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    json_body: Any = None,
    instrument_id: UUID | None = None,
    metadata: dict[str, str | int] | None = None,
    limiter: Callable[[DataSource], Awaitable[None]] = check_provider_rate,
    content_types: tuple[str, ...] = ("application/json",),
) -> RawIngestion:
    SourceGate.require_enabled(source, use)  # Before DNS/client creation.
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != allowed_host
        or parsed.port not in {None, 443}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise AppError(422, "SOURCE_ORIGIN_INVALID", "Exact approved HTTPS endpoint required")
    own = client is None
    client = client or provider_client()
    base_metadata = {"endpoint": parsed.path, "method": method, **(metadata or {})}
    try:
        for attempt in range(3):
            await db.refresh(source)
            SourceGate.require_enabled(source, use)
            await limiter(source)
            base_metadata["source_review_at"] = (
                source.checked_at.isoformat() if source.checked_at else "UNKNOWN"
            )
            requested = datetime.now(UTC)
            try:
                async with client.stream(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers={"Accept-Encoding": "identity", **(headers or {})},
                    follow_redirects=False,
                ) as response:
                    body = bytearray()

                    async def chunks() -> Any:
                        if response.is_stream_consumed:
                            yield response.content
                        else:
                            async for value in response.aiter_raw():
                                yield value

                    async for chunk in chunks():
                        if len(body) + len(chunk) > MAX_BYTES:
                            raise AppError(502, "SOURCE_RESPONSE_TOO_LARGE", "Provider size limit")
                        body.extend(chunk)
                    safe = dict(base_metadata)
                    # Only cache validators, never request/auth/cookie headers.
                    for field in ("etag", "last-modified", "retry-after"):
                        value = response.headers.get(field)
                        if value and len(value) <= 200 and all(ord(c) >= 32 for c in value):
                            safe[field.replace("-", "_")] = value
                    raw = await raw_service.store(
                        data=bytes(body),
                        source_id=source.id,
                        source_slug=source.slug,
                        resource_type=resource,
                        instrument_id=instrument_id,
                        requested_at=requested,
                        http_status=response.status_code,
                        content_type=response.headers.get(
                            "content-type", "application/octet-stream"
                        ),
                        request_metadata=safe,
                    )
                    status = response.status_code
                    if status in {204, 304}:
                        return raw
                    if status == 200:
                        kind = response.headers.get("content-type", "").split(";")[0].lower()
                        if (
                            kind not in content_types
                            or response.headers.get("content-encoding", "identity") != "identity"
                        ):
                            raise AppError(
                                502, "SOURCE_RESPONSE_INVALID", "Unexpected provider encoding/type"
                            )
                        return raw
                    delay = retry_delay(response.headers.get("retry-after"), attempt)
                    if status not in {429, 500, 502, 503, 504}:
                        raise AppError(502, "SOURCE_RESPONSE_INVALID", "Provider rejected request")
                    if attempt == 2 or delay > 30:
                        raise AppError(
                            429 if status == 429 else 503,
                            "SOURCE_RATE_LIMITED" if status == 429 else "SOURCE_UNAVAILABLE",
                            "Provider requires later retry",
                            retry_after=delay,
                        )
            except (httpx.TransportError, AppError) as error:
                if isinstance(error, AppError):
                    if error.code == "SOURCE_RESPONSE_TOO_LARGE":
                        await raw_service.record_failure(
                            source_id=source.id,
                            resource_type=resource,
                            requested_at=requested,
                            error_code=error.code,
                            request_metadata=base_metadata,
                        )
                    raise
                code = (
                    "SOURCE_TIMEOUT"
                    if isinstance(error, httpx.TimeoutException)
                    else "SOURCE_UNAVAILABLE"
                )
                await raw_service.record_failure(
                    source_id=source.id,
                    resource_type=resource,
                    requested_at=requested,
                    error_code=code,
                    request_metadata=base_metadata,
                )
                if attempt == 2:
                    raise AppError(503, code, "Provider transport unavailable") from None
                delay = 2**attempt
            await asyncio.sleep(delay + random.uniform(0, 0.5))
        raise AppError(503, "SOURCE_UNAVAILABLE", "Provider unavailable")
    finally:
        if own:
            await client.aclose()
