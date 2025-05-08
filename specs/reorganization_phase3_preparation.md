# Phase 3: Implementation Preparation & Tooling

**Lead Agent (Phase 3 Coordination):** Agent 1 (Lead Analyst & Coordinator)
**Supported by:** Co-Captain

## 1. Introduction & Objectives

This document outlines the tasks for Phase 3 of the project reorganization: Implementation Preparation & Tooling. The primary goal of this phase is to prepare all necessary scripts, tools, test suites, and checklists required for the smooth execution of the reorganization detailed in `specs/detailed_reorganization_plan_phase2.md`.

**Key Objectives:**
*   Develop automation scripts for file/directory migration and code/documentation refactoring (Agent 6).
*   Augment existing test suites and develop verification checklists to ensure post-reorganization stability (Agent 7).
*   Establish a pre-reorganization baseline for tests and system functionality (Agent 7).
*   Ensure all preparations are complete before moving to Phase 4 (Execution).

## 2. Agent 6: Automation & Scripting Specialist - Tasks

**Primary Reference:** `specs/detailed_reorganization_plan_phase2.md` (especially Section 3: Migration Paths & Actions).

### 2.1. Script Development for File & Directory Migration
*   **Task:** Develop scripts (Python or shell) to automate the `mv` operations outlined in Section 3 of the Phase 2 plan.
*   **Requirements:**
    *   Scripts **must** use `git mv` to preserve file history.
    *   Implement dry-run capabilities for all scripts.
    *   Ensure scripts are idempotent where possible (e.g., can be re-run without negative side-effects if a step failed midway).
    *   Handle potential conflicts (e.g., if a target directory for a move already exists unexpectedly).
    *   Log all actions performed.
*   **Specific Migrations to Script (from Phase 2 Plan - Section 3):**
    *   3.1. Archive Consolidation (`_archive/` to `archive/`).
    *   3.2. Sandbox Consolidation (`dev_sandbox/` to `sandbox/`).
    *   3.3. Application Code Consolidation (`app/` & `apps/` to `src/apps/`).
    *   3.5. Internal `ai_docs` Cleanup (`ai_docs/architecture_docs/` deletion/merge).

### 2.2. Script Development for Path/Link Updates
*   **Task:** Develop scripts to automate updating import paths in Python code and links in Markdown documentation.
*   **Python Import Path Updates (related to Section 3.3 migration):
    *   Search for affected import statements (e.g., `from app.automation...`, `from apps.sky_viewer...`).
    *   Replace with new paths (e.g., `from src.apps.automation_gui...`, `from src.apps.sky_viewer...`).
    *   Consider using AST-based refactoring tools for Python if simple regex is too risky, or focus regex on very specific, confirmed patterns.
*   **Markdown Link Updates (related to Section 3.4 migration):
    *   Analyze link patterns identified by Agent 5 (Phase 2 Plan, Section 7.4.1).
    *   Develop scripts to update relative and absolute links in `.md` files within `ai_docs/` and any affected code/test files.
    *   Handle different link formats and path recalculations carefully.
*   **Requirements for Path/Link Update Scripts:**
    *   Dry-run mode is essential.
    *   Backup original files before modification (or ensure operations are on a Git branch).
    *   Log all changes made.

### 2.3. Tooling for `docs/` to `ai_docs/` Content Merge (Section 3.4)
*   **Task:** While full content-aware merging is complex, develop helper scripts for Agent 6 to:
    *   Systematically list files in `docs/` and their proposed target locations in `ai_docs/` (based on the mapping Agent 4/1 will finalize).
    *   Automate the `git mv` of individual files/directories from `docs/` to `ai_docs/` once the target sub-structure in `ai_docs/` is created/confirmed.
    *   Potentially a script to identify broken Markdown links *after* moves, to help Agent 8's validation (if a full pre-emptive update script is too complex).

## 3. Agent 7: Test & Verification Suite Developer - Tasks

**Primary Reference:** `specs/detailed_reorganization_plan_phase2.md` (especially Section 7.4.3: Validation Plan Outline).

### 3.1. Augment Test Suites
*   **Task:** Review existing test suites (`tests/`) and identify areas needing augmentation to specifically cover changes due to reorganization.
*   Focus on integration points affected by moved modules (e.g., if `automation_gui` is called by another service, ensure tests cover this interaction with the new path).
*   Ensure tests for any applications moved into `src/apps/` are robust and correctly discovered.

### 3.2. Develop Detailed Verification Checklists
*   **Task:** Expand the Validation Plan Outline (Phase 2 Plan, Section 7.4.3) into detailed, step-by-step checklists for manual verification.
*   **Checklists Needed:**
    *   Pre-reorganization baseline checks.
    *   Post-reorganization application smoke tests (for key apps identified).
    *   Post-reorganization documentation spot-checks (key documents, link integrity).

### 3.3. Establish Pre-Reorganization Baseline Procedures
*   **Task:** Formalize the procedure for capturing the pre-reorganization baseline (as outlined in Phase 2, Section 7.4.3.A).
*   Document commands to run tests, build the project, etc., and where to record the results (e.g., a specific Markdown file in `specs/`).
*   Ensure the project can be cleanly built and all tests pass in the current state on the reorganization branch *before* Agent 6 runs any migration scripts.

## 4. Collaboration & Next Steps

*   Agent 6 and 7 will work in parallel, providing updates to Agent 1/Co-Captain.
*   Agent 1/Co-Captain to facilitate any clarifications needed from the Phase 2 plan.
*   Once scripts are developed and tested (dry-run), and baseline procedures are ready, Phase 3 will conclude, and the project will be ready for Phase 4 (Execution).

**STATUS UPDATE (Agent 1/Co-Captain):** Phase 3 is now considered COMPLETE.
*   Agent 6 has drafted and performed initial dry-runs of all migration and update scripts.
*   Agent 7 has finalized the pre-reorganization baseline procedure, drafted the post-reorganization verification checklist, and identified areas for test suite augmentation.
*   The project is now ready to proceed to Phase 4: Execution, Verification & Finalization. 