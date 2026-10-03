from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from typing import Protocol

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings


class ObjectStorage(Protocol):
    def ensure_bucket(self) -> None: ...

    def put(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...


class MinioObjectStorage:
    def __init__(self, client: Minio, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        if self.exists(key):
            raise FileExistsError(f"Object already exists: {key}")
        self.client.put_object(
            self.bucket, key, BytesIO(data), len(data), content_type=content_type
        )

    def get(self, key: str) -> bytes:
        response = self.client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def exists(self, key: str) -> bool:
        try:
            self.client.stat_object(self.bucket, key)
            return True
        except S3Error as error:
            if error.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                return False
            raise

    def delete(self, key: str) -> None:
        """Reserved for smoke/test objects; raw ingestion code must never call this."""
        self.client.remove_object(self.bucket, key)


@lru_cache
def get_storage() -> MinioObjectStorage:
    settings = get_settings()
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    return MinioObjectStorage(client, settings.minio_bucket_raw)
