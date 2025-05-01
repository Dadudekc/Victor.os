# Standard Event Reporting Format

Effective communication within the Dream.OS swarm relies on standardized event
reporting via the `AgentBus`. This document outlines the expected structure and
key event types.

## Core Structure: `BaseEvent`

All events dispatched on the `AgentBus` should ideally be instances of
`BaseEvent` (or subclasses thereof) defined in
`src/dreamos/core/coordination/agent_bus.py`.

The `BaseEvent` dataclass provides the following standard fields:

- `event_type` (EventType): An enum member specifying the event's nature (e.g.,
  `EventType.TASK_COMPLETED`, `EventType.SYSTEM_ERROR`). Topic strings derived
  from this enum follow the `domain.entity.action[.qualifier]` standard.
- `source_id` (str): The unique ID of the agent or system component that
  dispatched the event.
- `data` (Dict[str, Any]): A dictionary containing the event-specific payload.
  The structure of this payload should ideally be defined by a corresponding
  Pydantic model (see `src/dreamos/core/coordination/event_payloads.py`).
- `timestamp` (float): A Unix timestamp (seconds since epoch) indicating when
  the event object was created (defaults to `time.time()`).
- `event_id` (str): A unique UUID (hex string) identifying this specific event
  instance (defaults to `uuid.uuid4().hex`).
- `correlation_id` (Optional[str]): An optional ID used to link related events,
  such as a request and its corresponding response or result.

## Key Event Types & Payloads

While many specific event types exist (see `EventType` enum), some common
reporting patterns include:

### 1. Task Lifecycle Events (`EventType.TASK_*`)

These events track the progress of tasks managed by agents.

- **Publisher:** Typically `BaseAgent` subclasses.
- **Payload:** Uses `TaskEventPayload` or its derivatives
  (`TaskProgressPayload`, `TaskCompletionPayload`, `TaskFailurePayload`).
- **Key Fields in `data`:**
  - `task_id` (str): The ID of the task.
  - `agent_id` (str): The ID of the agent processing the task.
  - `status` (TaskStatus): The current status (`ACCEPTED`, `RUNNING`,
    `COMPLETED`, `FAILED`, etc.).
  - `task_type` (str): The type of the task.
  - `progress` (float): Optional progress percentage (0.0-1.0) for
    `TASK_PROGRESS`.
  - `details` (str): Optional progress details for `TASK_PROGRESS`.
  - `result` (dict): Optional dictionary containing the task result for
    `TASK_COMPLETED`.
  - `error` (str): Error message for `TASK_FAILED` or `TASK_PERMANENTLY_FAILED`.
  - `is_final` (bool): Indicates if a `TASK_FAILED` is permanent.

### 2. Agent Status Events (`EventType.SYSTEM_AGENT_STATUS_CHANGE`)

Reports changes in an agent's operational status.

- **Publisher:** `AgentBus` (internal) or agents themselves (e.g., via
  `BaseAgent.update_agent_status`).
- **Payload:** Uses `AgentStatusChangePayload`.
- **Key Fields in `data`:**
  - `agent_id` (str): The ID of the agent whose status changed.
  - `status` (str): The new status string (e.g., "IDLE", "BUSY", "ERROR").
  - `task_id` (Optional[str]): The ID of the task the agent is currently working
    on, if applicable.
  - `error_message` (Optional[str]): An error message if the status is "ERROR".

### 3. System/Agent Errors (`EventType.SYSTEM_ERROR`, `EventType.AGENT_ERROR`)

Reports errors encountered by system components or agents.

- **Publisher:** Any component or agent encountering an error (e.g., via
  `BaseAgent.publish_agent_error`).
- **Payload:** Uses `AgentErrorPayload`.
- **Key Fields in `data`:**
  - `agent_id` (str): The ID of the agent reporting the error (or "System" if
    applicable).
  - `error_message` (str): A description of the error.
  - `exception_type` (Optional[str]): The class name of the exception, if
    applicable.
  - `traceback` (Optional[str]): The formatted exception traceback, if
    available.
  - `task_id` (Optional[str]): The ID of the task being processed when the error
    occurred.
  - `details` (Optional[dict]): Additional context or details about the error.
  - `correlation_id` (Optional[str]): Correlation ID, if relevant.

### 4. Tool Usage (`EventType.TOOL_CALL`, `EventType.TOOL_RESULT`)

Tracks requests to use agent tools and the results received.

- **Publisher:** Agents requesting tool use or providing results.
- **Payload:** Uses `ToolCallPayload` or `ToolResultPayload`.
- **Key Fields in `data`:**
  - `tool_name` (str): The name of the tool.
  - `args` (dict): Arguments provided to the tool (`TOOL_CALL`).
  - `result` (dict): The result returned by the tool (`TOOL_RESULT`).
  - `error` (Optional[str]): Error message if the tool call failed
    (`TOOL_RESULT`).

## Best Practices

- **Use `EventType` Enum:** Always use the `EventType` enum members when
  creating or subscribing to events to ensure consistency and leverage the
  hierarchical topic structure.
- **Use Payload Dataclasses:** Define and use specific Pydantic dataclasses
  (like those in `event_payloads.py`) for the `data` field of common event
  types. This provides structure, validation, and clarity.
- **Include Correlation ID:** Use `correlation_id` when an event is part of a
  request/response flow or related to a specific workflow instance.
- **Be Concise:** Include only necessary information in the payload.
- **Log Events:** Ensure important events are logged appropriately for debugging
  and monitoring (e.g., using `ChronicleLoggerHook`).
