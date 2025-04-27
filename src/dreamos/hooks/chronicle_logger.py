# src/dreamos/hooks/chronicle_logger.py
import logging
from datetime import datetime
from pathlib import Path
import threading

from dreamos.coordination.agent_bus import AgentBus, BaseEvent

logger = logging.getLogger(__name__)


class ChronicleLoggerHook:
    """Listens to AgentBus events and logs them to the Dreamscape Chronicle."""

    DEFAULT_CHRONICLE_PATH = Path("runtime/logs/dreamscape_chronicle.md")

    def __init__(self, chronicle_path: Path | None = None):
        self.chronicle_path = chronicle_path or self.DEFAULT_CHRONICLE_PATH
        self.chronicle_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.agent_bus = AgentBus() # Assuming singleton

        # Subscribe to relevant events
        self.agent_bus.subscribe("*", self._handle_event)
        logger.info(f"ChronicleLoggerHook initialized. Logging to {self.chronicle_path}")

    def _format_entry(self, event: BaseEvent) -> str:
        """Formats an event into a Markdown log entry."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        event_type = event.event_type
        task_id = getattr(event.data, 'task_id', 'N/A')
        agent_id = getattr(event.data, 'agent_id', 'System')
        outcome = getattr(event.data, 'status', 'INFO').upper()
        details = getattr(event.data, 'message', 'No details provided.')
        
        # Sanitize details slightly
        details = str(details).replace('\n', ' ').strip()
        if not details:
            details = 'No details provided.'

        entry = (
            f"### {timestamp} — Event: {event_type} (Task: {task_id})\n"
            f"- **Agent**: {agent_id}\n"
            f"- **Outcome**: {outcome}\n"
            f"- **Details**: {details}\n"
            f"---\n\n" # Add separator and extra newline
        )
        return entry

    def _handle_event(self, event: BaseEvent):
        """Callback function to handle incoming events and log them."""
        # Add filtering here if needed (e.g., ignore DEBUG events)
        log_entry = self._format_entry(event)
        try:
            with self._lock:
                with open(self.chronicle_path, "a", encoding="utf-8") as f:
                    f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to write to Chronicle {self.chronicle_path}: {e}")

    def stop(self):
        """Unsubscribe from events."""
        # In a real scenario, you might need a more robust unsubscribe mechanism
        # depending on how AgentBus handles subscriptions.
        logger.info("ChronicleLoggerHook stopping (unsubscribe mechanism basic).")
        # self.agent_bus.unsubscribe("*", self._handle_event) # If unsubscribe exists

# Example usage (if run directly, though normally instantiated by the main app)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("Initializing Chronicle Logger Hook...")
    hook = ChronicleLoggerHook()
    print(f"Hook initialized. Sending test event to {hook.chronicle_path}")

    # Send a test event
    test_event_data = {
        'task_id': 'test-001',
        'agent_id': 'test_agent',
        'status': 'SUCCESS',
        'message': 'This is a test log entry from ChronicleLoggerHook direct run.'
    }
    hook.agent_bus.dispatch_event(BaseEvent("TEST_EVENT", data=test_event_data))
    print("Test event sent. Check the chronicle file.")
    # Keep running for a bit to potentially catch other events if bus is active
    # import time
    # time.sleep(5)
    # hook.stop() 