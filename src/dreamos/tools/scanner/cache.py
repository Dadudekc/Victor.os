"""
Cache module for the project scanner.

This module provides functionality to cache scan results to improve performance
on subsequent scans.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ProjectCache:
    """
    Manages caching for the project scanner to avoid redundant analysis.
    """
    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self.cache_lock = threading.Lock()
        self.cache = self._load()

    def _load(self) -> Dict:
        with self.cache_lock:
            if self.cache_path.exists():
                try:
                    with open(self.cache_path, "r") as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(
                        f"Failed to load cache file {self.cache_path}: {e}. Starting fresh."
                    )
                    return {}
            return {}

    def _save(self):
        with self.cache_lock:
            try:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_path, "w") as f:
                    json.dump(self.cache, f, indent=2)
            except IOError as e:
                logger.error(f"Failed to save cache file {self.cache_path}: {e}")

    def get(self, key: str) -> Optional[Any]:
        with self.cache_lock:
            return self.cache.get(key)

    def set(self, key: str, value: Any):
        with self.cache_lock:
            self.cache[key] = value
            # Consider debounced/throttled save later if performance is an issue
            self._save()

    def remove(self, key: str):
        with self.cache_lock:
            self.cache.pop(key, None)
            self._save()

    def clear(self):
        with self.cache_lock:
            self.cache = {}
            if self.cache_path.exists():
                try:
                    self.cache_path.unlink()
                    logger.info(f"Cleared cache file: {self.cache_path}")
                except OSError as e:
                    logger.error(f"Failed to delete cache file {self.cache_path}: {e}")

    def analyze_scan_results(self) -> Dict[str, Any]:
        """
        Analyze cache data for patterns or insights.
        """
        logger.info("ProjectCache.analyze_scan_results called, but not yet implemented.")
        return {} 