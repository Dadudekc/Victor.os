#!/usr/bin/env python3
"""
event_logger.py

Structured event logger service: appends typed events to a JSONL file in runtime/structured_events.jsonl.
"""  # noqa: E501

import json
import uuid
from datetime import datetime
from pathlib import Path

# Default path for structured event logs
# FIXME: Determine project root more robustly if this service is used widely.
#        For now, assumes script is run from a context where Path.cwd() is project root
#        or that this path is correctly resolved by the application.
PROJECT_ROOT_ASSUMED = Path.cwd()  # Or use a marker file based approach
DEFAULT_LOG_PATH = PROJECT_ROOT_ASSUMED / "runtime" / "structured_events.jsonl"


def log_structured_event(
    event_type: str, data: dict, source: str, log_file: str = None
) -> None:
    """
    Append a structured event record to a JSONL log file.

    Args:
        event_type: Logical type of the event (e.g., 'GUI_STATE_SAVE').
        data: Arbitrary event payload.
        source: Origin of the event (e.g., 'DreamOSMainWindow').
        log_file: Optional override for the log file path.
    """
    path = Path(log_file or DEFAULT_LOG_PATH)
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "id": uuid.uuid4().hex,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": event_type,
        "source": source,
        "data": data,
    }
    # Atomically append a line
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
