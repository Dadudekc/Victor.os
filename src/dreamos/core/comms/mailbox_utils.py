"""Utility functions for agent mailbox interactions."""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from filelock import AsyncFileLock, Timeout

# Adjust utils import if common_utils is moved
from ...utils.common_utils import get_utc_iso_timestamp

# Use relative imports within the core package
from ..config import AppConfig
from ..errors import ConfigurationError
from ..events.base_event import BaseDreamEvent
from ..utils.file_locking import FileLock, LockAcquisitionError, LockDirectoryError

# Setup logger
util_logger = logging.getLogger(__name__)

# --- Type Definitions ---
MailboxMessageType = Literal[
    "TASK_COMMAND",
    "TASK_UPDATE",
    "SYSTEM_MESSAGE",
    "AGENT_QUERY",
    "AGENT_RESPONSE",
    "HEARTBEAT",
    "ERROR_REPORT",
    "DIRECTIVE",
    "PROPOSAL",
    "VOTE",
    "FILE_SHARE",
    "DEBUG_INFO",
    "CUSTOM",
]

MailboxMessagePriority = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# --- Mailbox Utility Functions ---


def validate_mailbox_message_schema(message_data: Dict[str, Any]) -> bool:
    """Validates if the message data dictionary conforms to the basic mailbox message schema."""
    required_keys = [
        "message_id",
        "timestamp_utc",
        "sender_agent_id",
        "recipient_agent_id",
        "subject",
        "message_type",
        "priority",
        "body",
        "read_status",
    ]

    if not all(key in message_data for key in required_keys):
        missing = [key for key in required_keys if key not in message_data]
        util_logger.error(
            f"Mailbox message schema validation failed: Missing keys: {missing}"
        )
        return False

    if not isinstance(message_data.get("message_id"), str):
        util_logger.error(
            "Mailbox message schema validation failed: message_id is not a string."
        )
        return False
    if not isinstance(message_data.get("sender_agent_id"), str):
        util_logger.error(
            "Mailbox message schema validation failed: sender_agent_id is not a string."
        )
        return False
    # Add more strict type/value checks as needed...

    util_logger.debug("Mailbox message schema validation successful.")
    return True


def create_mailbox_message(
    sender_agent_id: str,
    recipient_agent_id: str,
    subject: str,
    message_type: MailboxMessageType,
    body: Union[str, Dict[str, Any]],
    priority: MailboxMessagePriority = "MEDIUM",
    message_id: Optional[str] = None,
    timestamp_utc: Optional[str] = None,
    base_event: Optional[BaseDreamEvent] = None,
) -> Dict[str, Any]:
    """Creates a standardized mailbox message dictionary."""
    msg_id = message_id or uuid.uuid4().hex
    ts_utc = timestamp_utc or get_utc_iso_timestamp()

    message_data = {
        "message_id": msg_id,
        "timestamp_utc": ts_utc,
        "sender_agent_id": sender_agent_id,
        "recipient_agent_id": recipient_agent_id,
        "subject": subject,
        "message_type": message_type,
        "priority": priority,
        "body": body,
        "read_status": False,
        "related_event_id": base_event.event_id if base_event else None,
        "correlation_id": base_event.correlation_id if base_event else None,
    }
    if not validate_mailbox_message_schema(message_data):
        raise ValueError("Generated mailbox message failed schema validation.")
    return message_data


async def write_mailbox_message(
    message_data: Dict[str, Any],
    recipient_inbox_path: Union[str, Path],
    filename_prefix: str = "msg",
    lock_timeout: int = 10,
) -> Path:
    """Writes a mailbox message dictionary to a JSON file in the recipient's inbox."""
    if not validate_mailbox_message_schema(message_data):
        raise ValueError("Message data failed schema validation.")

    inbox_path = Path(recipient_inbox_path)
    lock_path = inbox_path / ".inbox.lock"

    try:
        await asyncio.to_thread(inbox_path.mkdir, parents=True, exist_ok=True)
    except OSError as e:
        util_logger.error(f"Failed to create inbox directory {inbox_path}: {e}")
        raise

    ts_part = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    msg_id_part = message_data["message_id"][:8]
    filename = f"{filename_prefix}_{ts_part}_{msg_id_part}.json"
    filepath = inbox_path / filename
    temp_filepath = inbox_path / f"{filename}.{os.getpid()}.tmp"

    lock = AsyncFileLock(lock_path)
    try:
        async with lock.acquire(timeout=lock_timeout):
            util_logger.debug(f"Acquired lock for inbox {inbox_path}")

            def write_sync():
                with open(temp_filepath, "w", encoding="utf-8") as f:
                    json.dump(message_data, f, indent=2)
                os.replace(temp_filepath, filepath)

            await asyncio.to_thread(write_sync)
            util_logger.info(f"Successfully wrote mailbox message to {filepath}")
            return filepath
    except Timeout:
        util_logger.error(
            f"Could not acquire lock for inbox {inbox_path} within {lock_timeout}s"
        )
        if await asyncio.to_thread(temp_filepath.exists):
            try:
                await asyncio.to_thread(os.remove, temp_filepath)
            except OSError:
                pass
        raise
    except Exception as e:
        util_logger.error(
            f"Failed to write mailbox message to {filepath}: {e}", exc_info=True
        )
        if await asyncio.to_thread(temp_filepath.exists):
            try:
                await asyncio.to_thread(os.remove, temp_filepath)
            except OSError:
                pass
        raise IOError(f"Failed writing message to {filepath}") from e
    finally:
        if lock.is_locked:
            await lock.release()
            util_logger.debug(f"Released lock for inbox {inbox_path}")


async def read_mailbox_message(
    filepath: Union[str, Path], lock_timeout: int = 10
) -> Optional[Dict[str, Any]]:
    """Reads a mailbox message JSON file, optionally marking it as read."""
    path = Path(filepath)
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock = AsyncFileLock(lock_path)

    try:
        async with lock.acquire(timeout=lock_timeout):
            util_logger.debug(f"Acquired lock for message file {path}")
            if not await asyncio.to_thread(path.exists):
                util_logger.warning(f"Mailbox message file not found: {path}")
                return None

            def read_sync():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)

            message_data = await asyncio.to_thread(read_sync)
            util_logger.debug(f"Successfully read message file {path}")
            return message_data
    except FileNotFoundError:
        util_logger.warning(
            f"Mailbox message file not found during locked read: {path}"
        )
        return None
    except json.JSONDecodeError:
        util_logger.error(
            f"Failed to decode JSON from message file: {path}", exc_info=True
        )
        return None
    except Timeout:
        util_logger.error(
            f"Could not acquire lock for message file {path} within {lock_timeout}s"
        )
        return None
    except Exception as e:
        util_logger.error(f"Failed to read mailbox message {path}: {e}", exc_info=True)
        return None
    finally:
        if lock.is_locked:
            await lock.release()
            util_logger.debug(f"Released lock for message file {path}")


async def list_mailbox_messages(
    inbox_path: Union[str, Path], pattern: str = "msg_*.json"
) -> List[Path]:
    """Lists message files in the inbox directory, excluding temporary/lock files."""
    path = Path(inbox_path)
    if not await asyncio.to_thread(path.is_dir):
        util_logger.warning(f"Inbox directory not found or is not a directory: {path}")
        return []
    try:

        def glob_sync():
            return list(path.glob(pattern))

        all_files = await asyncio.to_thread(glob_sync)
        message_files = [
            f
            for f in all_files
            if f.is_file() and not f.name.endswith((".tmp", ".lock"))
        ]
        util_logger.debug(
            f"Found {len(message_files)} potential messages in {path} matching {pattern}"
        )
        return message_files
    except Exception as e:
        util_logger.error(f"Failed to list messages in {path}: {e}", exc_info=True)
        return []


def get_agent_mailbox_path(agent_id: str, config: AppConfig) -> Path:
    """Constructs the standard inbox path for a given agent ID based on config."""
    base_mailbox_dir = config.get("system.paths.mailboxes")
    if not base_mailbox_dir:
        raise ConfigurationError(
            "Base mailbox directory ('system.paths.mailboxes') not found in configuration."
        )
    safe_agent_id = agent_id.replace(" ", "_").replace("/", "-").replace("\\", "-")
    if safe_agent_id != agent_id:
        util_logger.warning(
            f"Agent ID '{agent_id}' contained potentially unsafe characters, using '{safe_agent_id}' for path."
        )
    inbox_path = Path(base_mailbox_dir) / safe_agent_id / "inbox"
    return inbox_path


def validate_agent_mailbox_path(path: Path, config: AppConfig) -> bool:
    """Checks if a given path is a valid agent mailbox inbox path according to config."""
    base_mailbox_dir = config.get("system.paths.mailboxes")
    if not base_mailbox_dir:
        util_logger.error(
            "Cannot validate mailbox path: Base directory not configured."
        )
        return False
    base_path = Path(base_mailbox_dir).resolve()
    target_path = path.resolve()
    if not target_path.is_relative_to(base_path):
        return False
    try:
        relative_parts = target_path.relative_to(base_path).parts
        if len(relative_parts) == 2 and relative_parts[1] == "inbox":
            return True
    except ValueError:
        pass
    return False


# ... existing code ... (Keep other utils like format_agent_report, publish_supervisor_alert)
