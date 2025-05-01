# Dream.OS Developer Guide

This guide provides instructions and best practices for developing Agents within
the Dream.OS framework.

## Table of Contents

- [Introduction](#introduction)
- [Agent Lifecycle](#agent-lifecycle)
- [Agent Communication](#agent-communication)
  - [AgentBus](#agentbus)
  - [Message Patterns](#message-patterns)
- [Creating a New Agent](#creating-a-new-agent)
- [Using Hooks](#using-hooks)
- [Agent Registration](#agent-registration)
- [Best Practices](#best-practices)

## Introduction

Dream.OS Agents are modular components responsible for specific tasks or
functionalities within the system. They operate independently but communicate
and coordinate through the central `AgentBus`.

## Agent Lifecycle

Agents in Dream.OS follow a defined lifecycle managed by the core orchestrator.
Key phases typically include:

1.  **Initialization (`__init__`)**: Set up initial state, dependencies.
2.  **Registration**: The agent makes itself known to the system (often handled
    implicitly or via configuration).
3.  **Running**: The agent actively performs its tasks, listens for messages,
    and interacts with the `AgentBus`. (Specific methods like `start`, `run`, or
    event handlers depend on the `BaseAgent` implementation).
4.  **Termination/Shutdown**: Clean up resources, save state if necessary.

_(Note: Refer to `src/dreamos/core/coordination/base_agent.py` for the exact
lifecycle methods and their expected behavior.)_

## Agent Communication

### AgentBus

The `AgentBus` (`src/dreamos/agent_bus.py`) is the central message broker for
inter-agent communication. Agents use it to:

- **Publish messages**: Send information or requests to other agents.
- **Subscribe to topics**: Listen for specific types of messages relevant to
  their function.

Consult the `AgentBus` class documentation for specific methods like `publish`,
`subscribe`, etc.

### Message Patterns

Standardized message patterns ensure consistent communication. Key patterns
observed include:

- **Request/Reply**: One agent sends a request, expecting a specific reply from
  another.
- **Publish/Subscribe**: An agent publishes information to a topic, and multiple
  subscribers can receive it.
- **Voting/Consensus**: Used for distributed decision-making, potentially
  involving patterns like those in
  `src/dreamos/core/coordination/message_patterns.py` and the previously
  examined `voting_patterns.py`.

Define clear message schemas (e.g., using Pydantic models or dataclasses) for
robustness.

## Creating a New Agent

To create a new agent:

1.  **Define the Agent Class**: Create a new Python class that inherits from
    `dreamos.core.coordination.base_agent.BaseAgent`.
2.  **Implement Required Methods**: Override necessary methods from `BaseAgent`
    (e.g., `__init__`, lifecycle methods, message handlers).
3.  **Define Agent Logic**: Implement the core functionality of your agent.
4.  **Register the Agent**: Ensure the system can discover and load your agent
    (see Agent Registration).

```python
# Example structure (adapt based on BaseAgent actual methods)
from dreamos.core.coordination.base_agent import BaseAgent
from dreamos.agent_bus import AgentBus

class MyNewAgent(BaseAgent):
    def __init__(self, agent_id: str, agent_bus: AgentBus, config: dict):
        super().__init__(agent_id, agent_bus)
        self.config = config
        # ... other initializations ...

    async def start(self):
        # Subscribe to relevant topics
        await self.agent_bus.subscribe("some/topic", self.handle_message)
        print(f"{self.agent_id} started and listening.")

    async def handle_message(self, topic: str, payload: dict):
        print(f"{self.agent_id} received message on {topic}: {payload}")
        # ... process message ...

    async def stop(self):
        # Cleanup resources
        print(f"{self.agent_id} stopping.")
        # Unsubscribe, close connections, etc.
```

## Using Hooks

Hooks (`src/dreamos/hooks/`) provide extension points to modify or augment
system behavior at specific lifecycle events or actions without altering core
code.

- **Discover Available Hooks**: Check the `src/dreamos/hooks/` directory and
  potentially a registration mechanism.
- **Implement a Hook**: Create a function or class conforming to the required
  hook signature.
- **Register the Hook**: Use the system's mechanism (e.g., configuration,
  decorators) to register your hook implementation.

## Agent Registration

How agents are discovered and loaded into the system:

- **Discovery**: The system might automatically scan specific directories (e.g.,
  `src/dreamos/agents/`) for classes inheriting from `BaseAgent`.
- **Configuration**: Agents might be explicitly listed in a configuration file
  (e.g., YAML, JSON).
- **Dynamic Loading**: The orchestrator or CLI might load agents based on
  commands or runtime parameters.

_(Clarify the exact mechanism used in Dream.OS based on orchestrator/CLI
implementation.)_

## Best Practices

- **Keep Agents Focused**: Each agent should have a single, well-defined
  responsibility.
- **Use Asynchronous Operations**: Leverage `asyncio` for non-blocking I/O,
  especially when interacting with the `AgentBus` or external services.
- **Define Clear Message Schemas**: Use data classes or Pydantic models for
  message payloads.
- **Handle Errors Gracefully**: Implement robust error handling and logging
  within agents.
- **Use the AgentBus**: Avoid direct agent-to-agent calls; use the bus for
  decoupling.
- **Manage State Carefully**: Be mindful of agent state, especially in a
  distributed or concurrent environment.
- **Write Unit Tests**: Test agent logic and message handling independently.

## Project Structure Guidelines

*(Consolidated from Developer Notes)*

Maintaining a consistent and logical project structure is crucial for scalability and maintainability.

- **Core Logic Location**: All core Python source code for Dream.OS components (agents, services, utilities) MUST reside within the `src/dreamos/` directory.
- **Sub-package Organization**: Within `src/dreamos/`, code should be organized into logical sub-packages based on functionality:
    - `agents/`: Contains individual agent implementations.
    - `coordination/`: Components related to agent communication, task management, and orchestration (e.g., `AgentBus`, `ProjectBoardManager`, `BaseAgent`).
    - `services/`: Shared services used by agents (e.g., configuration loading, logging setup, potentially file management, external API clients).
    - `utils/`: General-purpose utility functions not specific to a single agent or service.
    - `schemas/` or `models/`: Data models, Pydantic models, or schemas used across the system.
    - `hooks/`: Extension points.
    - *(Other specific areas like `memory/`, `gui/`, `chat_engine/`, etc. should follow this pattern)*
- **Avoid Root Clutter**: Do not place Python modules directly in the `src/dreamos/` root. They should belong to a sub-package.
- **Test Structure**: Unit and integration tests MUST reside in the top-level `tests/` directory, mirroring the structure of `src/dreamos/` (e.g., tests for `src/dreamos/coordination/agent_bus.py` should be in `tests/coordination/test_agent_bus.py`).
- **Configuration**: Runtime configuration files (e.g., `config.yaml`) should ideally be located in a dedicated directory like `runtime/config/`.
- **Scripts/Tools**: Utility scripts or standalone tools should be placed in a top-level `scripts/` or `tools/` directory, not within the main `src/` tree.
- **Import Paths**: Use relative imports within the `src/dreamos/` package where appropriate, or absolute imports starting from `dreamos.` (assuming `src` is in the Python path). Avoid complex `sys.path` manipulations.
- **Consistency**: Follow naming conventions (e.g., `snake_case` for files and variables, `PascalCase` for classes) as established in the project (refer to `docs/naming.md` if available).
