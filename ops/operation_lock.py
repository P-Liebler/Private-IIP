"""Host-wide backup/restore/retention exclusion with automatic OS crash release."""
from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO


def acquire(root: Path) -> BinaryIO:
    root.mkdir(parents=True, exist_ok=True)
    stream = (root / ".operation.lock").open("a+b")
    if os.fstat(stream.fileno()).st_size == 0:
        stream.write(b"0")
        stream.flush()
    stream.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        stream.close()
        raise RuntimeError("Another backup or restore holds the operation lock") from None
    return stream
