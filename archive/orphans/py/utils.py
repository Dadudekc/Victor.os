"""
Consolidated utility functions for file I/O, event handling, health checks, and other common operations.
This module centralizes duplicated or similar utility functions from various scripts.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import psutil

logger = logging.getLogger(__name__)


class FileLock:
    """Thread-safe file locking mechanism."""

    def __init__(self, lock_file: Path):
        self.lock_file = lock_file
        self.lock = threading.Lock()

    def __enter__(self):
        self.lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()


class StateManager:
    """Manages state persistence with file locking."""

    def __init__(self, state_file: Path):
        self.state_file = state_file

    def load_state(self) -> Dict[str, Any]:
        """Load state from file with locking."""
        with FileLock(self.state_file):
            if self.state_file.exists():
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}

    def save_state(self, state: Dict[str, Any]):
        """Save state to file with locking."""
        with FileLock(self.state_file):
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)


class EventHandler:
    """Base class for event handling."""

    def __init__(self):
        self.handlers = {}

    def register_handler(self, event_type: str, handler: Callable):
        """Register an event handler."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def unregister_handler(self, event_type: str, handler: Callable):
        """Unregister an event handler."""
        if event_type in self.handlers:
            self.handlers[event_type].remove(handler)

    def handle_event(self, event_type: str, *args, **kwargs):
        """Handle an event by calling all registered handlers."""
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                handler(*args, **kwargs)


class HealthMonitor:
    """System health monitoring utilities."""

    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """Get current memory usage in MB."""
        mem = psutil.virtual_memory()
        return {
            "total": mem.total / (1024 * 1024),  # MB
            "available": mem.available / (1024 * 1024),
            "percent": mem.percent,
        }

    @staticmethod
    def get_cpu_usage() -> float:
        """Get current CPU usage percentage."""
        return psutil.cpu_percent(interval=1)

    @staticmethod
    def get_disk_usage(path: Path) -> Dict[str, float]:
        """Get disk usage for a path in MB."""
        usage = psutil.disk_usage(str(path))
        return {
            "total": usage.total / (1024 * 1024),  # MB
            "used": usage.used / (1024 * 1024),
            "free": usage.free / (1024 * 1024),
            "percent": usage.percent,
        }


class FileUtils:
    """Common file operations."""

    @staticmethod
    def ensure_dir(path: Path):
        """Ensure a directory exists."""
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def safe_write(path: Path, content: str, encoding: str = "utf-8"):
        """Safely write content to a file."""
        with FileLock(path):
            with open(path, "w", encoding=encoding) as f:
                f.write(content)

    @staticmethod
    def safe_read(path: Path, encoding: str = "utf-8") -> Optional[str]:
        """Safely read content from a file."""
        with FileLock(path):
            if path.exists():
                with open(path, "r", encoding=encoding) as f:
                    return f.read()
            return None
