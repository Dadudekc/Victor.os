# Developer Notes: Memory & Feedback Module Consolidation

Date: 2024-06-XX

## Summary
This commit consolidates key modules into the new `dreamos` package structure:

### 1. Placeholder Removal
- Deleted `main_copy.py` at repo root.

### 2. Memory Modules
- Moved and renamed:
  - `dream_mode/local_blob_channel.py` → `src/dreamos/memory/blob_channel_memory.py`
  - `dream_mode/azure_blob_channel.py` → `src/dreamos/memory/azure_blob_channel_memory.py`
- Core memory files remain under `src/dreamos/memory/`:
  - `memory_manager.py`
  - `governance_memory_engine.py`

### 3. Feedback Modules
- Created `src/dreamos/feedback/` and moved:
  - `src/dreamos/chat_engine/feedback_engine.py`
  - `src/dreamos/chat_engine/feedback_engine_v2.py`

### 4. Import Normalization
- Updated all `dream_mode.local_blob_channel` imports to `dreamos.memory.blob_channel_memory`.
- Updated `dream_mode.azure_blob_channel` → `dreamos.memory.azure_blob_channel_memory`.
- Updated `dreamos.chat_engine.feedback_engine*` imports to `dreamos.feedback.*`.

### 5. Validation
- Ran full `pytest` suite to ensure no regressions.
- Added JSON schema–driven task validation using `jsonschema` (schema at `src/dreamos/utils/task_schema.json`) and refactored `validate_task_entry` in `social/scripts/inject_task.py`.
- Created unit tests in `tests/utils/test_task_schema_validation.py` covering required fields, type enforcement, and date-time format validation.

### 5.1 Broadcast Validation Enhancements
- Introduced `dry_run` mode in `broadcast_directive` CLI to simulate broadcasts without writing files.
- Enforced mailbox schema validation: mailbox JSON must contain a list at `messages`, else the broadcast is rejected and an error logged.
- Refactored `broadcast_to_mailboxes` to perform atomic writes via temporary files and `os.replace`, improving safety under concurrent operations.
- Added comprehensive tests in `tests/core/coordination/test_broadcast_directive.py` covering dry-run behavior, corrupt mailbox schemas, invalid JSON handling, and concurrency scenarios.

### 6. Memory Layer Migration
- Migrated to UnifiedMemoryManager:
  - Replaced imports of `MemoryManager` with `UnifiedMemoryManager` in UI (`ui/main_window.py`, `ui/fragment_forge_tab.py`) and monitoring modules.
  - Refactored storage calls from `save_fragment/load_fragment` to `set/get` in `prompt_execution_monitor.py`.
  - Removed dead references to legacy `MemoryManager`.
- Added `tests/memory/test_unified_memory_manager.py` covering:
  • `set()`/`get()` on `system` segment
  • `record_interaction()` + `fetch_conversation()`
  • `export_conversation_finetune()`

### 7. Memory Test Expansion
- Unlocked `tests/memory` slice in pytest configs (`conftest.py`) to enable full coverage of memory tests.
- Added comprehensive tests in `tests/memory/test_unified_memory_manager.py`:
  • `test_compression_roundtrip` – verifies zlib compress/decompress integrity.
  • `test_lru_cache_eviction` – ensures cache respects `cache_size` limit and evicts oldest entries.
  • `test_clear_segment_resets_data` – checks `clear_segment` empties both cache and segment file.
  • `test_export_jsonl_compliance` – validates JSONL output format for fine-tuning exports.
- Goal: Achieve 95%+ coverage on `src/dreamos/memory/memory_manager.py`.

**Next steps**: run full `pytest` suite to validate.

## Missing Test Coverage

The following areas currently lack unit tests and should be covered in future iterations:

1. **MemoryManager**
   - Persistence edge cases: invalid JSON format, load errors, `save_memory` failures.
   - `list_fragment_ids` returns expected IDs after multiple operations.

2. **DatabaseManager**
   - SQLite operations: `record_interaction`, `initialize_conversation`, `fetch_conversation`, and `close` behaviors.
   - Thread safety via the lock.

3. **UnifiedMemoryManager**
   - `clear_segment`: ensure cache and segment file cleared.
   - `get_stats`: correct stats after multiple sets.
   - `optimize`: verify recompression and file writes.
   - Interaction helpers: `record_interaction`, `initialize_conversation`, `fetch_conversation`, and `export_conversation_finetune` output format.
   - `render_narrative`: template loading and rendering, including fallback on missing template.

4. **ResilientChatScraper**
   - Edge cases: HTTP error codes, invalid HTML structures, large payload performance.

5. **CursorInteractionVerifier**
   - Success path: verify `click_and_verify` returns `True` when match score meets threshold.

6. **CycleHealthMonitor**
   - Auto-persist after threshold without escalation.

## Escalated Agents Tab
- Added new tab **"Escalated Agents"** to the Dream.OS dashboard sidebar.
- Filters agents with `escalation` count > 0.
- Displays each entry as `agent_id: count` and, if tracked, `(last: YYYY-MM-DD HH:MM:SS)`.
- View refreshes live on `ESCALATION` events alongside the existing Agents view.
- Default dashboard behavior remains unchanged when no agents have active escalations.
- Added pytest-qt UI tests in `tests/ui/test_escalated_agents_view.py` to verify:
  - The tab is hidden when no escalations are active.
  - The tab becomes visible and populated upon receiving an `ESCALATION` event.

### 8. Coordination Package Flatten

Date: 2025-04-14

**Prior layout:**
```
src/dreamos/coordination/_agent_coordination/
  ├─ dispatchers/
  ├─ utils/
  ├─ tools/
  ├─ shared_mailboxes/
  └─ ...
```

**Flattened layout:**
```
src/dreamos/coordination/
  ├─ dispatchers/
  ├─ utils/
  ├─ tools/
  ├─ shared_mailboxes/
  └─ ...
```

Removed the nested `_agent_coordination/` directory by moving all its contents up one level, and deleted the empty folder. Imports were updated from `dreamos.coordination._agent_coordination.*` to `dreamos.coordination.*`.

---
End of consolidation notes.

## Escalation System
- Added `escalation` counter and `last_escalation` timestamp to `agent_counters`.
- Subscribed to `ESCALATION` events on `AgentBus`: status bar pulses ⚠️, agent cards flash yellow, and metrics persisted to `runtime/logs/dashboard_state.json`.
- Introduced "Escalated Agents" tab with live list of agents having active escalations and their last event timestamps.
- Smoke-tested via `smoke_escalation.py`, confirming UI updates and JSON structure.

## Escalation System
- Extended `DashboardEventListener` to support an optional `on_escalation` callback for ESCALATION events.
- Dashboard now tracks `escalation_count` and flashes a yellow warning overlay on ESCALATION events.
- ESCALATION events trigger a UI refresh to update task and agent views.

## Phase 3 Core-to-Src Migration
- Migrated BaseDispatcher implementation:
  - `src/dreamos/coordination/dispatchers/base_dispatcher.py` now contains the full, real dispatcher logic migrated from `core/coordination/dispatchers/base_dispatcher.py`.
- Migrated AgentBus implementation:
  - `src/dreamos/coordination/agent_bus.py` now houses the real `AgentBus` class migrated from `core/coordination/agent_bus.py`.
  - Kept `src/dreamos/agent_bus.py` stub for re-export consistency (`AgentBus = dreamos.coordination.agent_bus.AgentBus`).
- Migrated Task Utilities:
  - `src/dreamos/utils/task_utils.py` includes real `read_tasks`, `write_tasks`, and `update_task_status` implementations from `core/utils/task_utils.py`.
- Cleaned up imports:
  - Replaced all `from core.*` and `import core.*` with `from dreamos.*` and `import dreamos.*` across the repo.
- Preserved UI location:
  - `ui/main_window.py` remains at root `ui/` per architectural decision; not relocated into `src/dreamos/`.
- Removed legacy `core/` directory entirely after migration.

Phase 3 migration complete and validated via full pytest run.

---
## Phase 2: Modularization Plan

### 2.1 Service/Module Boundaries
- **Dashboard Service**: UI components, event listener, visualization layers.
- **Automation Service**: Task injection, toolbar commands, auto-click logic.
- **Coordination/Agent Management Service**: AgentBus wiring, system events, agent status flows.
- **State Management/Memory Service**: MemoryManager, UnifiedMemoryManager, persistence APIs.

### 2.2 Target Directory Structure
```text
src/dreamos/
  dashboard/             # Dashboard Service
    __init__.py
    event_listener.py
    dashboard_ui.py      # Main Dashboard logic moved here
  automation/            # Automation Service
    __init__.py
    automation_controller.py
    task_injector.py
  coordination/          # Agent Coordination Service
    __init__.py
    agent_bus.py
    dispatcher.py
    handler_registry.py
  memory/                # State Management/Memory Service
    __init__.py
    memory_manager.py
    unified_memory.py
  services/              # shared service abstractions (if needed)
    __init__.py
    service_base.py
```

### 2.3 Refactor Batches (Small, Green Commits)
1. **Batch 1**: Scaffold new folders and `__init__.py`; move raw files without logic changes; update imports.
   - ✅ Completed: moved `dashboard.py` → `src/dreamos/dashboard/dashboard_ui.py`, updated imports across codebase, removed root `dashboard.py`, and verified pytest remains green.
2. **Batch 2**: Extract Dashboard UI into `dashboard/dashboard_ui.py`, leave event listener in place.
   - ✅ Completed: verified `src/dreamos/automation/` contains all automation modules (main, supervisor, injector, scraper, verifier) and imports are normalized; no residual automation code outside this package; pytest remains green.
3. **Batch 3**: Move automation commands into `automation/` and decouple from dashboard module.
4. **Batch 4**: Isolate AgentBus and dispatcher logic into `coordination/`, update references.
5. **Batch 5**: Consolidate memory modules under `memory/`, ensure `MemoryManager` and `UnifiedMemoryManager` exports.
6. **Batch 6**: Clean up `services/` abstractions, migrate common utilities (e.g. logging, config loaders).
7. **Batch 7**: Update test suite paths and imports to match new structure; confirm `pytest` suite remains green.

### 2.4 Next Steps
- Review and approve the directory layout.
- Kick off Batch 1: scaffold modules and update top‐level imports.
- Track progress via commit prefixes: `refactor(service): …` and ensure CI pipeline passes.

## Automation Module

### Entry Point
- `src/dreamos/automation/main.py` provides a CLI for launching the automation loop:
  ```bash
  automation/main.py \
    --page-url <URL> \
    --primary-selector <CSS/XPath> [--primary-selector ...] \
    --fallback-selector <CSS/XPath> [--fallback-selector ...] \
    --click-image <path/to/template.png> \
    [--window-image <path/to/window_icon.png>] \
    [--delay <seconds>]
  ```
  This instantiates `AutomationSupervisor` and calls `run_loop()`.

### AgentBus Events
- **automation_heartbeat**: emitted each cycle with payload `{timestamp, cycle, status[, error]}` on `EventType.SYSTEM`, `source_id="AutomationSupervisor"`.
- **automation_scrape_failure**: emitted when scraping fails after retries.
- **automation_inject_failure**: emitted when injection fails after retries.

On successful event dispatch, file-based logs in `runtime/loop_health_logs/{heartbeat.log,failures.json}` are skipped. These logs remain as a fallback if the AgentBus is unavailable.

## System Event Types

The following event types are emitted on the AgentBus (SYSTEM channel) to signal key workflow events. Handlers can subscribe using `AgentBus.register_handler(EventType.SYSTEM, handler)` and inspect `event.data['type']` to react.

### PROMPT_SUCCESS
- Emitted when a prompt execution succeeds.
- Payload:
  - `type`: "PROMPT_SUCCESS"
  - `agent_id`: ID of the agent that succeeded.
  - `...` (other context fields)

### PROMPT_FAILURE
- Emitted when a prompt execution fails.
- Payload:
  - `type`: "PROMPT_FAILURE"
  - `agent_id`: ID of the agent that failed.
  - `error`: Error details or message.

### CHATGPT_SCRAPE_SUCCESS
- Emitted by `ResilientChatScraper` after successfully extracting ChatGPT response.
- Payload:
  - `type`: "CHATGPT_SCRAPE_SUCCESS"
  - `agent_id`: ID of the agent (or instance) performing the scrape.
  - `scrape_id` (string): Timestamp or unique ID for this scrape attempt.
  - `retry_count` (int, optional): Number of retry attempts before success.
  - `event_version` (string, optional, default "v1"): Version identifier for the event payload.

### CHATGPT_SCRAPE_FAILED
- Emitted by `ResilientChatScraper` after exhausting retries without success.
- Payload:
  - `type`: "CHATGPT_SCRAPE_FAILED"
  - `agent_id`: ID of the agent (or instance) performing the scrape.
  - `scrape_id` (string): Timestamp or unique ID for this scrape attempt.
  - `retry_count` (int, optional): Number of retry attempts made.
  - `event_version` (string, optional, default "v1"): Version identifier for the event payload.
  - `snapshot_path`: Path where the final DOM snapshot is saved.

Handlers can use these events to update UI metrics, trigger dashboards, or escalate workflows.

• CycleHealthMonitor now subscribes to these SYSTEM events when constructed with an AgentBus,
  automatically invoking record_success/record_failure on 'CHATGPT_SCRAPE_SUCCESS' or
  'CHATGPT_SCRAPE_FAILED' events to keep cycle health metrics in sync.

**Integration Complete**: CycleHealthMonitor's event-bus subscription for scrape health auto-tracking is finished and production-ready.

---
*End of developer notes.*

## Expanded Test Coverage

Following the core module tests, we've now broadened coverage to include:

- **Full Test Suite Enabled**:
  - Removed restrictive `testpaths` and collection filters in `pytest.ini` and `conftest.py` to collect all tests under `tests/`, including integration tests.
  - Added `src/dreamos/version.py` to satisfy integration test imports.

- **AgentBus & AgentStatus** (`tests/core/coordination/test_agent_bus.py`):
  - Verified handler registration and presence in the internal dispatcher.
  - Confirmed `AgentStatus` enum values and iteration.

- **EventDispatcher** (`tests/core/coordination/test_dispatcher.py`):
  - Tested that `dispatch_event` enqueues events correctly.
  - Processed a single queued event, ensuring registered handlers are invoked.

- **Task Utilities** (`tests/utils/test_task_utils.py`):
  - Read/write tasks JSON and default `failure_count` initialization.
  - Updated task statuses, including failure count increments for `RESCUE_PENDING`.
  - Verified behavior with missing task IDs and invalid JSON.

These additions bring us closer to the 95%+ coverage goal across core coordination, utility, and integration layers.

### Task Update Hardening
- Added tests for `update_task_status` edge-cases:
  - Read failure (read_tasks returns None) → logs error and returns False.
  - Task not found in list → logs warning and returns False.
  - No-op update (status unchanged) → returns True without file rewrite.
  - Successful update → rewrites file with `timestamp_updated`, `last_updated_by`, and optional result/error fields.
  - Invalid structure (non-list JSON) → safe failure with warning, returns False.

## Automation Supervisor Agent

- On initialization, `AutomationSupervisor` registers itself with `AgentBus` as agent_id `automation_supervisor` and capability `automation`.
- This registration emits a `SYSTEM` event of type `agent_registered` with payload `{"type": "agent_registered", "agent_id": "automation_supervisor"}`.
- Subsequent heartbeat and failure cycles are emitted as standard swarm events (`prompt_success` / `prompt_failure`) under this agent_id.
- Dashboards can now list and monitor this agent like any other Dream.OS agent.

### Dashboard UI Metadata Display

- The Agents tab now includes **Priority** and **Description** columns, reflecting `agent_metadata` events.
- The metadata columns are auto-populated when the `agent_metadata` SYSTEM event is received for an agent.
- Blank cells appear if metadata isn't available.
- This behavior is defined in `dashboard_ui.py` under `_on_metadata` and extended table model columns.

### Dashboard Health Chart Polish

- Tooltips are color-coded (green for Success, red for Failure).
- Tooltips are suppressed for bars with zero values to reduce noise.
- Health bars are sorted by total activity (Success + Failure) in descending order.
- Legend remains visible and hover interactions persist after refresh.
- Phase 2 Health Chart polish milestone: complete.
- Phase 3 Health Chart Stacked View: added a "Stacked View" toggle checkbox to switch between grouped and stacked bar views, implemented in `dashboard_ui.py`, with unit test coverage in `tests/ui/test_dashboard_stacked_toggle.py`.
- Phase 4 Health Chart Threshold Overlays: added dashed green/red lines at SUCCESS_THRESHOLD (50) and FAILURE_THRESHOLD (10), implemented via `QLineSeries` with `QPen` dash styles.
- Phase 4.1 Health Chart Breach Warnings: added yellow UI pulse on threshold breach (success < 50 or failure > 10) using `self._flash_color(QColor(255,255,0))`.

*End of developer notes.*

## Phase 4: TaskUtils Hardening

Date: 2024-07-XX

- Hardened `update_task_status` in `task_utils.py` with:
  - Atomic writes using a temporary file and `os.replace` for crash-safety
  - Automatic backup of the original JSON to a `.bak` file before overwrite
  - Enforcement of `ALLOWED_STATUSES`, returning `False` on invalid status inputs
  - Enhanced logging listing available task IDs when the specified `task_id` is not found
  - Optional `fail_on_corrupt` flag to escalate `JSONDecodeError` on corrupted task lists
  - Optional `enable_file_locking` flag to perform file-level locking via the `filelock` library
- Added comprehensive pytest tests (`coordination/tests/test_task_utils.py`) covering:
  - `test_backup_and_atomic_write`
  - `test_invalid_status_no_update`
  - `test_task_not_found_logs_available_ids`
  - `test_fail_on_corrupt`
  - `test_file_locking`

*End of developer notes.*

## CLI Help Stabilization
- Added CLI smoke tests for `--help` and `-h` via `tests/integration/test_cli_help_output.py`.
- Snapshot validated core commands: `run`, `stats`, `validate-config`, `version`.
- Ensures baseline Typer behavior and helps detect future CLI regressions.

*End of developer notes.*

### Phase 4.1: Threshold Breach Warnings
- After drawing thresholds, `Dashboard.refresh()` scans each agent's stats:
  • If **success < SUCCESS_THRESHOLD** or **failure > FAILURE_THRESHOLD**, fires a yellow UI pulse via `self._flash_color(QColor(255,255,0))`.
- Utilizes existing `QTimer.singleShot` for an immediate, non-blocking flash.
- Keeps warnings lightweight—no tab changes or system events.
- Phase 4.1 milestone: threshold breach warnings fully implemented and verified.

*End of developer notes.*

### Phase 4.2: Persistent Breach Badges
- Introduced `self.agent_breach_flags: Dict[str,bool]` to track per-agent breach state on each `refresh()`.
- Badge column (⚠️) added to Agents tab; hidden when no active breaches.
- Breach flags persist until agent recovers (success ≥ threshold AND failure ≤ threshold).
- Uses `QStandardItemModel.setColumnHidden` to show/hide badge column dynamically.

*End of developer notes.*

## Release v0.2.1
- Fully integrated `CycleHealthMonitor` with AgentBus event-driven scrape health tracking.
- Added health chart threshold overlays (dashed SUCCESS/FAILURE lines) and breach warnings (yellow UI pulses).
- Enhanced `update_task_status` with hardening tests and edge-case coverage.

*End of developer notes.*

### Phase 4.3: Legacy Test Migration
- Deleted legacy `tests/utils/test_task_utils.py` after migrating and consolidating tests under `coordination/tests`.
- Added read_tasks edge-case tests (`test_read_tasks_missing_and_empty`, `test_read_tasks_invalid_json`) to `coordination/tests/test_task_utils.py`.
*End of developer notes.* 