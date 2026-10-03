from __future__ import annotations

from uuid import uuid4

from app.core.storage import get_storage


def main() -> None:
    storage = get_storage()
    storage.ensure_bucket()
    key = f"smoke/{uuid4()}.txt"
    data = b"storage-ok"
    storage.put(key, data, "text/plain")
    try:
        if not storage.exists(key) or storage.get(key) != data:
            raise RuntimeError("MinIO round trip failed")
        print("MinIO object round trip: ok")
    finally:
        storage.delete(key)


if __name__ == "__main__":
    main()
