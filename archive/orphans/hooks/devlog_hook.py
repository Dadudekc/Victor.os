# src/dreamos/hooks/devlog_hook.py
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict

from dreamos.core.config import AppConfig

# Use canonical AgentBus and EventType definitions
from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.core.coordination.event_types import EventType
from dreamos.utils.common_utils import get_utc_iso_timestamp
from filelock import AsyncFileLock, Timeout

logger = logging.getLogger(__name__)


class DevlogHook:
    """Listens for significant system events on the AgentBus and logs them.

    This hook subscribes to various event types (task completion/failure,
    agent errors, protocol violations) and appends formatted summaries to the
    central devlog file (`runtime/devlog/devlog.md`). It uses file locking
    to prevent concurrent write issues.
    """

    def __init__(self, agent_bus: AgentBus, config: AppConfig):
        """Initializes the DevlogHook.

        Args:
            agent_bus: The application's AgentBus instance for subscribing to events.
            config: The loaded application configuration (AppConfig) for accessing paths.
        """
        self.agent_bus = agent_bus
        self.config = config
        try:
            self.devlog_path = (
                Path(config.paths.project_root) / "runtime" / "devlog" / "devlog.md"
            )
            self.devlog_path.parent.mkdir(parents=True, exist_ok=True)
            # Ensure file exists
            if not self.devlog_path.exists():
                self.devlog_path.touch()
            # Use a lock file next to the devlog
            self.lock_path = self.devlog_path.with_suffix(".lock")
            self.lock = AsyncFileLock(self.lock_path, timeout=5)  # 5 second timeout
            logger.info(f"DevlogHook initialized. Log path: {self.devlog_path}")
        except Exception as e:
            logger.critical(
                f"DevlogHook failed to initialize paths/lock: {e}", exc_info=True
            )
            # Consider raising or disabling the hook if init fails critically
            self.lock = None
            self.devlog_path = None

    async def setup_subscriptions(self):
        """Subscribes the hook's event handlers to the AgentBus.

        This method should be called after the asyncio event loop is running
        and the AgentBus is available.
        """
        if not self.agent_bus or not self.lock:
            logger.error(
                "Cannot setup DevlogHook subscriptions: AgentBus or lock not initialized."
            )
            return

        subscriptions = {
            EventType.TASK_COMPLETED: self._handle_task_event,
            EventType.TASK_FAILED: self._handle_task_event,
            EventType.TASK_PERMANENTLY_FAILED: self._handle_task_event,
            EventType.AGENT_ERROR: self._handle_error_event,
            EventType.SYSTEM_ERROR: self._handle_error_event,
            EventType.AGENT_PROTOCOL_VIOLATION: self._handle_protocol_violation,
            # EventType.SYSTEM_AGENT_STATUS_CHANGE: self._handle_agent_status_change, # Optional
        }

        for event_type, handler in subscriptions.items():
            try:
                # Ensure using the string value of the enum member for topic
                await self.agent_bus.subscribe(event_type.value, handler)
                logger.info(f"DevlogHook subscribed to {event_type.name}")
            except Exception as e:
                logger.error(
                    f"Failed to subscribe DevlogHook to {event_type.name}: {e}",
                    exc_info=True,
                )

    async def _handle_task_event(self, event_data: Dict[str, Any]):
        """Handles task lifecycle events (completion, failure).

        Extracts relevant information from the event data and formats a log entry.

        Args:
            event_data: The dictionary payload received from the AgentBus.
                        Expected to contain keys like 'task_id', 'agent_id',
                        'status', 'result_summary'/'result.summary', 'error'.
        """
        try:
            # Assuming payload adheres to TaskEventPayload structure (needs validation)
            task_id = event_data.get("task_id", "UnknownTask")
            agent_id = event_data.get("agent_id", "UnknownAgent")
            status = event_data.get("status", "UNKNOWN_STATUS").upper()
            result_summary = event_data.get("result_summary") or event_data.get(
                "result", {}
            ).get("summary")
            error_msg = event_data.get("error")

            entry = f"- **{status}:** Task `{task_id}` by `{agent_id}`."
            if result_summary:
                entry += f" Summary: {result_summary}"
            if error_msg:
                entry += f" Error: {error_msg}"

            await self._write_log_entry(entry)
        except Exception as e:
            logger.error(
                f"Error handling task event for devlog: {e}. Data: {event_data}",
                exc_info=True,
            )

    async def _handle_error_event(self, event_data: Dict[str, Any]):
        """Handles agent and system error events.

        Extracts error details from the event data and formats a log entry.

        Args:
            event_data: The dictionary payload received from the AgentBus.
                        Expected to conform loosely to BaseEvent structure with
                        an 'error_payload' key containing 'message' and 'details'.
        """
        try:
            source_id = event_data.get(
                "source_id", "UnknownSource"
            )  # Assuming BaseEvent structure
            error_payload = event_data.get(
                "error_payload", {}
            )  # Assuming ErrorEventPayload structure
            error_msg = error_payload.get("message", "Unknown Error")
            details = error_payload.get("details", "No details")

            entry = f"- **ERROR:** Source `{source_id}` reported: {error_msg}. Details: {details}"
            await self._write_log_entry(entry)
        except Exception as e:
            logger.error(
                f"Error handling error event for devlog: {e}. Data: {event_data}",
                exc_info=True,
            )

    async def _handle_protocol_violation(self, event_data: Dict[str, Any]):
        """Handles agent protocol violation events.

        Extracts violation details from the event data and formats a log entry.

        Args:
            event_data: The dictionary payload received from the AgentBus.
                        Expected to contain keys like 'agent_id', 'protocol', 'details'.
        """
        try:
            # Payload structure might vary, adapt as needed
            violator_agent_id = event_data.get("agent_id", "UnknownAgent")
            protocol = event_data.get("protocol", "UnknownProtocol")
            details = event_data.get("details", "No details")

            entry = f"- **PROTOCOL VIOLATION:** Agent `{violator_agent_id}` violated `{protocol}`. Details: {details}"
            await self._write_log_entry(entry)
        except Exception as e:
            logger.error(
                f"Error handling protocol violation for devlog: {e}. Data: {event_data}",
                exc_info=True,
            )

    # async def _handle_agent_status_change(self, event_data: Dict[str, Any]):
    #     """Handles SYSTEM_AGENT_STATUS_CHANGE events (Optional)."""
    #     try:
    #         # Assuming AgentStatusChangePayload structure
    #         agent_id = event_data.get("agent_id", "UnknownAgent")
    #         status = event_data.get("status", "UNKNOWN").upper()
    #         task_id = event_data.get("task_id")
    #
    #         # Only log significant changes like BLOCKED or ERROR?
    #         if status in ["BLOCKED", "ERROR"]:
    #             entry = f"- **STATUS:** Agent `{agent_id}` entered status `{status}`"
    #             if task_id:
    #                 entry += f" during task `{task_id}`."
    #             else:
    #                 entry += "."
    #             await self._write_log_entry(entry)
    #     except Exception as e:
    #          logger.error(f"Error handling agent status change for devlog: {e}. Data: {event_data}", exc_info=True)

    async def _write_log_entry(self, entry: str):
        """Appends a timestamped entry to the devlog file using an async file lock.

        Args:
            entry: The formatted string message to append to the log.
        """
        if not self.lock or not self.devlog_path:
            logger.error(
                f"Cannot write devlog entry, hook not initialized correctly. Entry: {entry}"
            )
            return

        timestamp = get_utc_iso_timestamp()
        formatted_entry = f"\n{timestamp} - {entry}"  # Add newline before entry

        try:
            async with self.lock:
                async with asyncio.to_thread(
                    self.devlog_path.open, mode="a", encoding="utf-8"
                ) as f:
                    await asyncio.to_thread(f.write, formatted_entry)
            logger.debug(f"Appended devlog entry: {entry}")
        except Timeout:
            logger.error(
                f"Timeout acquiring devlog lock ({self.lock_path}). Failed to write entry: {entry}"
            )
        except Exception as e:
            logger.error(
                f"Failed to write entry to devlog {self.devlog_path}: {e}",
                exc_info=True,
            )
