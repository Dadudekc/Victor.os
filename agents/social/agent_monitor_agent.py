"""
Agent responsible for monitoring the system by listening to events on the AgentBus
and logging key events to a structured log file.
"""
import logging
import os
# Removed sys path manipulation, assume standard imports work
# import sys
import json
import threading
from datetime import datetime # Removed timedelta as it wasn't used
from typing import Optional, Dict, Any

# Canonical imports for Bus and Event system
from core.coordination.agent_bus import AgentBus
from core.coordination.dispatcher import Event, EventType

# Keep TaskStatus if needed for interpreting event.data, but EventType.TASK_COMPLETED/FAILED should suffice
# from agents.task_executor_agent import TaskStatus

logger = logging.getLogger(__name__)

AGENT_NAME = "AgentMonitorAgent"
DEFAULT_LOG_PATH = "run/logs/agent_history.jsonl"

class AgentMonitorAgent:
    """Listens to the AgentBus and logs significant events based on EventType."""

    def __init__(self, agent_bus: AgentBus, log_file_path: str = DEFAULT_LOG_PATH):
        """
        Initializes the agent monitor.

        Args:
            agent_bus: The central AgentBus instance.
            log_file_path: Path to the JSON Lines file for logging events.
        """
        self.agent_name = AGENT_NAME
        self.bus = agent_bus
        self.log_file_path = os.path.abspath(log_file_path)
        self._log_lock = threading.Lock() # Lock for writing to the log file

        # Ensure log directory exists
        try:
            os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
            with open(self.log_file_path, 'a', encoding='utf-8'): pass
        except IOError as e:
            logger.error(f"Failed to create log directory or file {self.log_file_path}: {e}")
            raise

        # Register agent
        self.bus.register_agent(self.agent_name, capabilities=["monitoring"])

        # Register handler for specific EventTypes we want to monitor
        # This list can be expanded or configured
        event_types_to_monitor = [
            EventType.AGENT_REGISTERED,
            EventType.AGENT_UNREGISTERED,
            EventType.TASK_QUEUED,
            EventType.TASK_STARTED,
            EventType.TASK_PROGRESS, # Log progress updates
            EventType.TASK_COMPLETED,
            EventType.TASK_FAILED,
            EventType.POST_CONTENT, # Log social posts
            EventType.GET_ANALYTICS, # Log analytics requests
            EventType.REQUEST_CURSOR_ACTION, # Log cursor requests
            EventType.SHUTDOWN_REQUESTED, # Log shutdown signals
            EventType.SYSTEM_DIAGNOSTICS_REQUEST, # Log diagnostic requests
            EventType.SYSTEM_DIAGNOSTICS_RESPONSE, # Log diagnostic responses
            # Consider adding AGENT_LOGIN, CHECK_AGENT_LOGIN_STATUS if needed
            # Add a generic error type if one exists or handle TASK_FAILED carefully
        ]

        for event_type in event_types_to_monitor:
            # Assuming bus.register_handler can take EventType enum directly
            # If it requires string, use event_type.name
            try:
                self.bus.register_handler(event_type, self.handle_event)
                logger.info(f"Registered handler for EventType: {event_type.name}")
            except Exception as e:
                logger.error(f"Failed to register handler for {event_type.name}: {e}")

        # Alternative: Register a wildcard handler if the bus supports it
        # try:
        #     self.bus.register_wildcard_handler(self.handle_event)
        #     logger.info(f"Registered wildcard handler to monitor all events.")
        # except AttributeError:
        #     logger.warning("AgentBus does not support register_wildcard_handler. Monitoring only specific types.")
        # except Exception as e:
        #      logger.error(f"Failed to register wildcard handler: {e}")

        logger.info(f"{self.agent_name} initialized. Logging events to: {self.log_file_path}")

    def _log_event(self, event_data: Dict[str, Any]):
        """Appends a structured event to the JSON Lines log file (thread-safe)."""
        try:
            event_data["log_timestamp"] = datetime.now().isoformat() # Add monitor timestamp
            # Ensure all values are JSON serializable (basic conversion)
            serializable_data = json.loads(json.dumps(event_data, default=str))
            log_line = json.dumps(serializable_data)
            with self._log_lock:
                with open(self.log_file_path, 'a', encoding='utf-8') as f:
                    f.write(log_line + '\n')
        except TypeError as e:
            logger.error(f"Serialization error writing event to log file {self.log_file_path}: {e} - Event keys: {list(event_data.keys())}")
        except Exception as e:
            logger.error(f"Failed to write event to log file {self.log_file_path}: {e} - Event Type: {event_data.get('event')}")

    def handle_event(self, event: Event):
        """Processes events received on the bus and logs them."""
        logger.debug(f"{self.agent_name} received event: ID={event.id}, Type={event.type.name}, Source={event.source_id}, Target={event.target_id}")

        # Construct the log entry directly from the event object
        log_entry = {
            "timestamp": datetime.fromtimestamp(event.timestamp).isoformat() if event.timestamp else datetime.now().isoformat(), # Use event timestamp
            "event": event.type.name, # Use the enum name as the event type string
            "event_id": event.id,
            "source_id": event.source_id,
            "target_id": event.target_id,
            "priority": event.priority,
            "data": event.data # Log the entire data payload
        }

        # Optionally extract specific fields from data for top-level logging if needed
        # Example: Extract task_id if present in TASK_* events
        if event.type in [EventType.TASK_QUEUED, EventType.TASK_STARTED, EventType.TASK_PROGRESS, EventType.TASK_COMPLETED, EventType.TASK_FAILED]:
            log_entry["task_id"] = event.data.get("task_id") # Get task_id if available in data
            # Maybe also log correlation_id if present (for responses)
            log_entry["correlation_id"] = event.data.get("correlation_id")

        # Example: Extract platform for social media events
        if event.type in [EventType.POST_CONTENT, EventType.GET_ANALYTICS]:
             log_entry["platform"] = event.data.get("platform")

        # Example: Log error details for TASK_FAILED
        if event.type == EventType.TASK_FAILED:
            log_entry["error_details"] = event.data.get("error")

        self._log_event(log_entry)

    def shutdown(self):
        """Perform any cleanup needed for the monitor agent."""
        logger.info(f"Shutting down {self.agent_name}...")
        # If bus supports it, explicitly unregister handlers or agent
        # try:
        #     self.bus.unregister_agent(self.agent_name)
        # except AttributeError:
        #     pass # Ignore if bus doesn't support unregister
        # except Exception as e:
        #     logger.error(f"Error unregistering agent {self.agent_name}: {e}")

        logger.info(f"{self.agent_name} shutdown complete.")


# --- REMOVED Main execution block --- 