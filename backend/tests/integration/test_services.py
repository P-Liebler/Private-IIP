from __future__ import annotations

import asyncio

import pytest

from app.core.storage import get_storage
from app.core.valkey import check_valkey
from app.db.session import check_database


@pytest.mark.integration
def test_database_connection() -> None:
    asyncio.run(check_database())


@pytest.mark.integration
def test_valkey_connection() -> None:
    asyncio.run(check_valkey())


@pytest.mark.integration
def test_minio_bucket_connection() -> None:
    storage = get_storage()
    storage.ensure_bucket()
    assert storage.client.bucket_exists(storage.bucket)
