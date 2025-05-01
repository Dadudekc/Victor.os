# AgentBus Usage (`src/dreamos/core/comms/agent_bus.py`)

This document explains the standard way to use the `AgentBus` for inter-agent
communication.

## Purpose

The `AgentBus` provides a publish/subscribe mechanism for broadcasting events
across the swarm. It's suitable for one-to-many communication where the sender
doesn't need to know who specifically receives the event.

For direct one-to-one communication, use Agent Mailboxes
(`runtime/agent_comms/agent_mailboxes/`).

## Core Concepts

- **Events:** Information is broadcast as `BaseEvent` objects (or subclasses).
  See `src/dreamos/core/comms/events.py`.
- **Topics:** Events are published to specific string-based topics (e.g.,
  `agent.status.update`, `system.error`, `task.completed`).
- **Subscriptions:** Agents subscribe to topics they are interested in using
  callback functions.
- **Publishing:** Agents publish events to relevant topics.

## Standard Usage (within `BaseAgent` or similar)

Most agents inherit from `BaseAgent`, which typically provides an
`self.agent_bus` instance.

**1. Subscribing to Events:**

```python
from src.dreamos.core.comms.events import BaseEvent, AgentStatusEvent # Example

class MyAgent(BaseAgent):
    def __init__(self, agent_id, agent_bus, ...):
        super().__init__(agent_id, agent_bus, ...)
        # Subscribe during initialization
        self.agent_bus.subscribe("agent.status.update", self.handle_status_update)
        self.agent_bus.subscribe("system.shutdown", self.handle_shutdown)

    def handle_status_update(self, event: AgentStatusEvent):
        # Ensure type checking if specific event subclass is expected
        if isinstance(event, AgentStatusEvent):
            print(f"Agent {self.agent_id} received status update from {event.payload.get('agent_id')}: {event.payload.get('status')}")
            # Process the event payload...
        else:
            print(f"Agent {self.agent_id} received unexpected event type on agent.status.update topic.")

    def handle_shutdown(self, event: BaseEvent):
        print(f"Agent {self.agent_id} received shutdown signal. Initiating cleanup...")
        # Perform cleanup actions...
        self.stop()

    # ... other methods ...
```

**2. Publishing Events:**

```python
from src.dreamos.core.comms.events import BaseEvent, AgentStatusEvent # Example

class MyAgent(BaseAgent):
    # ... (init, subscribe methods) ...

    def report_status(self, current_status: str, task_id: str):
        payload = {
            "agent_id": self.agent_id,
            "status": current_status,
            "current_task_id": task_id,
            # Add other relevant details
        }
        # Use a specific Event subclass if available
        status_event = AgentStatusEvent(source=self.agent_id, payload=payload)
        # OLD: self.agent_bus.publish("agent.status.update", status_event)
        # NEW: Use EventType
        self.agent_bus.publish(EventType.SYSTEM_AGENT_STATUS_CHANGE, status_event)
        print(f"Agent {self.agent_id} published status update.")

    def report_error(self, error_message: str, details: dict):
        payload = {
            "agent_id": self.agent_id,
            "error_message": error_message,
            "details": details
        }
        # Can use BaseEvent for generic errors or create a specific ErrorEvent class
        error_event = BaseEvent(source=self.agent_id, payload=payload)
        # OLD: self.agent_bus.publish("system.error", error_event)
        # NEW: Use EventType
        self.agent_bus.publish(EventType.SYSTEM_ERROR, error_event)
        print(f"Agent {self.agent_id} published system error.")
```

## Best Practices

- **Standardize Topics:** Agree on a clear, hierarchical topic naming
  convention.
- **Standardize Events:** Define specific `BaseEvent` subclasses for common
  event types (e.g., `TaskCompletedEvent`, `AgentReadyEvent`) with well-defined
  payload schemas (ideally using dataclasses - see Task `ENHANCE-EVENTS-001`).
- **Payloads:** Keep payloads concise and include only necessary information.
- **Error Handling:** Implement error handling within your callback functions.
- **Unsubscription:** If an agent needs to stop listening, implement
  unsubscription logic (see Task `ENHANCE-AGENTBUS-001`). Currently,
  subscriptions are typically permanent for the agent's lifetime.
- **Avoid Overuse:** Don't use the AgentBus for large data transfers or
  request/response patterns; use mailboxes or dedicated services for those.
