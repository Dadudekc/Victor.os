# src/dreamos/hooks/chronicle_logger.py
import logging
import threading
from datetime import datetime
from pathlib import Path

from dreamos.coordination.agent_bus import AgentBus, BaseEvent

# TODO: Consider removing dependency on core events if hooks should be generic
from dreamos.core.coordination.events import DebugInfoData, DebugInfoEvent

logger = logging.getLogger(__name__)


class ChronicleLoggerHook:
    """Listens to AgentBus events and logs them to the Dreamscape Chronicle."""

    DEFAULT_CHRONICLE_PATH = Path("runtime/logs/dreamscape_chronicle.md")

    def __init__(self, chronicle_path: Path | None = None):
        self.chronicle_path = chronicle_path or self.DEFAULT_CHRONICLE_PATH
        self.chronicle_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.chronicle_path.exists():
            try:
                # Create file with a header if it doesn't exist
                with open(self.chronicle_path, "w", encoding="utf-8") as f:
                    f.write("# Dreamscape Chronicle\n---\n\n")
                logger.info(f"Created chronicle file: {self.chronicle_path}")
            except OSError as e:
                # E501 Fix
                logger.error(
                    f"Failed to create chronicle file {self.chronicle_path}: {e}"
                )
        # TODO: If AgentBus dispatch is async, using threading.Lock and sync
        #       file I/O here will block the event loop. Consider asyncio.Lock
        #       and aiofiles if performance becomes an issue.
        self._lock = threading.Lock()
        self.agent_bus = AgentBus()  # Assuming singleton

        # Subscribe to relevant events
        self.agent_bus.subscribe("*", self._handle_event)
        # E501 Fix
        logger.info(
            f"ChronicleLoggerHook initialized. Logging to {self.chronicle_path}"
        )

    def _format_entry(self, event: BaseEvent) -> str:
        """Formats an event into a Markdown log entry."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        # Use event.event_type directly (might be enum member or string)
        event_type_name = getattr(event.event_type, "name", str(event.event_type))

        if hasattr(event, "data") and isinstance(event.data, dict):
            event_data = event.data
            task_id = str(event_data.get("task_id", "N/A"))
            agent_id = str(
                event_data.get(
                    "agent_id",
                    # E501 Fix
                    (event.source_id if hasattr(event, "source_id") else "System"),
                )
            )
            outcome = str(event_data.get("status", "INFO")).upper()
            details = str(event_data.get("message", "No details provided."))
        elif hasattr(event, "data"):
            event_data_obj = event.data
            task_id = str(getattr(event_data_obj, "task_id", "N/A"))
            agent_id = str(
                getattr(
                    event_data_obj,
                    "agent_id",
                    # E501 Fix
                    (event.source_id if hasattr(event, "source_id") else "System"),
                )
            )
            outcome = str(getattr(event_data_obj, "status", "INFO")).upper()
            # E501 Fix (split getattr chain)
            msg_details = getattr(event_data_obj, "message", None)
            dir_details = getattr(event_data_obj, "directive", None)
            details_val = getattr(event_data_obj, "details", None)
            details = str(
                msg_details or details_val or dir_details or "No details provided."
            )
        else:
            task_id = "N/A"
            # E501 Fix
            agent_id = event.source_id if hasattr(event, "source_id") else "System"
            outcome = "INFO"
            details = "Event has no data field."

        details = str(details).replace("\n", " ").strip()
        if not details:
            details = "No details provided."

        # E501 Fix (part of multi-line f-string, ensure clarity)
        entry = (
            f"### {timestamp} — Event: {event_type_name} (Task: {task_id})\n"
            f"- **Agent**: {agent_id}\n"
            f"- **Outcome**: {outcome}\n"
            # E501 Fix
            f"- **Details**: {details}\n"
            f"---\n\n"
        )
        return entry

    def _handle_event(self, event: BaseEvent):
        """Callback function to handle incoming events and log them."""
        # Add filtering here if needed (e.g., ignore DEBUG events)
        log_entry = self._format_entry(event)
        try:
            # TODO: Revisit locking if switching to async I/O
            with self._lock:
                with open(self.chronicle_path, "a", encoding="utf-8") as f:
                    f.write(log_entry)
        except Exception as e:
            # E501 Fix
            logger.error(f"Failed to write to Chronicle {self.chronicle_path}: {e}")

    def stop(self):
        """Unsubscribe from events."""
        # In a real scenario, you might need a more robust unsubscribe mechanism
        # depending on how AgentBus handles subscriptions.
        logger.info("ChronicleLoggerHook stopping.")
        try:
            # Attempt to unsubscribe if the method exists and is needed
            if hasattr(self.agent_bus, "unsubscribe"):
                self.agent_bus.unsubscribe("*", self._handle_event)
                logger.info("Unsubscribed from AgentBus events.")
            else:
                logger.warning("AgentBus does not have an 'unsubscribe' method.")
        except Exception as e:
            logger.error(f"Error during ChronicleLoggerHook stop/unsubscribe: {e}")

    def start(self):
        """Ensures the hook is ready (subscription happens in __init__)."""
        # Subscription is handled in __init__ to ensure it's done upon creation.
        # This method can be used for any additional startup logic if needed.
        logger.info(
            f"ChronicleLoggerHook started. Already subscribed in init. "
            f"Logging to: {self.chronicle_path}"
        )
        # Removed redundant subscribe call and fixed logger name


# Example usage (if run directly, though normally instantiated by the main app)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Initializing Chronicle Logger Hook...")
    hook = ChronicleLoggerHook()
    print(f"Hook initialized. Sending test event to {hook.chronicle_path}")

    debug_data = DebugInfoData(
        message=(
            "This is a test log entry from ChronicleLoggerHook direct run "
            "using DebugInfoEvent."
        ),
        details={"task_id": "test-001", "custom_info": "some value"},
        level="SUCCESS",
    )
    debug_event = DebugInfoEvent(source_id="test_agent", data=debug_data)
    hook.agent_bus.dispatch_event(debug_event)

    print("Test event sent. Check the chronicle file.")
    # Keep running for a bit to potentially catch other events if bus is active
    # import time
    # time.sleep(5)
    # hook.stop()
