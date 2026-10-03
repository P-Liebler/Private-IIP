from __future__ import annotations

from collections.abc import Iterator
from typing import cast

import pytest
from minio import Minio

from app.core.storage import MinioObjectStorage


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.closed = False
        self.released = False

    def read(self) -> bytes:
        return self.content

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


class FakeMinio:
    def __init__(self) -> None:
        self.buckets: set[str] = set()
        self.objects: dict[tuple[str, str], bytes] = {}
        self.last_response: FakeResponse | None = None

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.buckets

    def make_bucket(self, bucket: str) -> None:
        self.buckets.add(bucket)

    def put_object(
        self, bucket: str, key: str, stream: object, length: int, content_type: str
    ) -> None:
        assert hasattr(stream, "read")
        self.objects[(bucket, key)] = stream.read(length)  # type: ignore[attr-defined]

    def stat_object(self, bucket: str, key: str) -> object:
        if (bucket, key) not in self.objects:
            from minio.error import S3Error

            raise S3Error("NoSuchKey", "missing", key, "request", "host", None)
        return object()

    def get_object(self, bucket: str, key: str) -> FakeResponse:
        self.last_response = FakeResponse(self.objects[(bucket, key)])
        return self.last_response

    def remove_object(self, bucket: str, key: str) -> None:
        del self.objects[(bucket, key)]


@pytest.fixture
def storage() -> Iterator[tuple[MinioObjectStorage, FakeMinio]]:
    fake = FakeMinio()
    service = MinioObjectStorage(cast(Minio, fake), "raw-ingestions")
    service.ensure_bucket()
    yield service, fake


def test_object_round_trip_and_cleanup(storage: tuple[MinioObjectStorage, FakeMinio]) -> None:
    service, fake = storage
    service.put("smoke/one", b"unchanged")
    assert service.exists("smoke/one")
    assert service.get("smoke/one") == b"unchanged"
    assert (
        fake.last_response is not None and fake.last_response.closed and fake.last_response.released
    )
    service.delete("smoke/one")
    assert not service.exists("smoke/one")


def test_put_refuses_to_overwrite(storage: tuple[MinioObjectStorage, FakeMinio]) -> None:
    service, _ = storage
    service.put("raw/existing", b"original")
    with pytest.raises(FileExistsError):
        service.put("raw/existing", b"replacement")
    assert service.get("raw/existing") == b"original"
