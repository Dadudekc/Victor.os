# Dream.OS Codebase Overview

## Mission

To systematically organize the Dream.OS codebase, establish clear documentation standards, ensure functional correctness, and facilitate collaborative development using autonomous agents.

## High-Level Structure

The Dream.OS project aims for a clean and modular architecture. Key top-level directories and their intended purposes are:

*   `ai_docs/`: Persistent knowledge base for agents, covering best practices, API documentation, architecture notes, business logic, and more. 
    *   **Status Note (Agent-8, <TIMESTAMP>):** This directory is part of a planned documentation reorganization (see `specs/detailed_reorganization_plan_phase2.md` and `specs/plans/docs_path_mapping.json`). It is intended to be the future primary location for much of the content currently in `/docs` and other knowledge sources. As of this review, the `ai_docs/` directory has not yet been created at the workspace root, or the migration is incomplete. The reorganization plan should be fully executed, or documentation (including this README) updated to reflect its planned (but not yet active) status.
*   `specs/`: Agentic planning and coordination documents, including the `current_plan.md`.
*   `src/dreamos/`: The main application source code for the Dream.OS core framework and components.
    *   `agents/`: Specific agent implementations.
    *   `core/`: Fundamental framework logic.
    *   `coordination/`: AgentBus, task management, base agent logic.
    *   `services/`: Shared services like configuration loading, logging.
    *   `integrations/`: Connectors to external systems (LLMs, APIs, databases).
    *   `utils/`: Common shared utilities.
    *   `schemas/`: Pydantic data models.
    *   And various other specialized modules (GUI, chat engine, automation, etc.).
*   `tests/`: Unit and integration tests, mirroring the `src/dreamos` structure.
*   `scripts/`: Utility and operational scripts.
*   `runtime/`: Ephemeral runtime data such as logs, events, reports, and configuration.
*   `docs/`: User and developer documentation (e.g., architecture, design documents).
*   `templates/`: Project-wide templates (e.g., Jinja2 for prompts, reports).
*   `prompts/`: LLM prompt templates.

For a detailed current layout, refer to `specs/project_tree.txt`. The `specs/current_plan.md` outlines ongoing organizational tasks and the evolving target structure. 