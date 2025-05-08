# Architecture & Design Documents

This directory holds high-level architecture diagrams, design documents, decision records (ADRs), and any other documentation that explains the overall structure and design choices of the project.

## Core Architectural Tenets (Summary)

The Dream.OS architecture is built upon several key principles and patterns observed across its components:

*   **Agent-Based Design:** The system operates as a swarm of specialized, autonomous agents, each responsible for specific functions (e.g., task execution, coordination, UI interaction, code analysis).
*   **Centralized Coordination & Task Management:** Core components like the AgentBus (for messaging), TaskNexus/ProjectBoardManager (for task lifecycle), and potentially a Capability Registry facilitate inter-agent communication and workflow orchestration.
*   **Modular Structure:** Code is organized into logical packages within `src/dreamos/` (e.g., `core`, `coordination`, `agents`, `services`, `integrations`, `utils`) to promote separation of concerns and maintainability.
*   **Asynchronous Operations:** `asyncio` is utilized for non-blocking I/O, particularly in components interacting with external services (API Clients) or the AgentBus.
*   **Configuration Management:** System settings, paths, and parameters are managed centrally via the `AppConfig` system (`src/dreamos/config.py`), promoting consistency and testability.
*   **File-System Persistence (with Considerations):** Several coordination mechanisms (e.g., Agent Mailboxes, proposed Meeting/Debate systems) leverage structured directories and files (often JSON) within `runtime/`. This necessitates careful handling of concurrency (e.g., file locking). Database alternatives (SQLite) are used or proposed for more robust state management (e.g., DbTaskNexus, AgentCommsV2).

## Core Architecture & Structure

*   **Core Auto-Fix Loop:** See the diagram in the main [README.md](../../README.md#architecture).
*   **Project Structure Guidelines:** Refer to the section in the [Developer Guide](../../docs/DEVELOPER_GUIDE.md#project-structure-guidelines).
*   **ChatGPT-Cursor Bridge Analysis:** Detailed breakdown in [docs/architecture/bridge_intel_agent5.md](../../docs/architecture/bridge_intel_agent5.md).

## Specific System/Feature Architectures

*   **Agent Meeting System:** [docs/architecture/agent_meeting_system.md](../../docs/architecture/agent_meeting_system.md)
*   **Agent Debate Arena:** [docs/architecture/agent_debate_arena.md](../../docs/architecture/agent_debate_arena.md)
*   **Digital Dreamscape (Narrative Engine):** [docs/architecture/digital_dreamscape.md](../../docs/architecture/digital_dreamscape.md)
*   **Social Media Manager:** [docs/architecture/social_media_manager.md](../../docs/architecture/social_media_manager.md)
*   **ChatGPT-Cursor Bridge (UI/API Focus):** [docs/architecture/chatgpt_cursor_bridge.md](../../docs/architecture/chatgpt_cursor_bridge.md)
*   **Agent Capability Registry:** [docs/architecture/agent_capability_registry.md](../../docs/architecture/agent_capability_registry.md)

## Design Proposals & Considerations

*   **Automated Devlog Hook:** [docs/designs/automated_devlog_hook.md](../../docs/designs/automated_devlog_hook.md)
*   **Agent Communication V2 (Persistence, ACK/NACK, DLQ):** [docs/designs/agent_comms_v2_proposal.md](../../docs/designs/agent_comms_v2_proposal.md)

This README serves as an index to the detailed architecture and design documents found primarily within the `docs/architecture/` and `docs/designs/` directories. 