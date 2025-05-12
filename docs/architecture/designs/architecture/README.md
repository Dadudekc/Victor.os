# Architecture & Design Documents

This directory holds high-level architecture diagrams, design documents, decision records (ADRs), and any other documentation that explains the overall structure and design choices of the project.

## Core Architectural Tenets (Summary)

Dream.OS is an experimental, **autonomous software development platform** designed to operate as a "swarm" of specialized AI agents. Its primary goal is automating complex tasks, particularly those related to **software development, code analysis, task execution, and self-improvement**. It aims to function as a specialized environment or "Operating System" where different AI agents collaborate to build, maintain, and evolve software (including Dream.OS itself).

The architecture is built upon several key principles and patterns:

*   **Agent-Based Design:** The system operates as a swarm of specialized, autonomous agents (e.g., `PlannerAgent`, `AutoFixerAgent`), each responsible for specific functions. Agents reside in `src/dreamos/agents/`.
*   **Centralized Coordination & Task Management:** Core components facilitate inter-agent communication and workflow orchestration:
    *   `AgentBus` (`src/dreamos/coordination/agent_bus.py`): Asynchronous message broker.
    *   `ProjectBoardManager` (`src/dreamos/coordination/project_board_manager.py`): Manages the task lifecycle across JSON files using the flow: `task_backlog.json` → `task_ready_queue.json` → `working_tasks.json` → `completed_tasks.json`.
*   **Modular Structure:** Code is organized into logical packages within `src/dreamos/` (e.g., `core`, `coordination`, `agents`, `tools`, `services`, `integrations`, `utils`) to promote separation of concerns and maintainability.
*   **Tool Usage:** Agents utilize shared tools (`src/dreamos/tools/`) for common functionalities like file editing (e.g., `edit_file.py`), code analysis (`ProjectScanner`), etc.
*   **External Integrations:** Connects with external tools and services:
    *   **Cursor IDE:** Uses GUI automation (PyAutoGUI) for interactions.
    *   **ChatGPT/LLMs:** Uses web scraping (Selenium/Undetected ChromeDriver) or direct API calls.
*   **Asynchronous Operations:** `asyncio` is utilized for non-blocking I/O, particularly in components interacting with external services or the `AgentBus`.
*   **Configuration Management:** System settings, paths, and parameters are managed centrally via the `AppConfig` system (`src/dreamos/config.py`) and configuration files (e.g., `config/config.yaml`), promoting consistency and testability.
*   **File-System Persistence (with Considerations):** Several coordination mechanisms (e.g., Agent Mailboxes, Task Boards) leverage structured directories and files (often JSON) within `runtime/`. This necessitates careful handling of concurrency (e.g., file locking).
*   **Self-Correction/Improvement:** Agents are expected to operate continuously and follow protocols (like the `DRIFT CONTROL & SELF-CORRECTION PROTOCOL`) for autonomous improvement and handling deviations.

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

## Key Architectural Documents

Below is a list of key architectural documents currently available. Agents are encouraged to consult these for understanding specific systems and to contribute new documents or update existing ones as the project evolves.

*   **[PyAutoGUI-ChatGPT Bridge Overview (v1.0)](./pyautogui_chatgpt_bridge_overview_v1.md)**
    *   Describes the architecture of the bridge facilitating interaction between Dream.OS and the Cursor IDE, including its components (`cursor_bridge.py`, `http_bridge_service.py`), configuration, and operational flow.

*   **[PyAutoGUI Bridge Component Map (PF-BRIDGE-INT-001)](./PF-BRIDGE-INT-001_PyAutoGUI_Component_Map.md)**
    *   Details the component mapping and initial design considerations for the PyAutoGUI bridge integration.

*   **[Scraper Metadata Integration - Phase 1 (PIPE-003)](./PIPE-003_ScraperMetadataIntegration_Phase1.md)**
    *   Initial report on integrating context metadata from scrapers.

*   **[Bus Correlation Validation Design](./bus_correlation_validation_design.md)**
    *   Design document for validating message correlation on the agent bus.


## Contributing

When adding new architectural documents, please:

*   Use a clear and descriptive filename (e.g., `[component_name]_architecture_v[version].md`).
*   Include versioning and status information in the document.
*   Aim for clarity and provide diagrams or code snippets where helpful.
*   Update this README to include a link to your new document. 