"""Shared utilities for the project scanner."""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class FileLock:
    """Thread-safe file locking mechanism."""

    def __init__(self, lock_file: Path):
        self.lock_file = lock_file
        self.lock = threading.Lock()

    def __enter__(self):
        self.lock.acquire()
        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.lock_file, "w") as f:
                f.write(str(os.getpid()))
        except Exception as e:
            self.lock.release()
            raise e
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        finally:
            self.lock.release()


class StateManager:
    """Manages state persistence with file locking."""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.lock = FileLock(state_file.with_suffix(".lock"))

    def load_state(self) -> Dict[str, Any]:
        """Load state from file with locking."""
        if not self.state_file.exists():
            return {}

        with self.lock:
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading state from {self.state_file}: {e}")
                return {}

    def save_state(self, state: Dict[str, Any]):
        """Save state to file with locking."""
        with self.lock:
            try:
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.state_file, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2)
            except Exception as e:
                logger.error(f"Error saving state to {self.state_file}: {e}")


class EventHandler:
    """Base class for event handling."""

    def __init__(self):
        self._handlers = {}
        self._lock = threading.Lock()

    def register_handler(self, event_type: str, handler: callable):
        """Register an event handler."""
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def unregister_handler(self, event_type: str, handler: callable):
        """Unregister an event handler."""
        with self._lock:
            if event_type in self._handlers:
                self._handlers[event_type].remove(handler)

    def handle_event(self, event_type: str, *args, **kwargs):
        """Handle an event by calling all registered handlers."""
        with self._lock:
            handlers = self._handlers.get(event_type, [])[:]

        for handler in handlers:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")


class HealthMonitor:
    """System health monitoring utilities."""

    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """Get current memory usage in MB."""
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                "rss": memory_info.rss / 1024 / 1024,  # Resident Set Size
                "vms": memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                "shared": memory_info.shared / 1024 / 1024,  # Shared Memory
                "text": memory_info.text / 1024 / 1024,  # Text Segment
                "data": memory_info.data / 1024 / 1024,  # Data Segment
            }
        except ImportError:
            logger.warning("psutil not installed. Memory monitoring disabled.")
            return {}

    @staticmethod
    def get_cpu_usage() -> float:
        """Get current CPU usage percentage."""
        try:
            import psutil

            return psutil.cpu_percent()
        except ImportError:
            logger.warning("psutil not installed. CPU monitoring disabled.")
            return 0.0

    @staticmethod
    def get_disk_usage(path: Path) -> Dict[str, float]:
        """Get disk usage for a path in MB."""
        try:
            import psutil

            usage = psutil.disk_usage(str(path))
            return {
                "total": usage.total / 1024 / 1024,
                "used": usage.used / 1024 / 1024,
                "free": usage.free / 1024 / 1024,
                "percent": usage.percent,
            }
        except ImportError:
            logger.warning("psutil not installed. Disk monitoring disabled.")
            return {}


class FileUtils:
    """File operation utilities."""

    @staticmethod
    def ensure_dir(path: Path):
        """Ensure a directory exists."""
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def safe_write(path: Path, content: str, encoding: str = "utf-8"):
        """Safely write content to a file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding=encoding) as f:
                f.write(content)
            temp_path.replace(path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise e

    @staticmethod
    def safe_read(path: Path, encoding: str = "utf-8") -> Optional[str]:
        """Safely read content from a file."""
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading {path}: {e}")
            return None
