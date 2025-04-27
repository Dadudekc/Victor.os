#!/usr/bin/env python3
"""
event_logger.py

Structured event logger service: appends typed events to a JSONL file in runtime/structured_events.jsonl.
"""

import os
import json
import uuid
from datetime import datetime

# Default path for structured event logs
DEFAULT_LOG_PATH = os.path.join(os.getcwd(), 'runtime', 'structured_events.jsonl')


def log_structured_event(event_type: str, data: dict, source: str, log_file: str = None) -> None:
    """
    Append a structured event record to a JSONL log file.

    Args:
        event_type: Logical type of the event (e.g., 'GUI_STATE_SAVE').
        data: Arbitrary event payload.
        source: Origin of the event (e.g., 'DreamOSMainWindow').
        log_file: Optional override for the log file path.
    """
    path = log_file or DEFAULT_LOG_PATH
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    record = {
        'id': uuid.uuid4().hex,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'type': event_type,
        'source': source,
        'data': data,
    }
    # Atomically append a line
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record) + '\n') 
