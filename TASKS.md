# Project Task List

This list outlines ongoing tasks for organizing, refining, and developing the
Dream.OS project.

## Infrastructure & Tooling

- [x] **Task Board Permissions:** Investigate and resolve the      `PermissionError: [Errno 13] Permission denied` when      `task_board_updater.py` accesses `runtime/task_board.json`. This currently      blocks status updates. (High Priority) (Resolved by implementing a new task_board_updater.py with filelock)
- [ ] **Project Scanner - `categorize_agents`:** Fully implement the agent
      categorization logic in `ProjectScanner.categorize_agents` beyond the
      current placeholder.
- [ ] **Project Scanner - Path Normalization:** Reduce "Detected move" log noise
      by ensuring consistent path separator usage (`/` vs `\\`) during cache
      comparison.
- [ ] **Project Scanner - Tree-sitter:** Investigate installing tree-sitter and
      relevant language grammars (`rust`, `javascript`) to enable full AST
      parsing capabilities.
- [ ] **Dependency Review:** Audit `requirements.txt` and `pyproject.toml` to
      ensure all necessary dependencies are listed and unused ones are removed.
- [ ] **YAML Updater Utility:** Evaluate the need for and potentially implement
      a robust YAML list append utility
      (`src/tools/dreamos_utils/yaml_updater.py`?) as suggested in THEA's
      directive for contract signing, replacing manual edits or basic file
      writes.

## Codebase & Refactoring

- [ ] **`src/dreamos/dream_mode/` Integration:** Deeply analyze the code moved
      into `src/dreamos/dream_mode/` and refactor/integrate it properly into the
      core `src/dreamos/` structure (e.g., `core/`, `automation/`, `runtime/`).
      (Partially done - files moved, imports fixed, deeper analysis needed)
- [x] **Review `_archive/`:** Examine the contents of the `_archive/` directory
      and definitively decide whether to delete it or keep it for historical
      reference. (Completed - Directory deleted)
- [ ] **Review `apps/` Structure:** Standardize the structure within the `apps/`
      directory (e.g., ensure each app has `README`, `requirements`, etc.).
- [ ] **Configuration Management:** Centralize configuration loading. Check for
      hardcoded paths or settings (e.g., in `project_scanner.py` defaults before
      args were added) and replace them with a unified config system (e.g.,
      using `config/` directory).
- [ ] **Import Validation:** Perform a more thorough check for potentially
      broken imports across the codebase after the significant restructuring,
      possibly using static analysis tools.

## Testing & Validation

- [ ] **Test Coverage:** Increase test coverage, particularly for core
      components and recently moved/refactored code (`dream_mode`, scanner
      components). Integrate `htmlcov/` into the CI/reporting process.
- [ ] **Health Checks:** Review and potentially expand health checks in
      `src/dreamos/core/health_checks/` to cover more subsystems. Fix any
      remaining issues (like the potential instability noted in
      `cursor_status_check.py`).

## Documentation

- [ ] **Update `README.md`:** Refresh the main `README.md` to accurately reflect
      the current project structure, setup instructions, and usage (especially
      `cli.py`).
- [ ] **Document `scripts/`:** Add READMEs or usage comments to the scripts
      within the `scripts/` subdirectories (`maintenance`, `testing`, `utils`).
- [ ] **Review `DEVELOPER_NOTES.md`:** Integrate relevant information from the
      moved `DEVELOPER_NOTES.md` (now in `docs/`) into the main documentation or
      specific module docs.

## Phase 2 Pipeline (Agent Specific)

- [ ] **Agent 2 (`prototype_context_router`):** Proceed with design and
      prototyping once task board is unblocked. (Blocked)
- [ ] **Agent 3 (`ROUTE_INJECTION_REQUEST`):** Define schema and provide
      example.
- [ ] **Agent 4 (`scraper_attach_context_metadata`):** Identify sources and
      integration hooks.
- [ ] **Agent 5 (`scraper_state_machine_conversion`):** Define states and
      refactor.
- [ ] **Agent 6 (`design_pipeline_test_harness`):** Outline test cases and
      harness structure.
- [ ] **Agent 7 (`monitor_bus_correlation_consistency`):** Design validator and
      plan implementation.
- [ ] **Agent 8 (`compile_consolidation_report`):** Define ingestion plan.

_(Note: Phase 2 statuses need updating via `task_board_updater.py` once
permissions are fixed)_
