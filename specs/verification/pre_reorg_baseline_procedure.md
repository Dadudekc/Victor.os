# Pre-Reorganization Baseline Procedure

**Phase:** 3 (Implementation Preparation & Tooling)
**Lead Agent:** Agent 7 (Test & Verification Suite Developer)
**Coordinator:** Agent 1 / Co-Captain
**Reference:** `specs/reorganization_phase3_preparation.md` (Section 3.3)
**Target Document for Results:** `specs/verification/pre_reorg_baseline_results.md` (to be created when baseline is run)

## 1. Objective

To establish and document a clear, repeatable baseline of the project's state (tests, build, key functionalities) *before* any reorganization scripts from Phase 4 are executed. This baseline will be used for comparison during post-reorganization validation.

## 2. Prerequisites

*   A dedicated Git branch for the reorganization effort has been created and is checked out.
*   The branch is up-to-date with the main development line from which it was created.
*   The working directory is clean (`git status` shows no uncommitted changes).
*   All necessary development tools (Python, Poetry, pytest, Node.js if applicable for UI, etc.) are installed and configured according to project standards.

## 3. Baseline Capture Procedures

### 3.1. Full Test Suite Execution

*   **Command:** `poetry run pytest` (or the project's standard command to run all tests).
*   **Expected Outcome:** 100% test pass rate.
*   **Recording:**
    *   Log the full terminal output of the test run (including summary) to `specs/verification/pre_reorg_baseline_results.md`.
    *   Explicitly note the number of tests run and the number passed/failed/skipped.
    *   If any known intermittent failures exist that cannot be fixed before this baseline, they **must** be documented with their issue IDs and current status.

### 3.2. Project Build Verification

*   **Command (Python Package):** `poetry build`
*   **Expected Outcome:** Build completes successfully without errors, generating distributable files (e.g., `.whl`, `.tar.gz` in `dist/`).
*   **Recording:**
    *   Log terminal output of the build command to `specs/verification/pre_reorg_baseline_results.md`.
    *   Note the names and sizes of generated artifacts in `dist/`.
*   **Command (Frontend/UI if applicable):** (e.g., `npm run build` or similar if Node.js frontend exists and is part of the project being reorganized)
*   **Expected Outcome:** UI build completes successfully.
*   **Recording:** Similar to Python package build.

### 3.3. Key Application Functionality (Manual Smoke Test Checklist)

*   **Objective:** Verify core functionalities of critical applications are working as expected.
*   **Checklist (Agent 7 to develop this based on project knowledge; examples below - *to be made more specific for actual project apps*):**
    *   **DreamOS Core Agent System (e.g., running a standard test agent profile):**
        *   [ ] Agent Initialization: Agent process starts, loads configuration, and registers without critical errors logged.
        *   [ ] Task Claiming: Agent successfully claims a predefined simple test task from `runtime/agent_comms/future_tasks.json` (e.g., a task to write a file or log a message).
        *   [ ] Task Execution & State: Agent updates its status in `runtime/agent_comms/working_tasks.json` and produces the expected output/artifact for the simple test task (e.g., creates a file, writes to a specific log).
        *   [ ] Agent Shutdown: Agent can be gracefully shut down (if applicable).
    *   **`src/apps/automation_gui/gui_automation.py` (if runnable as a demo script):**
        *   [ ] Script Execution: `python src/apps/automation_gui/gui_automation.py` (or its main block) runs without Python errors.
        *   [ ] Core Action (Safe Demo): A non-intrusive demo action (e.g., `pyautogui.size()`, `pyautogui.position()`, or a controlled mouse move to a corner) executes and prints expected output.
        *   [ ] Screenshot (if demoed): If the demo includes taking a screenshot, the file is created and is not corrupted.
    *   **`src/apps/sky_viewer/` (Example Application - details TBD by Agent 7 based on actual app):**
        *   [ ] Launch: Application launches successfully (e.g., `python src/apps/sky_viewer/main.py`).
        *   [ ] Load Data: Can load a sample/default data file or view.
        *   [ ] Basic Interaction: A core interaction (e.g., zoom, pan, select item) works as expected.
    *   **`src/apps/browser/` (Example Application - details TBD by Agent 7 based on actual app):**
        *   [ ] Launch: Application launches successfully.
        *   [ ] Navigate: Can navigate to a simple, predefined local HTML page or a safe external URL.
        *   [ ] Basic Rendering: Page renders without gross visual errors.
    *   *(Agent 7 to replace/add specific applications and their critical functionalities based on project priorities and what is most likely to be affected by path changes or refactoring.)*
*   **Recording:** For each item in the checklist, record Pass/Fail in `specs/verification/pre_reorg_baseline_results.md` with brief notes for any failures.

### 3.4. CI Pipeline Status

*   **Action:** Ensure the last run of the CI pipeline (`.github/workflows/ci.yml`) on the HEAD commit of the reorganization branch (before any reorg changes) was successful (all green).
*   **Recording:** Note the commit SHA and a link to the successful CI run in `specs/verification/pre_reorg_baseline_results.md`.

### 3.5. Git Status & Current Commit

*   **Command:** `git status`
*   **Expected Outcome:** Clean working tree.
*   **Command:** `git rev-parse HEAD`
*   **Recording:** Log output of both commands in `specs/verification/pre_reorg_baseline_results.md`.

## 4. Execution of this Procedure

*   This baseline procedure will be executed by Agent 7 *before* Agent 6 runs any of the migration scripts from Phase 4.
*   All results will be meticulously recorded in `specs/verification/pre_reorg_baseline_results.md`. 