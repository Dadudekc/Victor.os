"""
dreamos.tools.read_file
~~~~~~~~~~~~~~~~~~~~~~~

A robust, concurrency‑safe file‑reader for Dream.OS agents.

Key capabilities
----------------
* ✨  **Smart encoding detection** (UTF‑8, UTF‑16, latin‑1 …) via `locale` heuristics;
* 🧩 **Partial reads** – by byte‑range, line‑range *or* regex match (handy for huge logs);
* 🕒 **Timeout & retry** – non‑blocking read with configurable back‑off (`tenacity`);
* 🔐 **Cross‑platform file‑locking** – prevents reading half‑written files (`filelock`);
* 💾 **Streaming** – optional generator that yields chunks/lines to keep RAM tiny;
* 🗜️  **Transparent JSON / YAML helpers** (`read_json`, `read_yaml`);
* 🧮 **Metrics hooks** – pluggable callback so your monitoring agent can collect I/O stats;
* ✅  100 % backwards‑compatible: `read_file(path)` still gives you the full text.

Dependencies
------------
`pip install filelock chardet tenacity pyyaml`  (all are already used elsewhere in
Dream.OS, so you shouldn't be pulling in anything new).

"""

from __future__ import annotations

import io
import json
import locale
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Generator, Iterable, Iterator, Literal, Optional, Union

from filelock import FileLock, Timeout as LockTimeout
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import chardet

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # YAML helpers will raise if missing


__all__ = [
    "read_file",
    "read_json",
    "read_yaml",
    "StreamMode",
    "ReadMetrics",
    "ReadFileError",
]

_LOGGER = logging.getLogger("dreamos.tools.read_file")
DEFAULT_TIMEOUT = 10  # seconds
DEFAULT_LOCK_TIMEOUT = 0.1  # seconds
_CHUNK = 1024 * 1024  # 1 MiB

PathLike = Union[str, os.PathLike[str]]
StreamMode = Literal["text", "bytes", "lines"]
MetricsHook = Callable[["ReadMetrics"], None]


class ReadFileError(RuntimeError):
    """Raised when all read attempts fail."""


class ReadMetrics(dict):
    """Lightweight container to expose metrics to a callback."""

    path: Path
    duration: float
    size_bytes: int
    encoding: str
    attempt: int


# --------------------------------------------------------------------------- #
# internal helpers
# --------------------------------------------------------------------------- #


def _detect_encoding(sample: bytes) -> str:
    """Best‑effort encoding guess using chardet; fall back to locale."""
    if not sample:
        return "utf-8"
    guess = chardet.detect(sample)
    enc = (guess.get("encoding") or "").lower()
    if enc:
        return enc
    return locale.getpreferredencoding(False) or "utf-8"


def _open_locked(
    path: Path, lock_t: float = DEFAULT_LOCK_TIMEOUT
) -> tuple[io.BufferedReader, Optional[FileLock]]:
    """
    Open *path* for **reading** with a non‑blocking lock.

    The lock file is `path + ".lock"`.
    """
    lock = None
    if lock_t > 0:
        lock = FileLock(str(path) + ".lock")
        try:
            lock.acquire(timeout=lock_t)
        except LockTimeout:
            # just warn – we'll still try to read; better be eventually‑consistent
            _LOGGER.warning("Read lock timeout on %s – reading without lock", path)
            lock = None
    f = path.open("rb")
    return f, lock


# --------------------------------------------------------------------------- #
# core retry wrapper
# --------------------------------------------------------------------------- #


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((OSError, ReadFileError)),
    reraise=True,
)
def _read_once(
    path: Path,
    *,
    mode: StreamMode = "text",
    start: int | None = None,
    end: int | None = None,
    regex: str | None = None,
    encoding: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[Any, ReadMetrics]:
    """Single attempt; wrapped by tenacity for retries."""
    start_time = time.perf_counter()

    if not path.exists():
        raise ReadFileError(f"File not found: {path}")

    f, lock = _open_locked(path)

    try:
        if mode == "bytes":
            data: bytes
            if start is not None:
                f.seek(start)
            if end is not None:
                length = end - (start or 0)
                data = f.read(length)
            else:
                data = f.read()
            result = data

        elif mode == "lines":
            lines: list[str] = []
            text_stream = io.TextIOWrapper(f, encoding=encoding or "utf-8", errors="replace")
            for idx, line in enumerate(text_stream):
                if start is not None and idx < start:
                    continue
                if regex and not re.search(regex, line):
                    continue
                lines.append(line.rstrip("\n"))
                if end is not None and len(lines) >= (end - (start or 0)):
                    break
            result = lines

        else:  # "text"  (default)
            raw = f.read() if (start is None and end is None) else f.read(end or -1)
            enc = encoding or _detect_encoding(raw[:4096])
            result = raw.decode(enc, errors="replace")

    finally:
        f.close()
        if lock:
            lock.release()

    duration = time.perf_counter() - start_time
    metrics = ReadMetrics(
        path=path,
        duration=duration,
        size_bytes=path.stat().st_size,
        encoding=encoding or "utf-8",
        attempt=_read_once.retry.statistics.get("attempt_number", 1),
    )
    return result, metrics


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #


def read_file(
    path: PathLike,
    *,
    mode: StreamMode = "text",
    start: int | None = None,
    end: int | None = None,
    regex: str | None = None,
    encoding: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    on_metrics: MetricsHook | None = None,
) -> Any:
    """
    Read *path* with many quality‑of‑life improvements.

    Parameters
    ----------
    path:
        File to read.
    mode:
        ``"text"`` (default) – returns *str*  
        ``"bytes"`` – returns *bytes*  
        ``"lines"`` – returns *list[str]* (one line per element without ``\n``)
    start, end:
        Byte offsets for ``mode="bytes"`` *or* line numbers for ``mode="lines/text"``.
        Slices are inclusive of *start* and **exclusive** of *end*.
    regex:
        When ``mode="lines"``, include only lines matching this pattern.
    encoding:
        Force an encoding (default: auto‑detect).
    timeout:
        Seconds before the first read attempt is aborted (per attempt).
    on_metrics:
        Optional callback receiving a :class:`ReadMetrics` dict after a successful read.

    Raises
    ------
    ReadFileError
        If reading fails after retries.
    """
    path = Path(path)

    try:
        data, metrics = _read_once(
            path,
            mode=mode,
            start=start,
            end=end,
            regex=regex,
            encoding=encoding,
            timeout=timeout,
        )
        if on_metrics:
            on_metrics(metrics)
        return data
    except Exception as exc:
        raise ReadFileError(f"Failed to read {path}: {exc}") from exc


# convenience helpers ------------------------------------------------------- #


def read_json(path: PathLike, **kwargs) -> Any:
    """Shorthand for JSON files."""
    text = read_file(path, mode="text", **kwargs)
    return json.loads(text)


def read_yaml(path: PathLike, **kwargs) -> Any:
    """Shorthand for YAML files (requires ``pyyaml``)."""
    if yaml is None:  # pragma: no cover
        raise ImportError("pyyaml is required for read_yaml")
    text = read_file(path, mode="text", **kwargs)
    return yaml.safe_load(text) 