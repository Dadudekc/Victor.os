# Dream.OS Agent Design Guidelines

This document outlines the core design principles and architectural standards for creating and maintaining agents within the Dream.OS ecosystem. Adherence to these guidelines is crucial for ensuring consistency, maintainability, and interoperability of agents.

## 1. Core Architectural Principle: Cursor-Client-Only Execution Model

**All agents that perform automated tasks requiring interaction with an external AI model or development environment must operate as Cursor client agents.**

This means:

*   **Primary Interaction via Cursor:** Agents should not directly automate other UIs (e.g., web browsers for specific LLM services, other IDEs) if the same functionality can be achieved through the Cursor IDE.
*   **Prompt Injection:** The primary method of instructing a Cursor client agent (or the underlying Cursor instance it controls) is via prompt injection.
*   **Mailbox Loops & Event-Driven Architecture:** Agents are driven by messages or events received through defined "mailboxes" or, more broadly, the `AgentBus`. They listen for specific event types (e.g., `TASK_COMMAND`, `CURSOR_INJECT_REQUEST`) or messages in their designated mailbox, process them, and then typically return to a listening state.

**Rationale:**
*   **Standardization:** Provides a uniform way to interact with and manage task execution.
*   **Decoupling:** Separates task definition and orchestration from the mechanics of UI automation.
*   **Centralized Control & Monitoring:** Allows for easier monitoring, logging, and intervention via the `AgentBus` and Cursor interaction points.
*   **Simplified Agent Logic:** Agents focus on their specific domain logic (e.g., infrastructure tasks, response processing) rather than complex UI automation details, which are handled by dedicated Cursor interaction services (e.g., `CursorOrchestrator`).

## 2. Agent Archetypes

Based on the core principle, agents generally fall into these categories:

### 2.1. Cursor Interaction Delegates (Cursor Client Agents)
*   **Role:** These are the agents/services directly responsible for UI automation of the Cursor IDE. They listen for requests (like `CURSOR_INJECT_REQUEST`) on the `AgentBus` and execute them.
*   **Example:** `CursorOrchestrator` (or similar worker agents it might manage).
*   **Key Characteristics:**
    *   Directly use UI automation libraries (e.g., PyAutoGUI, Selenium if Cursor were web-based for some reason, etc.) specifically for Cursor.
    *   Subscribe to specific low-level command events on the `AgentBus`.
    *   Publish low-level success/failure events (e.g., `CURSOR_RETRIEVE_SUCCESS`).

### 2.2. Task Formulator & Orchestration Agents
*   **Role:** These agents define *what* needs to be done by Cursor. They break down higher-level goals into specific prompts or sequences of prompts. They then dispatch these as tasks or command events via the `AgentBus` to be picked up by Cursor Interaction Delegates or other relevant agents.
*   **Example:** `Agent2InfraSurgeon`, `TaskExecutorAgent` (if its role is to dispatch tasks to Cursor-interacting agents).
*   **Key Characteristics:**
    *   Do **not** perform UI automation themselves.
    *   Publish `TASK_COMMAND` or `CURSOR_INJECT_REQUEST` events.
    *   May manage task state, dependencies, and retries (e.g., `RecoveryCoordinatorAgent`).
    *   Subscribe to higher-level system events or process tasks from a queue.

### 2.3. System Support & Utility Agents
*   **Role:** Provide essential background services, monitoring, or data transformation that supports the overall agent ecosystem but do not directly execute tasks in Cursor or formulate them.
*   **Example:** `RecoveryCoordinatorAgent` (monitors and retries tasks), `Agent9ResponseInjector` (transforms one event type to another to bridge systems).
*   **Key Characteristics:**
    *   Operate based on system events or scheduled checks.
    *   Interact primarily via the `AgentBus`.
    *   Do not typically publish `CURSOR_INJECT_REQUEST` events directly but may trigger other agents that do.

### 2.4. Legacy or Non-Standard Agents (To Be Phased Out or Re-Evaluated)
*   **Role:** Agents that do not conform to the Cursor-client-only model. This includes agents directly automating other UIs (like web browsers for specific services if Cursor can provide similar access) or using outdated communication patterns (e.g., custom file-based channels instead of `AgentBus`).
*   **Example (Hypothetical/Past):** `SupervisorAgent` (using `LocalBlobChannel`), `ChatGPTWebAgent` (if direct web interaction is deemed replaceable by Cursor's LLM capabilities).
*   **Action:** These agents should be refactored to align with the standard architecture or be deprecated if their functionality is superseded or no longer strategically required.

## 3. Required Interfaces & Event Patterns (Mailbox-Driven Injection)

To ensure interoperability, agents involved in task execution via Cursor should adhere to common event patterns:

*   **`CURSOR_INJECT_REQUEST` (Event Type):**
    *   **Purpose:** Signals a request to inject a prompt into a specific Cursor agent's UI (or a generally available Cursor instance).
    *   **Publisher:** Typically a Task Formulator agent (e.g., `Agent2InfraSurgeon`).
    *   **Subscriber:** Cursor Interaction Delegate (e.g., `CursorOrchestrator`).
    *   **Key Payload Fields:** `target_agent_id` (or similar identifier for the Cursor instance/window), `prompt_text`, `correlation_id`.

*   **`CURSOR_OPERATION_RESULT` (Event Type - formerly `CURSOR_RETRIEVE_SUCCESS`/`FAILURE`):**
    *   **Purpose:** Reports the outcome of a Cursor UI operation (injection, copy, etc.).
    *   **Publisher:** Cursor Interaction Delegate.
    *   **Subscriber:** The original requester (e.g., `Agent2InfraSurgeon`) or other interested system components.
    *   **Key Payload Fields:** `correlation_id`, `status` (`SUCCESS`/`FAILURE`), `operation_type` (`inject`, `retrieve`), `message` (for errors), `retrieved_content` (if applicable).

*   **`TASK_COMMAND` (Event Type):**
    *   **Purpose:** A more general event to command an agent to perform a task described in the payload. This can be used to initiate a task that might involve Cursor interaction.
    *   **Publisher:** Orchestration agents, other agents.
    *   **Subscriber:** Agents capable of handling the specified task type (e.g., `Agent2InfraSurgeon` for infrastructure tasks).
    *   **Key Payload Fields:** `task_id`, `task_type`, `params` (which might include the prompt for Cursor), `target_agent_id`.

*   **Task Lifecycle Events (various types, e.g., `TASK_STATUS_UPDATE`):**
    *   **Purpose:** Communicate changes in a task's state (e.g., `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`).
    *   **Publisher:** Agents responsible for managing or executing tasks.
    *   **Subscriber:** Orchestrators, monitoring systems, `RecoveryCoordinatorAgent`.

## 4. Configuration and State

*   **Configuration via `AppConfig`:** Agents should receive their configuration via the central `AppConfig` object, passed during instantiation. Avoid direct file reads for configuration within agent logic where possible.
*   **State Management:** Prefer explicit state management via dedicated services (e.g., `PersistentTaskMemoryAPI`) or clear `AgentBus` event patterns rather than relying on local file-based state that is not visible to the wider system.

By adhering to these guidelines, Dream.OS can maintain a robust, scalable, and understandable agent architecture. 