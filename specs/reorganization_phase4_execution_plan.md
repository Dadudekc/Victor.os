# Phase 4: Execution, Verification & Finalization

**Lead Agent (Phase 4 Coordination):** Agent 1 (Lead Analyst & Coordinator)
**Supported by:** Co-Captain
**Key Executing Agents:** Agent 6 (Automation), Agent 7 (Baseline), Agent 8 (QA & Rollback)
**Supporting Agents:** Agent 4 (Manual Moves), Agent 5 (Config Updates)

**Reference Documents:**
*   `specs/detailed_reorganization_plan_phase2.md` (Definitive structure, migration paths, risks)
*   `specs/reorganization_phase3_preparation.md` (Details on scripts and verification plans)
*   `scripts/migration_helpers/` (Location of Agent 6's scripts)
*   `specs/verification/pre_reorg_baseline_procedure.md`
*   `specs/verification/post_reorg_verification_checklist.md`

## 1. Introduction & Objectives

This document outlines the execution steps for Phase 4 of the project reorganization. The primary goal is to implement the changes planned in Phase 2, using the tools and preparations from Phase 3, rigorously verify the outcome, and finalize the project structure.

**Key Objectives:**
*   Establish a pre-reorganization baseline.
*   Execute all automated and manual migration tasks.
*   Thoroughly verify the stability, functionality, and integrity of the reorganized project.
*   Update all relevant documentation to reflect the new structure.
*   Merge changes and conclude the reorganization effort.

## 2. Pre-Execution Steps ( строго Sequential)

1.  **Branch Creation & Code Freeze Announcement (Agent 1 / Co-Captain):**
    *   Task: Ensure a dedicated Git branch (e.g., `feature/project-reorg`) exists and is up-to-date with the main development line.
    *   Task: Announce a "code freeze" on the main development line if deemed necessary to prevent conflicts during the reorganization. For this simulated project, we assume a short freeze or careful coordination is sufficient.
    *   Deliverable: Confirmation of branch readiness and freeze announcement (if any).

2.  **Establish Pre-Reorganization Baseline (Agent 7):
    *   Task: Execute all steps defined in `specs/verification/pre_reorg_baseline_procedure.md`.
    *   Task: Record all results meticulously in `specs/verification/pre_reorg_baseline_results.md` (this file will be created by Agent 7).
    *   Deliverable: Completed `pre_reorg_baseline_results.md` committed to the reorg branch.
    *   **CRITICAL:** Proceed only if baseline is successful (e.g., tests pass, build succeeds).

## 3. Execution Stage (Iterative & Coordinated)

**Coordinator:** Agent 1 / Co-Captain
**Primary Executor of Scripts:** Agent 6

**General Principles:**
*   All script executions by Agent 6 will use the `--execute` flag (after prior successful dry-runs in Phase 3).
*   Changes should be committed in logical chunks to the reorganization branch.
*   Agent 1 to monitor progress and coordinate between agents.

### 3.1. Initial Structure & Consolidation Moves (Agent 6)
*   **Script:** `scripts/migration_helpers/move_archived_content.py --execute`
    *   Action: Consolidates `_archive/` into `archive/`.
*   **Script:** `scripts/migration_helpers/move_sandbox_content.py --execute`
    *   Action: Consolidates `dev_sandbox/` into `sandbox/`.
*   **Script:** `scripts/migration_helpers/move_application_content.py --execute`
    *   Action: Moves contents of `app/` and `apps/` to `src/apps/`.
*   **Manual Cleanup (Agent 6, guided by script output/Phase 2 plan):
    *   Verify `_archive/`, `dev_sandbox/`, `app/`, `apps/` (except `apps/examples` if its destination is still pending) are empty.
    *   Delete these empty directories using `git rm -r <dir>`.
*   **Commit Point:** After initial moves and deletions are verified.

### 3.2. Documentation Migration & Cleanup (Agent 6, Agent 1/4)
*   **Internal `ai_docs` Cleanup (Agent 1/4, then Agent 6 if scripting part):**
    *   Task: Execute steps in `specs/detailed_reorganization_plan_phase2.md` (Section 3.5) to handle `ai_docs/architecture_docs/` duplication.
*   **`docs/` to `ai_docs/` Migration (Agent 6):
    *   Task: Use/adapt helper scripts (conceptualized in Phase 3, Section 2.3) to systematically `git mv` files/directories from `docs/` to their new locations in `ai_docs/` based on `specs/verification/docs_path_mapping.json`.
    *   This may be iterative, section by section.
*   **Manual Cleanup (Agent 6):
    *   Verify `docs/` is empty. Delete with `git rm -r docs/`.
*   **Commit Point:** After documentation migration and old `docs/` deletion.

### 3.3. Path & Link Updates (Agent 6)
*   **Script:** `scripts/migration_helpers/update_python_imports.py --execute`
    *   Action: Updates Python import paths based on defined patterns.
*   **Script:** `scripts/migration_helpers/update_markdown_links.py --execute --mapping_file specs/verification/docs_path_mapping.json`
    *   Action: Updates Markdown links.
*   **Commit Point:** After automated path and link updates. Manual spot checks encouraged before commit.

### 3.4. Configuration & Build Script Updates (Agent 5)
*   **Task:** Based on Agent 5's impact analysis (Phase 2), manually update any paths in:
    *   `pyproject.toml`, `setup.py` (if changes needed beyond `src/` structure which Poetry might handle).
    *   `pytest.ini` (e.g., `pythonpath` is already `src`, but check `testpaths`).
    *   `.github/workflows/ci.yml` (and other CI scripts) for any hardcoded paths or changes to build commands.
    *   Any other configuration files identified.
*   **Commit Point:** After configuration updates.

## 4. Verification Stage (Led by Agent 8)

*   **Task:** Agent 8 to oversee and execute all post-reorganization checks as detailed in `specs/verification/post_reorg_verification_checklist.md`.
*   **Task:** Agent 7 to support Agent 8, especially in running automated test suites and interpreting results.
*   **Task:** All findings to be recorded in `specs/verification/post_reorg_verification_results.md` (created by Agent 8).
*   **CRITICAL:** If major issues are found that cannot be quickly resolved, Agent 8 coordinates with Agent 1/Co-Captain to initiate rollback procedures (Phase 2 Plan, Section 7.4.3.C).

## 5. Finalization Stage (Led by Agent 1 / Co-Captain)

1.  **Issue Resolution:** Address any minor issues found during verification.
2.  **Final Documentation Updates (Agents 2 & 3 - conceptually, or Agent 1/Co-Captain):**
    *   Update project root `README.md` to reflect new structure.
    *   Ensure `ai_docs/` (especially onboarding guides, architectural diagrams) accurately reflects the final state.
3.  **Merge to Main:** Once all checks pass and issues are resolved, merge the reorganization branch into the main development line.
4.  **Announce Completion:** Lift any code freeze and announce the completion of the reorganization.
5.  **Post-Reorganization Monitoring (All Agents):** Monitor the system for any unforeseen issues in the days following the merge.

## 6. Timeline & Agent Assignment Summary (Phase 4)
*   **Pre-Execution:** Agent 1, Agent 7 (Approx. 0.5-1 cycle)
*   **Execution - Moves & Cleanup:** Agent 6, Agent 1/4 (Approx. 1-2 cycles, iterative commits)
*   **Execution - Path/Config Updates:** Agent 6, Agent 5 (Approx. 1 cycle)
*   **Verification:** Agent 8, Agent 7 (Approx. 1-2 cycles, depends on issues found)
*   **Finalization:** Agent 1/Co-Captain, All Agents (Approx. 0.5-1 cycle) 