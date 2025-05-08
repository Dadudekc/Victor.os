# src/dreamos/monitoring/correlation_validator.py

import logging
import re
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Pattern

# Assuming BaseEvent is defined here - adjust import as necessary
# TODO: Resolve correct import path for BaseEvent
# from dreamos.coordination.agent_bus import BaseEvent
# Placeholder until import is resolved:
class BaseEvent:
    """Represents a basic event structure expected by BusCorrelationValidator.
    
    This is a placeholder. The actual BaseEvent should provide these attributes.
    The validator uses getattr, so it relies on duck-typing.
    
    Attributes:
        event_id (str): A unique identifier for the event.
        event_type (Any): The type of the event (e.g., an enum member, a string).
                          The validator expects `event_type.name` if it's an enum-like object
                          for logging, but primarily uses the `event_type` value itself for comparisons.
        source_id (str): Identifier of the agent or component that emitted the event.
        correlation_id (Optional[str]): The correlation ID for tracking related events.
    """
    event_id: str
    event_type: Any # Replace with actual EventType enum or specific type
    source_id: str
    correlation_id: Optional[str]

# Potential future dependency if loading regex from config
# from dreamos.core.config import AppConfig

logger = logging.getLogger("BusCorrelationValidator")


class BusCorrelationValidator:
    """Validates correlation ID usage in AgentBus events (Singleton)."""

    _instance: Optional["BusCorrelationValidator"] = None
    _lock = threading.Lock()
    # _initialized flag removed, initialization logic handles idempotency

    # Make __init__ private to enforce singleton via get_instance
    def __init__(self, expected_id_format_regex: Optional[str] = None):
        """Private initializer. Use get_instance() instead.

        Args:
            expected_id_format_regex: Optional regex string for validating IDs.
        """
        self.expected_id_format_pattern: Optional[Pattern] = None
        if expected_id_format_regex:
            try:
                self.expected_id_format_pattern = re.compile(expected_id_format_regex)
                logger.info(
                    f"Validator configured with regex: {expected_id_format_regex}"
                )
            except re.error as e:
                logger.error(
                    f"Invalid regex for correlation ID format: {e}. Format validation disabled."
                )
                self.expected_id_format_pattern = None
        else:
            logger.info("No correlation ID format regex. Skipping format validation.")

        self.issues_log: List[Dict[str, Any]] = []
        logger.info("BusCorrelationValidator initialized logic executed.")

    @classmethod
    def configure(cls, expected_id_format_regex: Optional[str] = None):
        """Configures and returns the singleton instance. Should be called once."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    logger.info("Initializing BusCorrelationValidator singleton...")
                    # Pass the configuration to the private constructor
                    cls._instance = cls.__new__(cls)
                    cls._instance.__init__(expected_id_format_regex)
                    logger.info("BusCorrelationValidator singleton initialized.")
                else:
                    # Already initialized while waiting for lock
                    logger.warning("BusCorrelationValidator already initialized by another thread.")
        else:
            # Attempting to reconfigure - log warning, could update config if needed
            logger.warning("BusCorrelationValidator already configured. Re-configuration attempt ignored. "
                           "If update needed, implement an update_config method.")
            # Optionally update config here if re-configuration is desired
            # self._instance.__init__(expected_id_format_regex) # Be careful with re-init logic

        return cls._instance

    @classmethod
    def get_instance(cls) -> "BusCorrelationValidator":
        """Gets the singleton instance. Raises error if not configured."""
        if cls._instance is None:
            # Configuration should happen first via configure()
            # This prevents accidental creation with default (None) regex if config exists
            logger.error("BusCorrelationValidator accessed before configuration.")
            raise RuntimeError("BusCorrelationValidator must be configured using configure() before accessing the instance.")
        return cls._instance

    def validate_event(
        self, event: BaseEvent, context_correlation_id: Optional[str] = None
    ) -> bool:
        """Validates a single event for correlation ID presence, format, and context.

        Returns:
            bool: True if the event is valid regarding correlation ID, False otherwise.
                  Issues are logged internally via log_issue.
        """
        is_valid = True
        # Using getattr defensively, assuming BaseEvent might not always guarantee the attr
        correlation_id = getattr(event, "correlation_id", None)

        # 1. Presence Check
        if correlation_id is None:
            self.log_issue(
                issue_type="MISSING_ID",
                message=f"Correlation ID missing in event ID {getattr(event, 'event_id', 'N/A')} (type: {getattr(event.event_type, 'name', 'N/A')}).",
                event_details={
                    "event_id": getattr(event, 'event_id', 'N/A'),
                    "event_type": getattr(event.event_type, 'name', 'N/A'),
                    "source_id": getattr(event, 'source_id', 'N/A'),
                },
            )
            is_valid = False
            return is_valid # Cannot perform further checks

        # 2. Format Check
        if self.expected_id_format_pattern:
            if not self.expected_id_format_pattern.match(correlation_id):
                self.log_issue(
                    issue_type="INVALID_FORMAT",
                    message=f"Correlation ID '{correlation_id}' does not match expected format in event ID {getattr(event, 'event_id', 'N/A')}.",
                    event_details={
                        "event_id": getattr(event, 'event_id', 'N/A'),
                        "event_type": getattr(event.event_type, 'name', 'N/A'),
                        "source_id": getattr(event, 'source_id', 'N/A'),
                        "correlation_id": correlation_id,
                    },
                    level=logging.WARNING # Treat format mismatch as warning initially
                )
                is_valid = False # Mark as invalid but continue to context check

        # 3. Context Consistency Check
        if context_correlation_id is not None:
            if correlation_id != context_correlation_id:
                self.log_issue(
                    issue_type="CONTEXT_MISMATCH",
                    message=f"Event correlation ID '{correlation_id}' does not match expected context ID '{context_correlation_id}' in event ID {getattr(event, 'event_id', 'N/A')}.",
                    event_details={
                        "event_id": getattr(event, 'event_id', 'N/A'),
                        "event_type": getattr(event.event_type, 'name', 'N/A'),
                        "source_id": getattr(event, 'source_id', 'N/A'),
                        "event_correlation_id": correlation_id,
                        "context_correlation_id": context_correlation_id,
                    },
                    level=logging.ERROR # Context mismatch is likely a bug
                )
                is_valid = False

        return is_valid

    def validate_event_sequence(
        self,
        events: List[BaseEvent],
        sequence_correlation_id: Optional[str] = None,
        expected_origin_types: Optional[List[Any]] = None,
        expected_terminal_types: Optional[List[Any]] = None,
        require_all_origin_types: bool = False, # If true, all expected_origin_types must be found
        require_all_terminal_types: bool = False, # If true, all expected_terminal_types must be found
        expected_event_order: Optional[List[Any]] = None # New parameter for event order
    ) -> bool:
        """Validates a sequence of events for correlation ID consistency, presence of origin/terminal events, and event order.

        Checks that all events share the same correlation ID. 
        Phase 2 adds checks for sequence completeness (start/end events).
        Phase 3 adds checks for event order.

        Args:
            events: The list of BaseEvent objects in the sequence.
            sequence_correlation_id: If provided, all events must match this ID.
                                     If None, the ID is inferred from the first event.
            expected_origin_types: List of event types that are expected to originate the sequence.
            expected_terminal_types: List of event types that are expected to terminate the sequence.
            require_all_origin_types: If true, all expected_origin_types must be found in the sequence.
            require_all_terminal_types: If true, all expected_terminal_types must be found in the sequence.
            expected_event_order: Optional list of event types defining a strict expected order.

        Returns:
            bool: True if the sequence passes basic correlation ID consistency checks,
                  False otherwise.
        """
        if not events:
            logger.debug("validate_event_sequence called with empty list, returning True.")
            return True # An empty sequence is arguably consistent

        target_id: Optional[str] = None

        if sequence_correlation_id is not None:
            target_id = sequence_correlation_id
            logger.debug(f"Validating sequence against explicit target ID: {target_id}")
        else:
            # Infer from the first event
            first_event_id = getattr(events[0], "correlation_id", None)
            if first_event_id is None:
                self.log_issue(
                    issue_type="INVALID_SEQUENCE_START",
                    message="First event in sequence lacks correlation ID. Cannot validate sequence.",
                    event_details={"first_event_id": getattr(events[0], 'event_id', 'N/A')}
                )
                return False
            target_id = first_event_id
            logger.debug(f"Validating sequence against inferred target ID: {target_id} from event {getattr(events[0], 'event_id', 'N/A')}")

        all_valid = True
        for i, event in enumerate(events):
            # Validate the individual event first (presence/format)
            # Pass the target_id as the context_correlation_id for consistency check
            if not self.validate_event(event, context_correlation_id=target_id):
                # log_issue was already called by validate_event
                logger.warning(f"Event index {i} (ID: {getattr(event, 'event_id', 'N/A')}) failed validation within sequence {target_id}.")
                all_valid = False
                # Decide on breaking early or collecting all errors - collect for now

        # --- Phase 2 Additions: Origin and Terminal Event Checks --- #
        if expected_origin_types:
            found_origin_types = set()
            for event in events:
                event_type = getattr(event, "event_type", None)
                if event_type in expected_origin_types:
                    found_origin_types.add(event_type)
            
            if require_all_origin_types:
                if not all(ot in found_origin_types for ot in expected_origin_types):
                    self.log_issue(
                        issue_type="MISSING_ALL_ORIGIN_EVENTS",
                        message=f"Sequence {target_id} does not contain all required origin event types. Expected: {expected_origin_types}, Found: {list(found_origin_types)}",
                        event_details={"correlation_id": target_id, "expected_types": expected_origin_types, "found_types": list(found_origin_types)},
                        level=logging.WARNING
                    )
                    all_valid = False
            elif not found_origin_types: # require_all_origin_types is False, so any one is enough
                self.log_issue(
                    issue_type="MISSING_ORIGIN_EVENT",
                    message=f"Sequence {target_id} does not contain any expected origin event type. Expected one of: {expected_origin_types}",
                    event_details={"correlation_id": target_id, "expected_types": expected_origin_types},
                    level=logging.WARNING
                )
                all_valid = False

        if expected_terminal_types:
            found_terminal_types = set()
            for event in events:
                event_type = getattr(event, "event_type", None)
                if event_type in expected_terminal_types:
                    found_terminal_types.add(event_type)

            if require_all_terminal_types:
                if not all(tt in found_terminal_types for tt in expected_terminal_types):
                    self.log_issue(
                        issue_type="MISSING_ALL_TERMINAL_EVENTS",
                        message=f"Sequence {target_id} does not contain all required terminal event types. Expected: {expected_terminal_types}, Found: {list(found_terminal_types)}",
                        event_details={"correlation_id": target_id, "expected_types": expected_terminal_types, "found_types": list(found_terminal_types)},
                        level=logging.WARNING
                    )
                    all_valid = False
            elif not found_terminal_types: # require_all_terminal_types is False, so any one is enough
                self.log_issue(
                    issue_type="MISSING_TERMINAL_EVENT",
                    message=f"Sequence {target_id} does not contain any expected terminal event type. Expected one of: {expected_terminal_types}",
                    event_details={"correlation_id": target_id, "expected_types": expected_terminal_types},
                    level=logging.WARNING
                )
                all_valid = False

        # --- Phase 3 Addition: Event Order Check ---
        if expected_event_order:
            if len(events) < len(expected_event_order):
                self.log_issue(
                    issue_type="INCOMPLETE_EVENT_ORDER",
                    message=f"Sequence {target_id} is shorter ({len(events)} events) than the expected event order ({len(expected_event_order)} types).",
                    event_details={
                        "correlation_id": target_id,
                        "actual_event_count": len(events),
                        "expected_order_length": len(expected_event_order),
                        "expected_order": expected_event_order
                    },
                    level=logging.WARNING
                )
                all_valid = False
            else:
                # Only check order up to the length of the shorter list if events are more than expected_order
                # or up to len(events) if events are fewer (covered by INCOMPLETE_EVENT_ORDER check already for strictness)
                # For now, let's assume a strict match of length if order is specified, 
                # or at least the beginning of the sequence must match the order.
                # If len(events) > len(expected_event_order), we only check the start.
                # A more sophisticated check might involve flags for strict length matching.
                
                order_len_to_check = min(len(events), len(expected_event_order))
                for i in range(order_len_to_check):
                    actual_event_type = getattr(events[i], "event_type", None)
                    expected_type_at_pos = expected_event_order[i]
                    if actual_event_type != expected_type_at_pos:
                        self.log_issue(
                            issue_type="INVALID_EVENT_ORDER",
                            message=f"Event order mismatch in sequence {target_id} at index {i}. Expected: {expected_type_at_pos}, Found: {actual_event_type}.",
                            event_details={
                                "correlation_id": target_id,
                                "index": i,
                                "expected_type": expected_type_at_pos,
                                "actual_type": actual_event_type,
                                "full_expected_order": expected_event_order
                            },
                            level=logging.WARNING
                        )
                        all_valid = False
                        break # First order mismatch is enough to invalidate order
                
                # Optional: Check if sequence is longer than expected order if strict length is implied by providing order
                if all_valid and len(events) > len(expected_event_order) and expected_event_order: # only if order check passed so far and order was specified
                    # This indicates extraneous events after an ordered prefix matched.
                    # Depending on policy, this could be an issue or allowed.
                    # For now, not logging as an error, but could be a new issue type like "EXTRANEOUS_EVENTS_AFTER_ORDER"
                    pass 

        # - Check against timeouts (would likely happen in the calling monitor service).
        if not all_valid:
             logger.warning(f"Sequence validation failed for correlation ID: {target_id}")

        # Current implementation only checks if all events share the same valid ID.
        return all_valid

    def log_issue(
        self,
        issue_type: str,
        message: str,
        event_details: Optional[Dict[str, Any]] = None,
        level: int = logging.WARNING, # Default to WARNING
    ):
        """Logs a detected validation issue internally and to standard logging."""
        timestamp = datetime.now(timezone.utc).isoformat()
        issue_data = {
            "type": issue_type,
            "message": message,
            "timestamp": timestamp,
            "event_details": event_details or {},
        }
        # Use lock to protect shared issues_log list
        with self._lock: # <<< Restored lock
            # Optional: Limit the size of the issues log (implement if needed)
            # MAX_LOG_SIZE = 1000
            # if len(self.issues_log) >= MAX_LOG_SIZE:
            #     self.issues_log.pop(0) # Remove oldest
            self.issues_log.append(issue_data) # <<< Restored append within lock

        # Log to Python logger
        # Use standard logging levels for severity
        log_prefix = f"[CorrelationValidator-{issue_type}]"
        log_entry = f"{log_prefix} {message}"
        details_str = str(event_details) if event_details else "{}"
        # Avoid excessively long log lines
        max_details_len = 300
        if len(details_str) > max_details_len:
             details_summary = details_str[:max_details_len] + "..."
        else:
             details_summary = details_str

        # Include key event details directly for easier searching if available
        ev_id = event_details.get('event_id', 'N/A') if event_details else 'N/A'
        corr_id = event_details.get('correlation_id', event_details.get('event_correlation_id', 'N/A')) if event_details else 'N/A'
        source_id = event_details.get('source_id', 'N/A') if event_details else 'N/A'

        # Structured logging approach (alternative)
        # logger.log(level, log_prefix + " Issue detected.", extra={ 
        #     'issue_type': issue_type,
        #     'message': message, 
        #     'event_details': event_details
        # })
        
        # Current approach: Log message with truncated details
        logger.log(level, f"{log_entry} [EventID: {ev_id}, CorrID: {corr_id}, Source: {source_id}] Details: {details_summary}")

    def get_issues(self) -> List[Dict[str, Any]]:
        """Returns a copy of the internally logged issues.

        Provides thread-safe access to the issues identified by the validator.
        Returns a shallow copy to prevent external modification of the internal log.
        """
        with self._lock: # <<< Restored lock
            # Return a copy to prevent external modification
            return list(self.issues_log) # <<< Restored access within lock

    def reset_issues(self):
        """Clears the internal issue log.

        Provides thread-safe clearing of the accumulated issues.
        Useful for starting fresh validation periods or during testing.
        """
        with self._lock: # <<< Restored lock
            count = len(self.issues_log)
            self.issues_log = []
            logger.info(f"BusCorrelationValidator issue log reset. Cleared {count} issues.") # <<< Restored access within lock

# --- Placeholder for BaseEvent until import is fixed ---
# Remove this class definition once the actual BaseEvent can be imported
# from dreamos.coordination.agent_bus import BaseEvent # Target import


# Example Usage / Integration Point (Conceptual)

# Configuration (typically done once at application startup):
# from dreamos.core.config import AppConfig # Assuming config system exists
# uuid_regex = AppConfig.load().monitoring.correlation_id_regex 
# BusCorrelationValidator.configure(expected_id_format_regex=uuid_regex)
# If no regex is needed, configure with None:
# BusCorrelationValidator.configure()

# Usage within an event dispatching system (e.g., in AgentBus.dispatch_event):
# validator = BusCorrelationValidator.get_instance()
# 
# # For a single event:
# # my_event: BaseEvent = ... # get event from somewhere
# # current_context_id: Optional[str] = ... # get current correlation from context if available
# # if not validator.validate_event(my_event, context_correlation_id=current_context_id):
# #     # An issue was logged by validate_event itself. Policy for handling can be decided here.
# #     # For example, log an additional high-level error, or prevent event propagation for critical errors.
# #     logger.error(f"Event {my_event.event_id} failed correlation validation.")
# 
# # For a sequence of events:
# # event_sequence: List[BaseEvent] = ...
# # explicit_corr_id: Optional[str] = ... # If the whole sequence must match a known ID
# # origin_types = [MyEventType.REQUEST_START, MyOtherEventType.PROCESS_BEGIN]
# # terminal_types = [MyEventType.REQUEST_END]
# # strict_order = [MyEventType.REQUEST_START, MyEventType.INTERMEDIATE_STEP, MyEventType.REQUEST_END]
# 
# # if not validator.validate_event_sequence(
# #     event_sequence,
# #     sequence_correlation_id=explicit_corr_id,
# #     expected_origin_types=origin_types,
# #     expected_terminal_types=terminal_types,
# #     expected_event_order=strict_order
# # ):
# #     logger.error(f"Event sequence associated with {explicit_corr_id or 'inferred ID'} failed validation.")
# #     # Issues are logged by the validator. Additional actions can be taken here.

# # To retrieve logged issues:
# # all_issues = validator.get_issues()
# # for issue in all_issues:
# #     print(f"Logged issue: {issue}")
# # validator.reset_issues() # To clear for a new period 