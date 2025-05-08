# Project-Specific Design Patterns

This document aims to identify and describe recurring design patterns, architectural motifs, and common solutions used throughout the Dream.OS codebase. Documenting these patterns helps maintain consistency, improves understanding for new contributors, and facilitates reuse.

## Identified Patterns

### 1. Agent-Based Design
*   **Description:** Core system functionality is encapsulated within specialized, autonomous agents. Each agent typically has a defined responsibility or role within the swarm.
*   **Context:** Used for breaking down complex problems into manageable, independently operating units.
*   **Examples:** `AutoFixerAgent`, `PlannerAgent` (in Dreamscape), various agents for UI interaction or code analysis.
*   **Further Investigation:** Common base classes for agents (e.g., `BaseAgent`), standard agent lifecycle methods, state management approaches, typical communication patterns between agents.

### 2. Centralized Coordination & Task Management
*   **Description:** Key components orchestrate agent interactions and manage the lifecycle of tasks.
*   **Context:** Ensures orderly processing, prevents conflicts, and provides a unified view of ongoing work.
*   **Examples:** `AgentBus` for messaging, `TaskNexus` or `ProjectBoardManager` for task assignment and status tracking, potential `CapabilityRegistry`.
*   **Further Investigation:** Specific protocols used on the AgentBus, structure of task definitions, interaction patterns with the task management system.

### 3. Modular Package Structure
*   **Description:** The codebase is organized into logical packages within `src/dreamos/` (e.g., `core`, `coordination`, `agents`, `services`, `integrations`, `utils`).
*   **Context:** Promotes separation of concerns, maintainability, and reusability.
*   **Examples:** The overall directory structure under `src/dreamos/`.
*   **Further Investigation:** Adherence to dependency rules between modules, common interfaces between modules.

### 4. Asynchronous Operations (`asyncio`)
*   **Description:** `asyncio` and `async/await` are used for non-blocking I/O operations, especially when dealing with external services or potentially long-running tasks.
*   **Context:** Improves responsiveness and efficiency for I/O-bound operations.
*   **Examples:** API clients in `src/dreamos/integrations/`, potentially AgentBus communication.
*   **Further Investigation:** Consistent error handling in async code, management of event loops, use of `asyncio` synchronization primitives.

### 5. Centralized Configuration Management (`AppConfig`)
*   **Description:** System settings, paths, API keys, and other parameters are managed centrally, typically through an `AppConfig` system (e.g., loaded from `src/dreamos/config.py` or `runtime/config/`).
*   **Context:** Provides a single source of truth for configuration, facilitates environment-specific settings, and improves testability.
*   **Examples:** Initialization of API clients, setting logging levels, defining file paths.
*   **Further Investigation:** How configuration is loaded, accessed, and potentially overridden for different environments or tests.

### 6. File-System Persistence (with Database Alternatives)
*   **Description:** Several coordination mechanisms and data stores leverage structured directories and files (often JSON) within `runtime/`. Databases (e.g., SQLite) are sometimes used or proposed for more complex state management.
*   **Context:** Provides a simple way to store state and messages, especially for inter-process communication or agent mailboxes. Databases offer more robust querying and transactional integrity.
*   **Examples:** Agent mailboxes, `future_tasks.json`, `working_tasks.json`, proposed Meeting/Debate systems. `DbTaskNexus` as a DB-backed task manager.
*   **Further Investigation:** File locking mechanisms, data serialization formats, schema validation for file-based data, patterns for migrating from file-based to DB-based persistence.

### 16. DB-Backed Registry with Cache
*   **Description:** A registry class (`CapabilityRegistry`) manages data (e.g., agent capabilities) persisted in an SQLite database via an adapter, while maintaining an in-memory cache for faster read access.
*   **Context:** Provides persistent storage for registry data combined with performant reads for frequent lookups.
*   **Examples:** `CapabilityRegistry` in `src/dreamos/core/tasks/nexus/capability_registry.py`.
*   **Further Investigation:** Cache consistency strategy (invalidation/refresh), error handling propagation from DB adapter.

### 17. Async Facade for Sync Logic
*   **Description:** An `async` handler class (`CapabilityHandler`) wraps a synchronous class (`CapabilityRegistry`) that performs blocking operations (like DB access or synchronous cache lookups).
*   **Context:** Allows synchronous business logic or data access layers to be safely called from an asynchronous application without blocking the event loop, typically using `asyncio.to_thread`.
*   **Examples:** `CapabilityHandler` wrapping `CapabilityRegistry` in `src/dreamos/core/tasks/nexus/capability_handler.py`.
*   **Further Investigation:** Necessity of the facade if the underlying synchronous component can be made natively async.

*(This section will be further populated as more specific implementation patterns are identified and analyzed.)*

### Potential Areas for Further Pattern Identification:

*   **Agent Design:** Common base classes, lifecycle methods, state management, communication protocols specific to agents.
*   **Service Initialization & Management:** How are shared services (e.g., logging, configuration, API clients) instantiated and accessed?
*   **Task Processing Pipelines:** Standard ways tasks are received, validated, executed, and their results handled.
*   **Integration Wrappers:** Common approaches for abstracting external APIs or tools.
*   **Data Handling & Schemas:** Patterns in using Pydantic models for data validation and serialization.
*   **Error Handling & Retries:** Consistent use of custom exceptions, `tenacity` for retries.
*   **Event-Driven Architecture:** Use of an AgentBus or similar eventing mechanisms.
*   **Configuration Loading:** Standard way `AppConfig` is used.

## How to Contribute

If you identify a recurring pattern or a common solution to a problem in the codebase that isn't documented here, please consider adding it. Describe the pattern, its context, the problem it solves, and provide links to example implementations.

## 📎 Linked Documents

- *(Link to relevant architecture diagrams or design documents)*
- *(Example: [Agent Message Bus Pattern](./project_patterns/agent_message_bus.md))* 