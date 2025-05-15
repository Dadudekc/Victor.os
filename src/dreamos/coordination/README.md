# Dream.OS Coordination Package

This is the central coordination package for Dream.OS, providing core mechanisms for agent communication, task management, and system orchestration.

## Directory Structure

```
coordination/
├── __init__.py           # Package initialization and exports
├── agent_bus.py          # Central message bus for inter-agent communication
├── base_agent.py         # Base class for all Dream.OS agents
├── base_agent_lifecycle.py # Agent lifecycle management
├── project_board_manager.py # Project and task management
├── event_payloads.py     # Event payload definitions
├── event_types.py        # Event type definitions
├── message_patterns.py   # Common message patterns
├── enums.py             # Shared enumerations
└── schemas/             # JSON schemas for validation
```

## Core Components

### AgentBus
The central message bus that enables communication between agents. Handles message routing, event dispatch, and communication patterns.

### BaseAgent
The foundational agent class that all Dream.OS agents inherit from. Provides core lifecycle management and communication capabilities.

### ProjectBoardManager
Manages the project board, tasks, and overall system state. Coordinates task assignment and tracking.

### Event System
- `event_types.py`: Defines all possible event types in the system
- `event_payloads.py`: Defines the structure of event payloads
- `message_patterns.py`: Implements common communication patterns

## Usage

```python
from dreamos.coordination import AgentBus, BaseAgent, ProjectBoardManager
from dreamos.coordination.event_types import EventType
from dreamos.coordination.event_payloads import EventPayload

# Create an agent
class MyAgent(BaseAgent):
    async def handle_event(self, event: EventPayload) -> None:
        # Handle events here
        pass

# Initialize components
agent_bus = AgentBus()
board_manager = ProjectBoardManager()
```

## Development

When adding new coordination features:
1. Define any new event types in `event_types.py`
2. Define corresponding payloads in `event_payloads.py`
3. Update schemas in the `schemas/` directory
4. Add tests to `tests/coordination/`

## Migration Note

This package consolidates coordination functionality previously spread across multiple locations:
- `archive/orphans/core/coordination/`
- `docs/agents/coordination/`
- `specs/` (coordination-related files)

All coordination code should now live in this central location. 