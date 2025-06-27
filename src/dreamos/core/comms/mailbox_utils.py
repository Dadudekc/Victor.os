from __future__ import annotations

"""Utilities for interacting with agent mailboxes."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from ..utils.file_locking import acquire_lock

MAILBOX_ROOT = Path("runtime/agent_comms/agent_mailboxes")


def _ensure_mailbox(agent_id: str) -> Path:
    mailbox = MAILBOX_ROOT / agent_id / "inbox.json"
    mailbox.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(mailbox.parent, 0o770)
    if not mailbox.exists():
        with acquire_lock(mailbox):
            if not mailbox.exists():
                temp = mailbox.with_suffix('.tmp')
                with temp.open('w', encoding='utf-8') as f:
                    json.dump([], f)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp, mailbox)
    return mailbox


def write_mailbox_message(agent_id: str, message: Dict[str, Any]) -> None:
    """Append a message to an agent's mailbox using file locking."""
    mailbox = _ensure_mailbox(agent_id)
    with acquire_lock(mailbox):
        try:
            with mailbox.open("r", encoding="utf-8") as f:
                messages: List[Dict[str, Any]] = json.load(f)
        except Exception:
            messages = []
        messages.append(message)
        temp = mailbox.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, mailbox)


def read_mailbox_messages(agent_id: str) -> List[Dict[str, Any]]:
    """Read all messages from an agent's mailbox."""
    mailbox = _ensure_mailbox(agent_id)
    with acquire_lock(mailbox):
        if not mailbox.exists():
            return []
        try:
            with mailbox.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


