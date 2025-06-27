from __future__ import annotations

"""Lightweight file locking utilities used across Dream.OS."""

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout


@contextmanager
def acquire_lock(path: Path, timeout: float = 10.0):
    """Context manager that acquires a ``FileLock`` for ``path``.

    The lock file is ``path`` with ``.lock`` appended. Raises ``Timeout`` if the
    lock cannot be acquired within ``timeout`` seconds.
    """
    lock = FileLock(str(path.with_suffix(path.suffix + ".lock")))
    lock.acquire(timeout=timeout)
    try:
        yield
    finally:
        lock.release()


def read_json_locked(path: Path, timeout: float = 10.0) -> Any:
    """Read JSON data from ``path`` using a file lock."""
    with acquire_lock(path, timeout=timeout):
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)


def write_json_locked(path: Path, data: Any, timeout: float = 10.0) -> None:
    """Write JSON data to ``path`` atomically using a lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    with acquire_lock(path, timeout=timeout):
        with temp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)

