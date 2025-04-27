from __future__ import annotations
import json
import asyncio
import time
import uuid
from pathlib import Path
from typing import TypeVar, Generic, Optional, Any, Callable, Awaitable, Union, List, Dict, Tuple

T = TypeVar('T')

class Singleton(type):
    """Metaclass for single-instance classes."""
    _instances: Dict[type, Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

class AsyncLockManager:
    """Async context manager for asyncio.Lock with optional timeout."""
    def __init__(self, lock: asyncio.Lock, timeout: Optional[float] = None) -> None:
        self._lock = lock
        self._timeout = timeout

    async def __aenter__(self) -> AsyncLockManager:
        if self._timeout is not None:
            await asyncio.wait_for(self._lock.acquire(), timeout=self._timeout)
        else:
            await self._lock.acquire()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._lock.locked():
            self._lock.release()

class Cache(Generic[T]):
    """In-memory cache with time-to-live (TTL) expiration."""
    def __init__(self, ttl: float) -> None:
        self._ttl = ttl
        self._data: Dict[str, Tuple[T, float]] = {}

    async def set(self, key: str, value: T) -> None:
        expire_at = time.monotonic() + self._ttl
        self._data[key] = (value, expire_at)

    async def get(self, key: str) -> Optional[T]:
        item = self._data.get(key)
        if item is None:
            return None
        value, expire_at = item
        if time.monotonic() >= expire_at:
            # expired
            del self._data[key]
            return None
        return value

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def clear(self) -> None:
        self._data.clear()

class RetryManager:
    """Manager to retry async operations with backoff."""
    def __init__(self, max_retries: int, base_delay: float, max_delay: float) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    async def execute(self, func: Callable[[], Awaitable[T]]) -> T:
        attempt = 0
        while True:
            try:
                return await func()
            except Exception:
                attempt += 1
                if attempt >= self.max_retries:
                    raise
                # exponential backoff
                delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
                await asyncio.sleep(delay)

def generate_id(prefix: str = "") -> str:
    """Generate a random 12-character ID, optionally prefixed."""
    random_id = uuid.uuid4().hex[:12]
    return f"{prefix}{random_id}"

def save_json_file(data: Any, path: Union[str, Path]) -> None:
    """Save data as JSON to the specified file path."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def load_json_file(path: Union[str, Path]) -> Any:
    """Load and return JSON data from the specified file path."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"JSON file not found: {p}")
    with p.open('r', encoding='utf-8') as f:
        return json.load(f)

class ValidationError(Exception):
    """Raised when data validation fails."""
    pass

def validate_required_fields(data: dict, fields: List[str]) -> None:
    """Ensure required fields are present in data."""
    missing = [f for f in fields if f not in data]
    if missing:
        raise ValidationError(f"Missing required fields: {missing}")

def validate_field_type(value: Any, expected_type: type, field_name: str) -> None:
    """Ensure the field value matches the expected type."""
    if not isinstance(value, expected_type):
        raise ValidationError(
            f"Field '{field_name}' expected type {expected_type.__name__}, got {type(value).__name__}"
        ) 
