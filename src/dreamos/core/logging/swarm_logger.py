"""
Provides structured JSONL logging for swarm agent events.

This module defines `log_agent_event` for recording agent activities
to a configured log file (typically `agent_activity_log.jsonl`).
It uses file locking to ensure safe concurrent writes from multiple agents
or processes and relies on AppConfig for log path configuration.
"""
import json
import logging
from pathlib import Path
from typing import Optional

# Direct imports - assumes these core components are available
from dreamos.core.config import AppConfig, ConfigError
from dreamos.utils.common_utils import get_utc_iso_timestamp
from dreamos.utils.file_locking import FileLock, LockAcquisitionError

logger = logging.getLogger(__name__)

# This is a simple approach for now, assuming config is loaded once at startup.
_swarm_log_path: Optional[Path] = None


def _get_log_path() -> Optional[Path]:
    """Gets the configured log path, loading config if needed."""
    global _swarm_log_path
    if _swarm_log_path is None:
        try:
            config = AppConfig.load()
            log_dir = config.logging.log_dir
            _swarm_log_path = log_dir / "agent_activity_log.jsonl"
            logger.info(f"[SwarmLogger] Initialized log path: {_swarm_log_path}")
        except ConfigError as e:
            logger.error(f"[SwarmLogger] Configuration error loading log path: {e}")
            _swarm_log_path = None
        except Exception as e:
            logger.error(
                f"[SwarmLogger] Unexpected error loading config for log path: {e}",
                exc_info=True,
            )
            _swarm_log_path = None
    return _swarm_log_path


def log_agent_event(
    agent_id: str,
    action: str,
    target: str,
    outcome: str,
    details: dict = None,
    escalation: bool = False,
):
    """Log a structured event from any agent to the configured JSONL file."""

    log_path = _get_log_path()
    if not log_path:
        logger.error(
            "[SwarmLogger] Cannot log event, log path not configured or failed to initialize."  # noqa: E501
        )
        return

    # Proceed WITH locking
    log_dir = log_path.parent
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"[SwarmLogger] Failed to create log directory {log_dir}: {e}")
        return

    event = {
        "timestamp_utc": get_utc_iso_timestamp(),
        "agent_id": agent_id,
        "action": action,
        "target": target,
        "details": details or {},
        "outcome": outcome,
        "escalation": escalation,
    }

    lock_acquired = False
    try:
        with FileLock(log_path):  # Use synchronous lock
            lock_acquired = True
            with open(log_path, "a", encoding="utf-8") as f:
                json.dump(event, f)
                f.write("\n")

    except LockAcquisitionError as e:
        logger.error(f"[SwarmLogger] Failed to acquire lock for {log_path}: {e}")
    except (IOError, OSError, json.JSONDecodeError) as e:
        logger.error(
            f"[SwarmLogger] Failed to write log event to {log_path} for agent {agent_id} (lock held: {lock_acquired}): {e}"  # noqa: E501
        )
    except Exception as e:
        logger.error(
            f"[SwarmLogger] Unexpected error writing log event (lock held: {lock_acquired}): {e}",  # noqa: E501
            exc_info=True,
        )
