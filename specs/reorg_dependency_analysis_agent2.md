# Agent-2: Reorganization Dependency Analysis - Phase 1

This document outlines the findings of the code dependency analysis performed by Agent-2 as part of `TASK: AGENT2-REORG-DEP-ANALYSIS-001`, supporting the project reorganization outlined in `specs/reorganization_proposal_phase1.md`.

## Scope
Analysis focused on Python (`*.py`) and JavaScript (`*.js`, though none were prominently found in key areas) dependencies in the following directories: `app/`, `apps/`, `bridge/` (top-level), `runtime/`, `scripts/`, `assets/`, and `src/`.

## Methodology
- Listed directory contents to understand scope.
- Used `grep_search` to identify import patterns:
    - Imports from `src/` subdirectories (`dreamos`, `dreamscape`, `tools`).
    - Relative imports (`from .`, `from ..`).
    - General `import` and `from` statements to understand overall library usage.

## Key Findings

### 1. `app/` directory
- Contains `app/automation/`.
- **`app/automation/`**:
    - Contains Python scripts: `automation_interface.py`, `gui_controller.py`, `gui_automation.py`.
    - **Dependencies**:
        - External: `pyautogui`, `time`, `os`, `logging`, `typing`.
        - Internal (relative): `automation_interface.py` imports from `./gui_controller.py`.
    - **No direct imports from `src/` (dreamos, dreamscape, tools) or other top-level project directories were found.**
    - **Relevance**: Appears self-contained or reliant on external libraries. Suitable for moving to `src/apps/automation/` as proposed. Internal relative imports must be maintained.

### 2. `apps/` directory
- Contains `sky_viewer/`, `examples/`, `browser/`.
- **`apps/sky_viewer/`**:
    - Contains `sky_viewer.py`.
    - **Dependencies**: External (`os`, `sys`, `PyQt5`).
    - **No direct imports from `src/` or relative project imports.**
    - **Relevance**: Standalone application. Suitable for `src/apps/sky_viewer/`.
- **`apps/examples/`**:
    - Contains Python scripts including `reflection_agent.py` and `stubs/agent_1_stub.py`.
    - **Dependencies**:
        - External: `json`, `pathlib`, `typing`, `yaml`, `watchdog`, `time`, `logging`, `datetime`, `os`, `traceback`.
        - **Imports from `src/dreamos/`**:
            - `reflection_agent.py` imports `from dreamos.core.config import AppConfig`.
            - `stubs/agent_1_stub.py` imports `from dreamos.coordination.agent_bus import AgentBus`, `from dreamos.coordination.dispatcher import Event, EventType`.
    - **Relevance**: Has direct dependencies on `src/dreamos/`. If moved to `src/apps/examples/`, these imports should remain valid if `src/` is in `PYTHONPATH`.
- **`apps/browser/`**:
    - Contains `main.py`.
    - **Dependencies**: External (`sys`, `PySide6`).
    - **No direct imports from `src/` or relative project imports.**
    - **Relevance**: Standalone application. Suitable for `src/apps/browser/`.

### 3. Top-Level `bridge/` directory
- Contains subdirectories: `outgoing_feedback/`, `feedback/`, `tests/`, `docs/`, `schemas/`, `incoming_commands/`, `relay/`.
- Python code was found primarily in `bridge/relay/` and `bridge/feedback/`.
- **`bridge/relay/`**:
    - `command_listener.py`: Imports standard libs, `watchdog`, and `from payload_handler import ...` (relative within `bridge/relay/`).
    - `payload_handler.py`: Imports standard libs and `from status_pusher import ...` (relative, presumably from `bridge/feedback/` or elsewhere within top-level `bridge/`).
- **`bridge/feedback/`**:
    - `status_pusher.py`: Imports standard libs (`json`, `os`, `logging`, `uuid`, `datetime`).
- **No direct imports from `src/dreamos` or `src/dreamscape` were found in the Python files analyzed within the top-level `bridge/` directory.**
- **Relevance**: The Python code in the top-level `bridge/` seems self-referential or uses external libraries. This is distinct from `src/dreamos/bridge/` which *does* import from `dreamos.core` etc. The reorganization plan needs to clarify the role and fate of this top-level `bridge/` directory versus `src/dreamos/bridge/`.

### 4. `scripts/` directory
- Contains numerous Python utility scripts.
- **Dependencies**:
    - **Imports from `src/dreamos/`**:
        - `swarm_monitor.py`: `from dreamos.core.swarm_sync import ...`
        - `monitor_bridge.py`: `from dreamos.tools.cursor_bridge import ...`, `from dreamos.core.config import ...`
        - `gpt_cursor_relay.py`: `from dreamos.tools.cursor_bridge import ...`
    - No `from ..` relative imports indicating attempts to import outside `scripts/` into other top-level areas.
- **Relevance**: Scripts depend on `src/dreamos/`. This is typical and acceptable for top-level utility scripts. Their location seems appropriate.

### 5. `runtime/` directory
- Primarily contains data, logs, state files, and configuration.
- **No Python files directly within `runtime/` were found to be importing from `src/dreamos`, `src/dreamscape`, or `src/tools`.**
- **Relevance**: Appears to correctly serve its purpose as a data/state directory, not a source code directory with cross-dependencies to main application logic.

### 6. `assets/` directory
- Contains `gui_images/`.
- **Relevance**: Unlikely to contain Python/JS code with direct import dependencies. May be referenced by file paths in code.

### 7. `src/` directory (Internal Package Dependencies)
- Contains `dreamos/`, `dreamscape/`, `tools/`.
- **`src/dreamos/` depends on `src/dreamscape/`**:
    - `src/dreamos/core/config.py` imports `from dreamscape.config import DreamscapeConfig`.
- **`src/dreamscape/` depends on `src/dreamos/`**:
    - `src/dreamscape/agents/planner_agent.py` imports from `dreamos.config`, `dreamos.coordination.agent_bus`, `dreamos.core.coordination.base_agent`, `dreamos.integrations.openai_client`, `dreamos.utils.config_utils`.
    - `src/dreamscape/agents/writer_agent.py` imports from `dreamos.core.config`, `dreamos.core.coordination.agent_bus`, `dreamos.core.coordination.base_agent`, `dreamos.integrations.openai_client`, `dreamos.utils.config_utils`.
- **Relevance**: **There is a bidirectional dependency between `dreamos` and `dreamscape` packages.** This is a critical architectural characteristic. While manageable, it indicates tight coupling. Any reorganization affecting these packages must carefully consider this.
- Dependencies of/within `src/tools/` were not deeply analyzed in this initial pass but should be considered if `tools` itself is to be restructured.

## Summary of Implications for Reorganization
- **Consolidation of `app/` and `apps/` into `src/apps/`**: Appears largely feasible. `apps/examples/` dependencies on `dreamos` will resolve correctly if `src/` is in `PYTHONPATH`.
- **Top-Level `bridge/` vs. `src/dreamos/bridge/`**: Requires clarification. The top-level `bridge/` doesn't show `src/` dependencies, unlike `src/dreamos/bridge/`. Its purpose and relationship to the core bridge logic needs to be defined for proper reorganization.
- **`dreamos` <-> `dreamscape` Coupling**: The bidirectional dependency is a key architectural point to be mindful of during any refactoring within `src/`.
- **`scripts/`**: Current dependencies on `src/dreamos` are normal for utility scripts.

This concludes the initial dependency analysis for task `AGENT2-REORG-DEP-ANALYSIS-001`. Further detailed analysis may be required for specific sub-modules as the reorganization progresses. 