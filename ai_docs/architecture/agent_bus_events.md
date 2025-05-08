## Task Lifecycle Events

These events track the progression of tasks managed within the system.

### `TASK_*` (General Structure)

*   **Payload Class:** `TaskEventPayload` (Base for specific task events)
*   **Purpose:** Provides common fields for various task-related events.
*   **Fields:**
    *   `task_id` (str): The unique ID of the task.
    *   `status` (TaskStatus): The current status of the task (using `TaskStatus` Enum).
    *   `details` (Optional[str]): General details or notes about the event.
    *   `result` (Optional[Any]): Task result data (typically on completion).
    *   `error` (Optional[str]): Error message (typically on failure).
    *   `progress` (Optional[float]): Task progress (typically for specific progress events).

```python
@dataclass
class TaskEventPayload:
    task_id: str
    status: TaskStatus
    details: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: Optional[float] = None
```

### `TASK_PROGRESS`

*   **Payload Class:** `TaskProgressPayload` (Inherits from `TaskEventPayload`)
*   **Purpose:** Reports incremental progress on a task.
*   **Fields (in addition to base):**
    *   `progress` (float): A value between 0.0 and 1.0 indicating completion percentage.
    *   `details` (Optional[str]): Specific details about the progress made.

```python
@dataclass
class TaskProgressPayload(TaskEventPayload):
    progress: float
    details: Optional[str] = None
```

### `TASK_COMPLETED`

*   **Payload Class:** `TaskCompletionPayload` (Inherits from `TaskEventPayload`)
*   **Purpose:** Signals successful completion of a task.
*   **Fields (in addition to base):**
    *   `result` (Optional[Dict[str, Any]]): A dictionary containing the task's output or results.

```python
@dataclass
class TaskCompletionPayload(TaskEventPayload):
    result: Optional[Dict[str, Any]] = field(default_factory=dict)
```

### `TASK_FAILED`

*   **Payload Class:** `TaskFailurePayload` (Inherits from `TaskEventPayload`)
*   **Purpose:** Signals that a task has failed.
*   **Fields (in addition to base):**
    *   `error` (str): A message describing the reason for failure.
    *   `is_final` (bool): Indicates if this failure is considered final (True) or potentially retryable (False).

```python
@dataclass
class TaskFailurePayload(TaskEventPayload):
    error: str
    is_final: bool = False
```

## Tool Interaction Events

Events related to agents invoking tools or reporting tool results.

### `TOOL_CALL`

*   **Payload Class:** `ToolCallPayload`
*   **Purpose:** Signals an agent is invoking a tool.
*   **Fields:**
    *   `tool_name` (str): The name of the tool being called.
    *   `tool_args` (Dict[str, Any]): Arguments passed to the tool.
    *   `agent_id` (str): The ID of the agent making the call.
    *   `correlation_id` (Optional[str]): ID to link this call to an originating task or request.

```python
@dataclass
class ToolCallPayload:
    tool_name: str
    tool_args: Dict[str, Any] = field(default_factory=dict)
    agent_id: str
    correlation_id: Optional[str] = None
```

### `TOOL_RESULT`

*   **Payload Class:** `ToolResultPayload`
*   **Purpose:** Reports the outcome of a tool execution.
*   **Fields:**
    *   `tool_name` (str): The name of the tool that was called.
    *   `status` (str): Outcome status (e.g., "SUCCESS", "FAILURE", "ERROR").
    *   `result` (Optional[Any]): The result data from the tool (JSON-serializable recommended).
    *   `error_message` (Optional[str]): Details if the tool execution failed.
    *   `agent_id` (str): The ID of the agent that invoked the tool.
    *   `correlation_id` (Optional[str]): ID linking back to the `TOOL_CALL` or originating task.

```python
@dataclass
class ToolResultPayload:
    tool_name: str
    status: str
    result: Optional[Any] = None
    error_message: Optional[str] = None
    agent_id: str
    correlation_id: Optional[str] = None
```

## Memory Events

Events related to interactions with memory systems.

### `MEMORY_OPERATION` (Example Event Type)

*   **Payload Class:** `MemoryEventData`
*   **Purpose:** Reports an operation performed on agent or system memory.
*   **Fields:**
    *   `agent_id` (str): Agent performing the operation.
    *   `operation` (str): Type of operation (e.g., 'set', 'get', 'delete', 'query').
    *   `key_or_query` (str): The key accessed or query used.
    *   `status` (str): Outcome ('SUCCESS' or 'FAILURE').
    *   `message` (Optional[str]): Optional details or error message.

```python
@dataclass
class MemoryEventData:
    agent_id: str
    operation: str
    key_or_query: str
    status: str
    message: Optional[str] = None
```

*(Documentation in progress...)* 