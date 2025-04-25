import os
import json
import threading
import uuid
from typing import Dict, Any, Optional

_lock = threading.RLock()

def _get_nexus_file() -> str:
    """Get the path to the nexus file, overridable via NEXUS_FILE env var."""
    return os.getenv("NEXUS_FILE", "runtime/task_nexus.json")


def _load() -> Dict[str, Any]:
    """Load the entire nexus data, returning default structure if missing."""
    path = _get_nexus_file()
    if not os.path.exists(path):
        return {"queue": [], "log": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: Dict[str, Any]) -> None:
    """Save the entire nexus data back to the file."""
    path = _get_nexus_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def add_task(task_type: str, content: str) -> str:
    """Add a new task to the queue and return its unique ID."""
    with _lock:
        data = _load()
        tid = str(uuid.uuid4())
        data["queue"].append({"id": tid, "type": task_type, "content": content})
        _save(data)
        return tid


def pop_task() -> Optional[Dict[str, Any]]:
    """Pop the next task in the queue, returning it or None if empty."""
    with _lock:
        data = _load()
        if not data["queue"]:
            return None
        task = data["queue"].pop(0)
        _save(data)
        return task


def log_result(entry: Dict[str, Any]) -> None:
    """Append a result entry to the log."""
    with _lock:
        data = _load()
        data["log"].append(entry)
        _save(data) 