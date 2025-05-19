# Bus Correlation Validator Design

**Agent-7 (SignalMonitor) - Task PIPE-006**

## 1. Overview

The `BusCorrelationValidator` is a system component designed to ensure the integrity of `correlation_id` usage across events flowing through the `AgentBus`. Its primary goal is to help detect and diagnose issues where event sequences are not correctly linked, potentially leading to lost context or errors in asynchronous workflows.

## 2. Validator Class Specification (`BusCorrelationValidator`)

### 2.1. Purpose
To validate the presence, format, and consistency of `correlation_id`s in events.

### 2.2. Instantiation & Configuration
- **Singleton Pattern:** Ensures a single, system-wide instance. Accessed via `BusCorrelationValidator.get_instance()`.
- **Configuration:**
    - `expected_id_format_regex` (Optional `str`): Loaded from `AppConfig`. If specified, `correlation_id`s will be validated against this regex (e.g., for UUID format). If `None`, format validation is skipped.
- **Initialization:** Created early in system startup, around `AgentBus` initialization.

### 2.3. Attributes
- `expected_id_format_regex: Optional[Pattern]` (compiled regex)
- `issues_log: List[Dict[str, Any]]` (internal log of detected validation issues)

### 2.4. Methods

#### `__init__(self, expected_id_format_regex: Optional[str] = None)`
- Stores and compiles `expected_id_format_regex`.
- Initializes `issues_log`.

#### `validate_event(self, event: BaseEvent, context_correlation_id: Optional[str] = None) -> bool`
- **Presence Check:** Verifies `event.correlation_id` exists. Logs `MISSING_ID` issue if not.
- **Format Check:** If `expected_id_format_regex` is set, validates `event.correlation_id` against it. Logs `INVALID_FORMAT` issue on mismatch.
- **Context Consistency Check:** If `context_correlation_id` is provided, compares `event.correlation_id`. Logs `CONTEXT_MISMATCH` on difference.
- Returns `True` if all checks pass for the event, `False` otherwise.

#### `validate_event_sequence(self, events: List[BaseEvent], sequence_correlation_id: Optional[str] = None) -> bool`
- **(Phase 2 Feature)** Determines a target `correlation_id` (from `sequence_correlation_id` or the first event).
- Iterates through `events`, calling `validate_event` for each against the target `correlation_id`.
- Returns `True` if all events in the sequence are valid and consistent. Logs `INVALID_SEQUENCE_START` or other issues as they occur.

#### `log_issue(self, issue_type: str, message: str, event_details: Optional[Dict[str, Any]] = None)`
- Creates an issue dictionary with `type`, `message`, `timestamp`, and optional `event_details`.
- Appends to `self.issues_log`.
- Also logs the issue to a dedicated Python logger (e.g., `logging.getLogger("BusCorrelationValidator")`) with appropriate severity.

#### `get_issues(self) -> List[Dict[str, Any]]`
- Returns a copy of `self.issues_log`.

#### `reset_issues(self)`
- Clears `self.issues_log`.

## 3. Integration Strategy

### 3.1. Primary Hook: `SimpleEventBus.dispatch_event`
- Before dispatching to handlers, `SimpleEventBus.dispatch_event` will call `BusCorrelationValidator.get_instance().validate_event(event)`.
- **Initial Policy on Failure:** Log the issue via `validator.log_issue()` and continue event dispatch (to avoid disrupting existing flows). This can be made stricter later.

### 3.2. Sequence Validation (Phase 2)
- **Option 1 (Preferred):** A dedicated monitoring service/agent subscribes to relevant events, buffers them by `correlation_id`, and calls `validator.validate_event_sequence()` upon sequence completion or timeout.
- **Option 2:** Instrument critical request-response handlers to collect and validate their specific event sequences.

## 4. Issue Reporting

1.  **Internal Validator Log:** `validator.issues_log` for programmatic access.
2.  **Python Logging:** Structured logs to `logging.getLogger("BusCorrelationValidator")`.
    - `WARNING` for missing/malformed IDs.
    - `ERROR` for inconsistencies likely indicating bugs.
3.  **Dedicated Failure Event (Future):** `SYSTEM_VALIDATION_CORRELATION_ERROR` event on `AgentBus`.
4.  **Metrics (Future):** Counters for total validated, missing IDs, format errors, etc.

## 5. Edge Case Considerations

-   **Asynchronous Operations:** Rely on `correlation_id` itself, not strict temporal order. Implement timeouts for sequence validation.
-   **Retries:** System needs a clear policy for `correlation_id` on retries (same ID vs. new/modified). Validator to be aware of retry counts if events carry them. Focus on eventual terminal events.
-   **Long-Lived Processes (Sagas):** Validator focuses on sub-transactions. Overall saga integrity might need event sourcing / audit trails. Hierarchical `correlation_id`s are an advanced topic.
-   **Validator State & Performance:** Use TTL for buffered events in sequence validation. Consider sampling for high-throughput sequence checks. Basic per-event validation applies to all.

## 6. Criteria for Related Events in Sequences (for Phase 2 Sequence Validation)

1.  **Shared `correlation_id`:** Mandatory.
2.  **Originating Event Type:** Identify "request" events from a configurable list of `EventType`s.
3.  **Expected Terminal Event Types:** Define corresponding "terminal" `EventType`s for each request type.
4.  **Intermediate Event Types (Optional):** Define expected intermediate steps for more thorough validation.
5.  **Source and Target ID Consistency (Contextual):** Check if response sources align with request targets.
6.  **Timeout for Sequence Completion:** Log issue if no terminal event is seen within a configurable window. 