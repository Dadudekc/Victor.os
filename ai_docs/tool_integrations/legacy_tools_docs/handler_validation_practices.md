# AgentBus Handler Validation Best Practices

Robust communication within the Dream.OS swarm depends not only on publishing
standardized events but also on handlers correctly processing these events. This
document outlines best practices for validating incoming events within AgentBus
handlers.

## Why Validate?

- **Prevent Errors:** Ensures your handler doesn't crash due to unexpected event
  structures or missing data.
- **Improve Reliability:** Makes agent interactions more predictable and less
  prone to cascading failures.
- **Ease Debugging:** Clear validation checks make it easier to pinpoint issues
  originating from malformed events or incorrect handler logic.
- **Security:** Basic validation can prevent unexpected behavior if events are
  somehow crafted maliciously (though AgentBus is primarily for internal
  communication).

## Validation Points

Handlers typically receive the `event` object (usually a `BaseEvent` instance or
subclass). Key validation points include:

1.  **Event Type:** Ensure the event received matches the type the handler
    expects (although the bus routing usually handles this).
2.  **Payload Existence & Type:** Check if `event.data` exists and is of the
    expected type (usually `dict`).
3.  **Required Payload Keys:** Verify that essential keys exist within the
    `event.data` dictionary before accessing them.
4.  **Data Types:** Check if the values associated with keys have the expected
    data types (e.g., `task_id` is a string, `progress` is a float).
5.  **Value Constraints:** If applicable, validate specific value ranges or
    formats (e.g., status is a valid `TaskStatus` enum, timestamp is a
    reasonable value).

## Implementation Strategies

### 1. Manual Dictionary Checks (Basic)

This is the simplest approach, suitable for handlers expecting basic dictionary
payloads.

```python
def handle_simple_event(event: BaseEvent):
    if not isinstance(event.data, dict):
        logger.warning(f"Handler received non-dict payload: {type(event.data)}")
        return

    task_id = event.data.get("task_id")
    status_str = event.data.get("status")

    if not task_id or not isinstance(task_id, str):
        logger.error(f"Handler missing or invalid 'task_id' in event data: {event.data}")
        # Optionally publish an error event
        return

    if not status_str or not isinstance(status_str, str):
        logger.error(f"Handler missing or invalid 'status' in event data: {event.data}")
        return

    # ... proceed with processing task_id and status_str ...
    print(f"Processing event for task {task_id} with status {status_str}")
```

- **Pros:** Simple, no external dependencies.
- **Cons:** Verbose, error-prone, doesn't handle complex types or nested
  structures well, requires manual type checking.

### 2. Pydantic Model Validation (Recommended)

Leverage Pydantic models (like those defined in
`src/dreamos/core/coordination/event_payloads.py`) for robust validation.

```python
from pydantic import ValidationError
from dreamos.core.coordination.event_payloads import TaskEventPayload # Example payload model

def handle_task_event(event: BaseEvent):
    if not isinstance(event.data, dict):
        logger.warning(f"Handler received non-dict payload: {type(event.data)}")
        return

    try:
        # Attempt to parse and validate the data using the Pydantic model
        payload = TaskEventPayload(**event.data)

        # Access validated data via payload attributes
        logger.info(f"Processing task event for {payload.task_id}, status: {payload.status}")
        # ... proceed with handler logic using payload ...

    except ValidationError as e:
        logger.error(f"Event payload validation failed for event {event.event_id}: {e}")
        logger.debug(f"Invalid payload data: {event.data}")
        # Optionally publish an error event detailing the validation failure
        # self.publish_agent_error("Payload validation failed", details={"error": str(e), "payload": event.data}, correlation_id=event.correlation_id)
    except Exception as e:
        logger.exception(f"Unexpected error processing event {event.event_id}: {e}")
        # Handle other potential errors during processing

```

- **Pros:** Robust type checking, clear definition of expected structure,
  automatic error messages, handles nested data, less boilerplate code in the
  handler.
- **Cons:** Requires defining Pydantic models for expected payloads.

## Error Handling

When validation fails:

- **Log Clearly:** Log an error specifying which validation failed and include
  the problematic event data (or relevant parts) and event ID.
- **Avoid Crashing:** Handlers should generally catch validation errors and
  return gracefully rather than crashing the agent.
- **(Optional) Publish Error Event:** Consider publishing a `SYSTEM_ERROR` or
  `AGENT_ERROR` event to notify the system or the event source about the
  malformed event. Include the original event ID and correlation ID if
  available.
- **Graceful Degradation:** Decide if the handler can partially proceed or if
  the entire operation must be aborted upon validation failure.

By implementing these practices, agent handlers become more resilient and
contribute to the overall stability and reliability of the Dream.OS swarm.
