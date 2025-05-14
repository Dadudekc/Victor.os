"""Abstract base class and in-memory implementation for cache providers."""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from core.utils.common_utils import get_utc_iso_timestamp # For CacheStats

class CacheStats:
    """Tracks cache performance statistics."""
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.last_cleared = get_utc_iso_timestamp()
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0
    def record_hit(self, key: str) -> None: self.hits += 1
    def record_miss(self, key: str) -> None: self.misses += 1
    def clear(self) -> None:
        self.hits = 0
        self.misses = 0
        self.last_cleared = get_utc_iso_timestamp()
    def get_stats(self) -> Dict[str, Any]:
        return {
            "hits": self.hits, "misses": self.misses,
            "hit_rate": round(self.hit_rate, 2), "last_cleared": self.last_cleared
        }

class CacheProvider(ABC):
    """Abstract base class for cache providers."""
    @abstractmethod
    def get(self, key: str) -> Optional[Tuple[Any, float]]: pass
    @abstractmethod
    def set(self, key: str, value: Any, timestamp: float) -> None: pass
    @abstractmethod
    def delete(self, key: str) -> None: pass
    @abstractmethod
    def clear(self) -> None: pass
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]: pass
    @abstractmethod
    def record_hit(self, key: str) -> None: pass
    @abstractmethod
    def record_miss(self, key: str) -> None: pass
    @abstractmethod
    def get_raw_cache_data(self) -> Dict[str, Tuple[Any, float]]: pass

class InMemoryCacheProvider(CacheProvider):
    """In-memory implementation of the CacheProvider interface."""
    def __init__(self, max_cache_size: int = 1000):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._stats = CacheStats()
        self.max_cache_size = max_cache_size
    def get(self, key: str) -> Optional[Tuple[Any, float]]: return self._cache.get(key)
    def set(self, key: str, value: Any, timestamp: float) -> None:
        if len(self._cache) >= self.max_cache_size and key not in self._cache:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        self._cache[key] = (value, timestamp)
    def delete(self, key: str) -> None:
        if key in self._cache: del self._cache[key]
    def clear(self) -> None:
        self._cache.clear()
        self._stats.clear()
    def get_stats(self) -> Dict[str, Any]: return self._stats.get_stats()
    def record_hit(self, key: str) -> None: self._stats.record_hit(key)
    def record_miss(self, key: str) -> None: self._stats.record_miss(key)
    def get_raw_cache_data(self) -> Dict[str, Tuple[Any, float]]: return self._cache.copy() 