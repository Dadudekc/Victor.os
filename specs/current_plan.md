# Current Project Plan

## Overall Mission:
[Define the overarching goal of the project here]

## Key Objectives:
1. [Objective 1]
2. [Objective 2]
3. [Objective 3]

## Phases / Milestones:
- **Phase 1: [Name]**
  - Task 1.1
  - Task 1.2

## Notes for Agents:
- [Any general guidelines or important context for agents working on this plan]

# Agentic Coding Plan - Project Organization

**Mission:** To systematically organize the codebase, establish clear documentation standards, ensure functional correctness, and facilitate collaborative development using autonomous agents.

**Target Structure (Based on Developer Guide - V2 Proposal):**

```
.
├── ai_docs/                 # Persistent knowledge base (Best Practices, APIs, Arch, Logic...)
│   ├── api_docs/
│   ├── architecture/
│   ├── best_practices/
│   ├── business_logic/
│   ├── codebase_overview/   # // TODO: Populate this
│   ├── implementation_notes/# // TODO: Populate this (from TODOs/FIXMEs)
│   ├── onboarding/          # // TODO: Populate this
│   └── project_patterns/    # // TODO: Populate this
├── specs/                   # Agentic planning & coordination
│   ├── current_plan.md      # This file
│   ├── automation_tasks/    # // TODO: Define automation tasks
│   └── archive/             # Completed or superseded plans
├── src/                     # Main application source code
│   ├── __init__.py
│   └── dreamos/             # Core framework components
│       ├── __init__.py
│       ├── agents/          # Agent implementations
│       ├── core/            # Fundamental framework logic (base classes, events?)
│       ├── coordination/    # AgentBus, Task Management, BaseAgent, Orchestration
│       ├── services/        # Shared services (Config Loading, Logging Setup, etc.)
│       ├── integrations/    # Connectors (LLMs, APIs, Playwright, DBs, etc.)
│       ├── utils/           # Common shared utilities
│       ├── schemas/         # Data models/schemas (Pydantic)
│       ├── hooks/           # Extension points
│       ├── memory/          # Memory components
│       ├── gui/             # GUI interaction logic (e.g., for Cursor bridge)
│       ├── chat_engine/     # Components related to LLM interaction/parsing
│       ├── monitoring/      # System monitoring and health checks
│       ├── cli/             # Command-line interface logic
│       ├── automation/      # GUI Automation helpers (e.g. pyautogui wrappers) - Exists: src/dreamos/automation
│       ├── channels/        # // TODO: ORG-002 Clarify purpose (e.g., communication?)
│       ├── feedback/        # // TODO: ORG-002 Clarify purpose (e.g., user feedback processing?)
│       ├── identity/        # // TODO: ORG-002 Clarify purpose (agent identity mgmt?)
│       ├── reporting/       # // TODO: ORG-002 Clarify purpose (generating reports?)
│       ├── social/          # // TODO: ORG-002 Clarify purpose (social media integration?)
│       └── ...              # (Other existing dirs like supervisor_tools, llm_bridge need review/consolidation)
│   # --------------------------------------------------------------------------
│   # Directories below exist in src/ but may need moving/review for ORG-002:
│   # └── dreamscape/        # // TODO: ORG-002 Confirm location - Feature specific?
│   # └── tools/             # // TODO: ORG-002 Consolidate with top-level 'scripts/'?
│   # └── config_files/      # // TODO: ORG-002 Deprecate/Move contents to runtime/config/
│   # └── templates/         # // TODO: ORG-002 Consolidate with top-level 'templates/'?
│   # └── prompts/           # // TODO: ORG-002 Consolidate with top-level 'prompts/'?
│   # └── apps/              # // TODO: ORG-002 Consolidate with top-level 'apps/'?
│   # └── bridge/            # // TODO: ORG-002 Consolidate with top-level 'bridge/'?
│   # --------------------------------------------------------------------------
├── tests/                   # Unit/integration tests (mirrors src/dreamos structure)
│   └── ...
├── scripts/                 # Utility and operational scripts (Dev Guide recommendation)
├── runtime/                 # Ephemeral runtime data
│   ├── logs/
│   ├── events/
│   ├── reports/             # // NEW: Moved reports here
│   ├── config/              # Preferred location for config.yaml
│   ├── swarm_sync_state.json # Example swarm sync file
│   └── ...                  # (Other runtime dirs like agent_comms, agent_registry need review/consolidation)
├── docs/                    # User/developer documentation
│   ├── architecture/
│   ├── designs/
│   └── ...
├── assets/                  # Static assets (images, icons, etc.) // NEW
├── templates/               # Project-wide templates (e.g., Jinja) // NEW
├── prompts/                 # LLM Prompts // NEW
├── .github/                 # CI/CD workflows
├── pyproject.toml
├── requirements.txt         # // TODO: ORG-002 Consider consolidation with pyproject.toml
├── README.md
└── .gitignore
# ------------------------------------------------------------------------------
# Directories below exist top-level but need review/moving/deletion for ORG-002:
# - app/
# - apps/ (dupe?)
# - bridge/ (dupe?)
# - analytics/
# - archive/ & _archive/
# - audit/
# - sandbox/ & dev_sandbox/
# ------------------------------------------------------------------------------
```
👉 For full current project layout, see [project_tree.txt](./project_tree.txt)

**Mission Updates & Task Log:**

*   **ORG-001:** **Define initial `specs/current_plan.md` structure.** (Status: DONE - Initial version created) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-002:** **Define target directory structure.** (Status: In Progress - V2 Structure proposed, needs review & sub-tasks) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}} - Note: Review placement of `core/tasks/nexus` vs `coordination` vs `core/coordination`.
*   **ORG-003:** **Scan codebase and populate `ai_docs/best_practices/`.** (Status: DONE - Key principles summarized) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-004:** **Scan codebase and populate `ai_docs/api_docs/`.** (Status: DONE - Client summaries added) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-005:** **Scan codebase and populate `ai_docs/architecture/`.** (Status: DONE - Core tenets summarized) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-006:** **Scan codebase and populate `ai_docs/business_logic/`.** (Status: Done - Initial rules extracted) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-007:** **Populate `ai_docs/codebase_overview/`.** (Status: DONE - Overview drafted) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-008:** **Populate `ai_docs/implementation_notes/` (Scan for TODO/FIXME).** (Status: DONE - Initial notes summarized) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-009:** **Populate `ai_docs/onboarding/` (Consolidate existing info).** (Status: DONE - Central guide created) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-010:** **Populate `ai_docs/project_patterns/` (Analyze codebase for patterns).** (Status: DONE - Initial patterns documented) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-011:** **Define `specs/automation_tasks/`.** (Status: DONE - Initial categories defined) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-012:** **Clarify purpose of `src/dreamos/channels/`.** (Status: DONE - Provides communication/data exchange abstractions, e.g., LocalBlobChannel, AzureBlobChannel, for tasks, memory, C2. Also an EventHub channel. The term 'channel' is used more broadly for message destinations like Discord or content publishing targets.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-013:** **Clarify purpose of `src/dreamos/feedback/`.** (Status: DONE - Houses the FeedbackEngine (currently `FeedbackEngineV2` placeholder), intended to process feedback data and provide adjustments or new instructions for agents.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-014:** **Clarify purpose of `src/dreamos/identity/`.** (Status: DONE - Manages agent identities. Defines `AgentIdentity` model (ID, role, metadata, timestamps) and `AgentIdentityStore` (singleton) for persisting these to `runtime/identity/agent_identities.json`.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-015:** **Clarify purpose of `src/dreamos/reporting/`.** (Status: DONE - Contains modules for generating reports on agent activity/performance. `devlog_utils.py` creates indexes for agent devlogs. `scoring_analyzer.py` analyzes `runtime/tasks/completed_tasks.json` for metrics like success rates, scores, and retries, reporting overall and per agent. Generated reports are intended for `runtime/reports/`.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-016:** **Clarify purpose of `src/dreamos/social/`.** (Status: DONE - Manages automated social media presence. Includes content generation (Jinja templates in `templates/social/`, AI-assisted context analysis via `prompts/social/`), dispatching (`services/utils/devlog_dispatcher.py`), and core logic (`integrations/social/core/` with `SocialMediaAgent`, `PostContextGenerator`, `FeedbackProcessor`). May link to sub-projects like 'Digital Dreamscape.') - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-017:** **Confirm location/purpose of `src/dreamscape/`.** (Status: DONE - Location `src/dreamscape/` confirmed. It's the core "Digital Dreamscape" subsystem for autonomous devblog/"episode" content generation, planning, and publishing. Defines content models (`ContentPlan`), event types, and uses specialized agents. Integrates with Discord and the Dashboard. Serves as a library for the application in `src/dreamos/apps/dreamscape/` which includes the `dreamscape_generator`.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-018:** **Consolidate `src/dreamos/tools/` vs. top-level `scripts/`.** (Status: DONE - `src/dreamos/tools/` is a package for importable/runnable tooling modules. Top-level `scripts/` is for standalone operational scripts. The nested `src/dreamos/tools/scripts/` was found to be empty or non-existent and requires no action.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-019:** **Deprecate/Move `src/dreamos/config_files/`.** (Status: DONE - Directory found empty of actual configs, only an `__init__.py` which was deleted. Directory effectively removed. `runtime/config/` is the designated location for config files.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-020:** **Consolidate `src/dreamos/templates/` vs. top-level `templates/`.** (Status: DONE - Contents of `src/dreamos/templates/` (including `lore/` and `social/` subdirs) moved to top-level `templates/`. `src/dreamos/agents/cursor_dispatcher.py` updated to use new path. `AppConfig.paths.templates` needs review to ensure it points to top-level `templates/`. Original `src/dreamos/templates/` deleted.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-021:** **Consolidate `src/dreamos/prompts/` vs. top-level `prompts/`.** (Status: DONE - Contents of `src/dreamos/prompts/` (including `governance/` and `social/` subdirs) moved to top-level `prompts/`. Original `src/dreamos/prompts/` deleted. **Action Required:** Code references loading these prompts must be identified and updated to use the new top-level `prompts/` path.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-022:** **Consolidate `src/dreamos/apps/` vs. top-level `apps/`.** (Status: BLOCKED - Listing contents of `src/dreamos/apps/` and top-level `app/` failed due to timeouts. **Action Required:** Manually inspect contents of `src/dreamos/apps/` and `app/`, move them into the existing top-level `apps/` directory. Afterwards, perform necessary code refactoring to update import paths (e.g., `from dreamos.apps...` to `from apps...`) and ensure the top-level `apps/` directory is correctly configured as a source path.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-023:** **Consolidate `src/dreamos/bridge/` vs. top-level `bridge/`.** (Status: BLOCKED - Listing `bridge/relay/` timed out. Partial moves done: config moved to `runtime/config/`, runtime files moved to `runtime/bridge/`. **Action Required:** Inspect `bridge/relay/`, move `bridge/docs` -> `docs/bridge`, `bridge/tests` -> `tests/bridge`, `bridge/schemas` -> `src/dreamos/schemas/bridge`, data dirs -> `runtime/bridge`, reports -> `runtime/reports/bridge`. Update code refs. Delete top-level `bridge/`.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-024:** **Consolidate `requirements.txt` with `pyproject.toml`.** (Status: DONE - Compared files, added missing dependencies (`markdownify`, `streamlit`, `praw`) to `[tool.poetry.dependencies]` in `pyproject.toml`. Deleted `requirements.txt`.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **ORG-025:** **Review/Move/Delete miscellaneous top-level directories.** (Status: Partially Done / Blocked - `_archive/` and `audit/` targeted for deletion but not found (possibly already removed/empty). Review of `app/`, `bridge/`, `analytics/`, `sandbox/`, `dev_sandbox/` blocked due to list_dir timeouts. **Action Required:** Manually inspect remaining dirs and consolidate/delete as appropriate.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **REFACTOR-SYNC-AGENT-IDS:** Refactor `src/dreamos/core/swarm_sync.py` to load expected agent IDs from config/registry instead of hardcoding. (Status: DONE) - Modified `swarm_sync.py` to use `AgentIdentityStore.get_agent_ids()` instead of hardcoded list. - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **REFACTOR-SYNC-PATHS:** Remove `sys.path` manipulation from `src/dreamos/core/swarm_sync.py`. (Status: DONE) - Removed direct `sys.path.append` calls. Script now relies on standard Python module resolution. - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **REFACTOR-SYNC-CONFIG:** Move constants from `src/dreamos/core/swarm_sync.py` (file paths, retry counts) into `AppConfig`. (Status: DONE - Current implementation in `src/dreamos/core/swarm_sync.py` already loads these values from `AppConfig` via `_get_sync_config` under `coordination.swarm_sync` key, with local defaults if keys are missing.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **REFACTOR-SYNC-PROTOCOL-ALIGN:** Align `src/dreamos/core/swarm_sync.py` file path and data schema with the `SwarmLinkedExecution` protocol definition. (Status: DONE - The default path `runtime/swarm_sync_state.json` (configurable via `AppConfig`) used by `swarm_sync.py` matches the reference in `ai_docs/onboarding/README.md`. The data schema used is appropriate for status reporting as per the protocol's intent. No specific conflicting schema definition found.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **REFACTOR-CONFIG-MODULARITY:** Investigate moving specific config models (e.g., `GuiAutomationConfig`, `DreamscapeConfig`) from `src/dreamos/core/config.py` closer to their respective modules. (Status: Partially Done / Blocked - `DreamscapeConfig` models moved to `src/dreamscape/config.py`. `GuiAutomationConfig` models moved to `src/dreamos/automation/config.py`. `pyproject.toml` updated to include `dreamscape` as a package. **Blocked:** Removal of original model definitions from `src/dreamos/core/config.py` failed after multiple attempts. Manual edit required for `src/dreamos/core/config.py` to complete this refactor.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **REFACTOR-CONFIG-PATHS:** Review and potentially regroup/simplify path definitions in `core/config.py::PathsConfig`. (Status: DONE - Reviewed `PathsConfig`. Core paths are based on `PROJECT_ROOT`. Optional paths default to `None`. `AppConfig` validators handle path resolution to absolute paths. No major regrouping or simplification deemed necessary at this time.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **REFACTOR-CONFIG-ACCESS:** Clarify/refactor `load_config` vs. `get_config` usage in `core/config.py`. (Status: DONE - `load_config()` is the app-level initializer for the global `AppConfig` singleton, wrapping Pydantic's `AppConfig.load()`. It uses `DREAMOS_CONFIG_PATH` env var to direct `YamlConfigSettingsSource`. `get_config()` is the accessor, with lazy default load. This division of responsibility is clear. No major refactoring deemed necessary; existing mechanism allows specific YAML loading.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **REFACTOR-VALIDATION-UTILS-AUDIT:** Audit usage of `core/validation_utils.py` functions and determine if they are redundant due to Pydantic validation. (Status: DONE - `src/dreamos/core/validation_utils.py` confirmed unused and deleted. `ai_docs/business_logic/README.md` updated to remove documentation for these utilities using the Archive & Recreate Protocol. Onboarding guide updated with this new protocol.) - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **REFACTOR-COORD-DUPLICATES:** Resolve duplicate files (`agent_bus.py`, `event_payloads.py`) between `core/coordination` and `coordination` directories. (Status: In Progress) - Analysis indicates `core/coordination` holds primary implementation; top-level versions likely removable after updating imports. **Note:** `agent_bus.py` and `event_payloads.py` from `src/dreamos/coordination/` deleted as per this task. The `project_board_manager.py` in `src/dreamos/coordination/` requires separate review. - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **REFACTOR-PBM-SIZE:** Review and potentially refactor large `project_board_manager.py` file. (Status: TODO)
*   **REFACTOR-BASE-AGENT-SIZE:** Review and potentially refactor large `core/coordination/base_agent.py` file. (Status: TODO) - Consider extracting task processing, command dispatch, event publishing logic. Note: Lifecycle logic is already separated in `BaseAgentLifecycleMixin`.
*   **FIX-LIFECYCLE-DECORATOR:** Correct placeholder decorator imports in `core/coordination/base_agent_lifecycle.py`. (Status: DONE) - Uncommented correct import from `dreamos.agents.utils.agent_utils` and removed local placeholder. - @Agent_Gemini - {{AUTO_TIMESTAMP_ISO}}
*   **REFACTOR-DB-PYDANTIC:** Integrate Pydantic models more deeply into `SQLiteAdapter` methods. (Status: TODO)
*   **REFACTOR-DB-TRANSACTIONS:** Review and implement explicit transaction management in `SQLiteAdapter` where needed for atomicity. (Status: TODO)
*   **REFACTOR-DB-ERRORS:** Refine error handling in `SQLiteAdapter` and potentially map to custom exceptions. (Status: TODO)
*   **REFACTOR-ERROR-HIERARCHY:** Review integration error definitions (`IntegrationError`, `APIError`) and consider unifying them under the core `DreamOSError` hierarchy. (Status: TODO)
*   **REFACTOR-EVENT-NAMING:** Ensure consistent usage of `BaseDreamEvent` vs. `BaseEvent` across the codebase. (Status: TODO)
*   **REFACTOR-MOVE-FEEDBACK-SCRIPT:** Move `thea_feedback_ingestor.py` to the `scripts/` directory. (Status: TODO)
*   **REFACTOR-FEEDBACK-CONFIG:** Load feedback path in `thea_feedback_ingestor.py` from `AppConfig`. (Status: TODO)
*   **VERIFY-THEA-IMPORT:** Check and correct the import path for `TheaAutoPlanner` in `thea_feedback_ingestor.py`. (Status: TODO)
*   **CLARIFY-SWARM-LOGGER-ROLE:** Clarify the intended role of `swarm_logger.py` vs. standard Python logging and rename/refactor if necessary. (Status: TODO)
*   **REFACTOR-SWARM-LOGGER-CONFIG:** Refactor `swarm_logger.py` to receive log path via configuration injection. (Status: TODO)
*   **REVIEW-SWARM-LOGGER-LOCK:** Review if the synchronous `FileLock` in `swarm_logger.py` is appropriate for the application's concurrency model. (Status: TODO)
*   **PIPE-003:** **Identify scraper context metadata integration points.** (Status: Phase 1 Done - Report at `ai_docs/agent_coordination/PIPE-003_MetadataScout_Phase1_Report.md`. Phase 2 Implemented (Direct Prompt Augmentation) - Report at `ai_docs/agent_coordination/PIPE-003_MetadataScout_Phase2_Report_PromptAugmentation.md`. Phase 3 Planning for PromptManager Context initiated - Plan at `ai_docs/agent_coordination/PIPE-003_MetadataScout_Phase3_Plan_PromptManagerContext.md`. Phase 4 Planning for FeedbackEngine Context initiated - Plan at `ai_docs/agent_coordination/PIPE-003_MetadataScout_Phase4_Plan_FeedbackEngineContext.md`) - @Agent-4 (MetadataScout) - {{AUTO_TIMESTAMP_ISO}}
*   **IMPROVE-DB-SNAPSHOT-CONSISTENCY:** Investigate using SQLite backup API or ensuring DB writes are paused during snapshot creation. (Status: TODO)
*   **REFACTOR-SNAPSHOT-CONFIG:** Ensure snapshot config (paths, timeouts) is managed via `AppConfig`. (Status: TODO)
*   **DEPRECATE-FILE-TASKNEXUS:** Replace usage of file-based `TaskNexus` with `DbTaskNexus` and remove the former. (Status: TODO)
*   **DEFINE-SHADOW-NEXUS-FALLBACK:** Define the mechanism for detecting primary Task Nexus failure and activating/using `ShadowTaskNexus`. (Status: TODO)
*   **ALIGN-SHADOW-NEXUS-TASK-MODEL:** Align the task structure used by `ShadowTaskNexus` with the primary task model (`TaskMessage`). (Status: TODO)
*   **REFACTOR-SHADOW-NEXUS-CONFIG:** Load the backlog path for `ShadowTaskNexus` from `AppConfig`. (Status: TODO)
*   **REFACTOR-TASK-ORCH-NAMING:** Consider renaming `TaskOperationsHandler` for clarity (e.g., `TaskClaimingService`). (Status: TODO)
*   **REFACTOR-ASYNC-INTEGRATION:** Investigate making `SQLiteAdapter` and `ProjectBoardManager` natively async. (Status: TODO)
*   **REVIEW-CAPREG-CACHE-CONSISTENCY:** Evaluate if the `CapabilityRegistry` cache-only read strategy is sufficient or if cache invalidation/refresh is needed. (Status: TODO)
*   **(Add more tasks here as they are defined)**

*   **TASK-SYS-001: Generate Comprehensive Codebase Status Report.** (Status: In Progress) - @Agent-5 (Captain) - {{AUTO_TIMESTAMP_ISO}} - General Victor directive. Initial focus: Bridge integration, Core loop & config, Specs & docs. Report at `ai_docs/reports/codebase_status_main.md`.
*   **ORG-CONTRIB-DOC-001: Contribute to Governance Docs (Onboarding, Protocols).** (Status: Ongoing) - @All Agents (excluding Captain during TASK-SYS-001 or as per specific directives) - {{AUTO_TIMESTAMP_ISO}} - Reflect on operational experiences, identify improvements, propose/apply updates to `runtime/governance/` documents. Focus on clarity, autonomy, and the "Dream.OS way". This is a standing task when not actively engaged in higher-priority, General-assigned project work.
*   **TASK-BRIDGE-001 (and related sub-tasks like PF-BRIDGE-INT-001): PyAutoGUI to ChatGPTScraper bridge integration.** (Status: Paused - General Victor Direct Implementation) - @Swarm (Previously Agent-1, et al.) - {{AUTO_TIMESTAMP_ISO}} - General Victor has taken over direct implementation. Swarm tasks related to this are paused pending further notice or requests for support from the General.

**Coordination Notes:**

*   Agents should claim tasks by assigning themselves (`@AgentName`).
*   Update status (TODO, In Progress, Blocked, Done).
*   Log significant blockers or decisions under the relevant task.
*   Keep the Target Structure updated as organization progresses.