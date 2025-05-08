# Phase 2: Detailed Reorganization Plan

**Lead Agent (Phase 2 Coordination):** Agent 1 (Lead Analyst & Coordinator)
**Supported by:** Co-Captain
**Primary Author (This Document):** Agent 4 (Structure Architect & Migration Planner)

## 1. Introduction

This document details the definitive target directory structure, migration paths, and rules for the project reorganization. It builds upon the findings and preliminary proposal from `specs/reorganization_proposal_phase1.md`.

The goal is to create a more maintainable, coherent, and flattened project structure, emphasizing the reuse of existing components and adherence to best practices.

## 2. Definitive Target Directory Structure

This section outlines the final proposed directory structure. For each top-level directory, its purpose and rules for content will be defined.

*(Agent 4 will populate this section based on Phase 1 proposal and further analysis. This will be reviewed by Agent 1 and refined in collaboration with Agent 5.)*

### 2.1. `src/` - Primary Python Source Code
*   **Purpose:** Houses all core Python packages and application source code.
*   **Rules:**
    *   All installable Python code resides here.
    *   Follows standard Python package structure.
*   **Subdirectories (Planned):**
    *   `src/dreamos/`: Core DreamOS package.
    *   `src/dreamscape/`: Core Dreamscape package.
    *   `src/apps/`: For distinct applications (migrated from current `apps/` and `app/`). Sub-structure TBD (e.g., `src/apps/sky_viewer`, `src/apps/automation_gui`).
    *   `src/tools/`: For CLI tools or utilities closely tied to the Python packages (e.g., if `scripts/` content is better suited here).

### 2.2. `ai_docs/` - Unified Project Documentation
*   **Purpose:** Single source of truth for all project documentation, knowledge base, architectural designs, guides, etc.
*   **Rules:**
    *   No duplicate documentation elsewhere.
    *   Organized into logical, discoverable categories.
*   **Migration:** Content from `docs/` to be merged and reorganized here.

### 2.3. `tests/` - Test Suites
*   **Purpose:** Contains all automated tests (unit, integration, etc.).
*   **Rules:**
    *   Mirrors the `src/` structure where applicable (e.g., `tests/dreamos/`, `tests/apps/`).

### 2.4. `archive/` - Archived Materials
*   **Purpose:** Storage for obsolete or superseded project materials.
*   **Rules:**
    *   Clear criteria for archival (e.g., deprecated features, old experimental code not in active sandbox).
*   **Migration:** Content from `_archive/` to be merged here.

### 2.5. `sandbox/` - Experimental Code & Prototypes
*   **Purpose:** For experimental code, prototypes, and temporary development work not yet ready for `src/`.
*   **Rules:**
    *   Code here is not considered production-ready or stable.
*   **Migration:** Content from `dev_sandbox/` to be merged here.

### 2.6. `scripts/` - Operational & Utility Scripts
*   **Purpose:** Standalone scripts for build, deployment, operations, or general utilities not part of the core Python packages in `src/`.
*   **Rules:**
    *   If a script becomes a core part of an application or package, it should move to `src/tools/` or within the relevant package.

### 2.7. `prompts/` - LLM Prompts
*   **Purpose:** Collection of prompts for Large Language Models.

### 2.8. `specs/` - Planning & Specifications
*   **Purpose:** Project plans, mission documents, requirements, and this reorganization plan.

### 2.9. `runtime/` - Runtime Data
*   **Purpose:** Dynamic data generated at runtime (logs, agent states, temporary files). Managed by `.gitignore`.

### 2.10. `assets/` - Static Assets
*   **Purpose:** Static files used by applications (e.g., images, UI resources, data files).

### 2.11. `reports/`, `analytics/`, `audit/`
*   **Purpose & Future:** To be finalized based on detailed content analysis from Agent 3 (Phase 1). Potential for consolidation or integration into `ai_docs/` or a new `artifacts/` directory if content is diverse.
    *   *Decision for Phase 2: These directories will be **retained in their current locations for now**. A separate follow-up task (ORG-XXX) should be created for Agent 3 or a dedicated analyst to review their contents in detail. Based on that review, they can be migrated, consolidated, or archived appropriately. This defers detailed analysis to avoid scope creep in the current reorganization phase.*

### 2.12. Root Directory
*   **Contents:** Essential configuration and project files (`.gitignore`, `pyproject.toml`, `README.md`, `LICENSE`, etc.).

## 3. Migration Paths & Actions

*(Agent 4 will detail the specific `mv` operations, merges, deletions, and archival steps here. This will serve as a checklist for Agent 6 in Phase 3.)*

### 3.1. Archive Consolidation

*   **Current Path:** `_archive/`
*   **Action:** Merge & Delete
*   **Target Path:** `archive/`
*   **Rationale:** Consolidate all archived materials into a single `archive/` directory. The `_archive/` naming is non-standard.
*   **Steps:**
    1.  `mv _archive/scripts/* archive/archived_scripts/` (Create `archived_scripts` subdirectory within `archive/` to namespace these specifically from `_archive`).
    2.  `mv _archive/tests/* archive/archived_tests/` (Create `archived_tests` subdirectory).
    3.  Review contents of `archive/from_underscore_archive/` - if it's a duplicate or successfully migrated, delete `archive/from_underscore_archive/`.
    4.  Delete `_archive/` directory.
*   **Notes:** Agent 6 to verify no filename conflicts during merge and ensure history is preserved if using `git mv`. Review contents of `archived_scripts` and `archived_tests` for any items that might still be relevant and could be moved to active `scripts/` or `tests/` directories *before* full archival.

*   **Current Path:** `archive/from_underscore_archive/`
*   **Action:** Review & Delete
*   **Target Path:** N/A (Content should already be in `archive/` if from `_archive`)
*   **Rationale:** Redundant subdirectory, likely from a previous attempt to merge `_archive`.
*   **Steps:**
    1.  Confirm its contents are either duplicates of what's now directly in `archive/` (or its new subdirectories like `archived_scripts`) or are genuinely obsolete.
    2.  Delete `archive/from_underscore_archive/`.
*   **Notes:** This assumes the contents of `_archive/` are moved directly into `archive/` or new subdirectories within it.

### 3.2. Sandbox Consolidation

*   **Current Path:** `dev_sandbox/`
*   **Action:** Merge & Delete
*   **Target Path:** `sandbox/`
*   **Rationale:** Consolidate sandbox/experimental code into a single `sandbox/` directory.
*   **Steps:**
    1.  `mkdir sandbox/legacy_stubs_and_utils/` (Or a more suitable name based on content review).
    2.  `mv dev_sandbox/agent_file_manager_stub.py sandbox/legacy_stubs_and_utils/`
    3.  Review any other files in `dev_sandbox/` and move them to `sandbox/legacy_stubs_and_utils/` or another relevant subdirectory within `sandbox/`.
    4.  Delete `dev_sandbox/` directory.
*   **Notes:** Ensure `agent_file_manager_stub.py` and any other items from `dev_sandbox/` are not actively used or are truly experimental before this move.

### 3.3. Application Code Consolidation (app/ & apps/ to src/apps/)

*   **Objective:** Consolidate all application-specific code under `src/apps/` to align with the `src/` layout for Python packages and improve clarity.

*   **Current Path:** `app/automation/`
*   **Action:** Move & Refactor (Imports may need updates)
*   **Target Path:** `src/apps/automation_gui/` (Assuming `automation` refers to `gui_automation.py`)
*   **Rationale:** To group all applications under `src/apps/`. Renaming to `automation_gui` for clarity if it primarily concerns GUI automation.
*   **Steps:**
    1.  `mkdir -p src/apps/automation_gui/`
    2.  `git mv app/automation/* src/apps/automation_gui/` (or specific files like `gui_automation.py` and its `README.md`).
    3.  Agent 5 & 6: Identify and update all import paths referencing the old location (`app.automation`).
    4.  Delete `app/` directory once empty.
*   **Notes:** `gui_automation.py` and its `README.md` are known contents. If other files exist in `app/automation/`, they should be moved accordingly. Agent 2 (from Phase 1) would ideally provide a dependency map.

*   **Current Path:** `apps/sky_viewer/`
*   **Action:** Move & Refactor
*   **Target Path:** `src/apps/sky_viewer/`
*   **Rationale:** Standardize application location.
*   **Steps:**
    1.  `mkdir -p src/apps/sky_viewer/`
    2.  `git mv apps/sky_viewer/* src/apps/sky_viewer/`
    3.  Agent 5 & 6: Update import paths.
*   **Notes:** Assumes `sky_viewer` is a self-contained application.

*   **Current Path:** `apps/browser/`
*   **Action:** Move & Refactor
*   **Target Path:** `src/apps/browser/`
*   **Rationale:** Standardize application location.
*   **Steps:**
    1.  `mkdir -p src/apps/browser/`
    2.  `git mv apps/browser/* src/apps/browser/`
    3.  Agent 5 & 6: Update import paths.

*   **Current Path:** `apps/examples/`
*   **Action:** Move & Evaluate
*   **Target Path:** `src/examples/` or `ai_docs/examples_and_tutorials/`
*   **Rationale:** Examples might be better placed directly under `src/` if they are runnable code examples for packages in `src/`, or in `ai_docs/` if they are more tutorial-focused.
*   **Steps:**
    1.  Review the nature of content in `apps/examples/`.
    2.  If code examples for `dreamos` or `dreamscape`: `mkdir -p src/examples/` then `git mv apps/examples/* src/examples/`.
    3.  If conceptual/tutorial examples: `mkdir -p ai_docs/examples_and_tutorials/` then `git mv apps/examples/* ai_docs/examples_and_tutorials/`.
    4.  Agent 5 & 6: Update any necessary paths or references.
*   **Notes:** This requires a content review to decide the best location. If `apps/` becomes empty after these moves, it can be deleted.

### 3.4. Documentation Consolidation (docs/ to ai_docs/)

*   **Objective:** Establish `ai_docs/` as the single source of truth for all project documentation.
*   **Strategy:** Carefully migrate content from `docs/` into the existing (or an improved) structure within `ai_docs/`. This is a significant task that requires careful mapping of content.

*   **Current Path:** `docs/` (entire directory)
*   **Action:** Merge, Reorganize & Delete
*   **Target Path:** `ai_docs/`
*   **Rationale:** Eliminate documentation redundancy and centralize knowledge.
*   **High-Level Steps (Agent 4 to detail further; Agent 6 to execute with care):**
    1.  **Analyze `docs/` structure:** Identify all top-level files and subdirectories in `docs/` (e.g., `docs/architecture`, `docs/protocols`, `docs/guides`, `docs/USER_ONBOARDING.md`, `docs/DEVELOPER_GUIDE.md`).
    2.  **Map to `ai_docs/` structure:** For each item in `docs/`, determine its corresponding new location within `ai_docs/`. Leverage existing `ai_docs/` subdirectories (`best_practices/`, `architecture_design_docs/`, `agent_coordination/`, etc.) or propose new ones if needed.
        *   Example Mapping:
            *   `docs/architecture/` -> `ai_docs/architecture_design_docs/` (or a sub-folder within)
            *   `docs/protocols/` -> `ai_docs/protocols_and_standards/` (new or existing)
            *   `docs/guides/` -> `ai_docs/guides_and_tutorials/` (new or existing)
            *   `docs/USER_ONBOARDING.md` -> `ai_docs/onboarding/user_onboarding.md`
            *   `docs/DEVELOPER_GUIDE.md` -> `ai_docs/onboarding/developer_guide.md`
    3.  **Execute Migration (Phased):**
        *   For each mapped section/file: `git mv docs/section_or_file.md ai_docs/target_location/`.
        *   Handle potential naming conflicts or needs for restructuring content during migration.
    4.  **Update Links:** Agent 5 & 6: Crucial step to find and update any cross-references, links in code, or other documentation that point to the old `docs/` paths.
    5.  Once `docs/` is confirmed empty and all links are updated, delete the `docs/` directory.
*   **Notes:** This migration will be complex and iterative. Prioritize high-value, frequently accessed documents. The `ai_docs/` sub-folder structure may need refinement as part of this process based on the content from `docs/`.

### 3.5. Internal `ai_docs` Cleanup (Identified by Agent 5)

*   **Current Path:** `ai_docs/architecture_docs/` (and its `README.md`)
*   **Action:** Review, Merge (if necessary) & Delete
*   **Target Path:** `ai_docs/architecture/README.md`
*   **Rationale:** `ai_docs/architecture_docs/README.md` appears to be a duplicate of `ai_docs/architecture/README.md`. Consolidate to `ai_docs/architecture/` which is a more standard name.
*   **Steps:**
    1.  Agent 1/4 to read both `ai_docs/architecture_docs/README.md` and `ai_docs/architecture/README.md`.
    2.  If `ai_docs/architecture_docs/README.md` has unique, valuable content not in the other, merge it into `ai_docs/architecture/README.md`.
    3.  Delete `ai_docs/architecture_docs/README.md`.
    4.  If `ai_docs/architecture_docs/` directory contains other files, evaluate them for migration or deletion. If it only contained the README, delete the `ai_docs/architecture_docs/` directory.
*   **Notes:** This ensures a cleaner structure within `ai_docs/` before large-scale link updates occur.

## 4. .gitignore Updates

*   The `.gitignore` file was reviewed in Phase 1 and found to be largely comprehensive for existing cache and virtual environment directories.
*   **Action for Agent 6 (during Phase 3 execution):**
    1.  After major structural changes (especially within `src/` and introduction of `src/apps/`), re-verify that build processes, testing, and new tooling do not generate new, unignored artifacts.
    2.  If new cache directories or build outputs appear, add them to `.gitignore`.
*   **Potential areas to check:** Output from any new build steps related to applications in `src/apps/`, or if new linters/tools introduced specific cache formats.

## 5. Naming Conventions

To ensure consistency across the reorganized project:

*   **Directory Names:** `snake_case` (e.g., `ai_docs`, `src/dream_os_internals`). Prefer lowercase.
*   **Python File Names:** `snake_case.py` (e.g., `gui_automation.py`).
*   **Python Package Names:** `snake_case` (e.g., `dreamos`, `some_app_module`).
*   **Test File Names:** `test_snake_case.py` or `snake_case_test.py` (follow existing project patterns, `pytest` discovery rules).
*   **Markdown Files:** `snake_case.md` or `CAPITALIZED_SNAKE_CASE.md` for prominent READMEs/guides (e.g., `USER_ONBOARDING.md`). Consistency within `ai_docs/` is key.
*   **Configuration Files:** Maintain existing conventions (e.g., `pyproject.toml`, `.somethingrc`).
*   **Scripts (non-Python):** `snake_case.sh`, `snake_case.js` etc.
*   **Clarity over Brevity:** Names should be descriptive.
*   **Avoid Redundancy:** Don't repeat parent directory names if unambiguous (e.g., `src/apps/automation_gui/main.py` is better than `src/apps/automation_gui/automation_gui_main.py` unless `main.py` is too generic).

## 6. Next Steps (for Agent 1, 4, 5)

1.  Agent 4: Complete detailed migration paths and rules in this document. *(Status: Done)*
2.  Agent 1 & Co-Captain: Review this detailed plan. *(Status: Done)*
3.  Agent 5 (Impact, Risk & Validation Strategist): Analyze impacts based on this plan and develop validation strategies. *(Status: Pending - See Section 7)*
4.  Agent 1: Lead collaborative session with Agents 4 & 5 to finalize this plan. *(Status: Pending Agent 5's input)*

## 7. Agent 5: Impact, Risk & Validation Strategy Mandate

**Objective:** Agent 5 is tasked with thoroughly analyzing the potential impacts of the proposed reorganization (detailed in Sections 2 & 3 of this document), identifying risks, proposing mitigation strategies, and outlining a comprehensive validation plan for Phase 4 (Execution).

### 7.1. Key Areas for Impact Analysis:

*   **Codebase:**
    *   Identify all code locations (import statements, dynamic path constructions, configuration readers) that will be affected by directory moves (e.g., `app/` to `src/apps/`, `apps/` to `src/apps/`).
    *   Assess impact on inter-module dependencies.
    *   Estimate effort for refactoring import paths (manual vs. automatable by Agent 6).
*   **Build System & CI/CD:**
    *   Analyze impact on `pyproject.toml`, `setup.py`, `pytest.ini` (e.g., path changes for package discovery, test discovery).
    *   Review `.github/workflows/ci.yml` (and other workflows) for necessary path updates or changes to build/test commands.
    *   Consider the `requirements.txt` usage in CI vs. Poetry; this reorganization might be an opportunity to standardize on Poetry for CI dependency management.
*   **Testing Infrastructure:**
    *   Ensure test discovery mechanisms (`pytest.ini`, test runner scripts) will function correctly with new paths.
    *   Identify if any tests rely on hardcoded paths to fixtures or test data that will change.
*   **Documentation & Artifacts:**
    *   Analyze impact of merging `docs/` into `ai_docs/` on internal links, cross-references, and any external systems that might link to current `docs/` paths.
    *   Assess impact on scripts or tools that might consume/generate reports in `reports/`, `analytics/`, `audit/` (though these are deferred for migration, path stability is key).
*   **Developer & Agent Workflows:**
    *   Consider how changes to directory structure might affect common developer/agent tasks (e.g., finding files, running local tests, IDE configurations).
    *   Evaluate impact on any scripts or tools used for local development or agent operations.

### 7.2. Risk Identification & Mitigation:

*   For each impacted area, identify potential risks (e.g., broken builds, runtime errors, test failures, lost Git history if `git mv` is not used correctly, incorrect documentation links).
*   Propose mitigation strategies for each risk (e.g., phased rollout of changes, thorough pre- and post-migration checks, automated link checking tools, specific instructions for Agent 6 on using `git mv`).

### 7.3. Validation Plan Outline (for Phase 4):

*   Define a comprehensive checklist of what needs to be validated post-reorganization.
*   Specify types of tests to be run (e.g., full test suite, specific integration tests, manual smoke tests for key applications).
*   Identify key application functionalities or services that must be confirmed working.
*   Outline steps for establishing a pre-reorganization baseline (e.g., all tests passing, key services operational).
*   Propose rollback procedures in case of critical failures during Phase 4 execution.

### 7.4. Deliverables for Agent 5:

*   A new section in this document (or a linked document) detailing:
    *   Impact Analysis Findings.
    *   Risk Register (Risk, Likelihood, Impact, Mitigation).
    *   Detailed Validation Plan for Phase 4.
*   Estimation of effort/time for validation activities.
*   Recommendations for Agent 6 (Automation Specialist) regarding areas needing careful scripting or manual intervention.

### 7.4.1. Impact Analysis Findings (Initial - Agent 5)

#### Codebase Impacts (Primary focus: `app/` & `apps/` migration to `src/apps/`)

*   **`app/automation/` -> `src/apps/automation_gui/`**:
    *   **Import Paths:**
        *   `from app.automation.gui_automation import ...` found in `app/automation/README.md`. This will need to be updated to `from src.apps.automation_gui.gui_automation import ...` (or similar, depending on how Python resolves `src` in its path).
    *   **Usages of `execute_gui_action`:**
        *   Occurrences are within `app/automation/gui_automation.py` (definition and examples) and its `README.md` (examples).
        *   No widespread external usages were immediately found via `grep_search` for `execute_gui_action(`.
    *   **Preliminary Conclusion:** Impact appears localized to the module itself and its documentation. If it's used as an API by other modules not found by current search, those would break.
        *   *Risk:* Low, if usage is truly localized. Medium, if undiscovered external usages exist.
        *   *Mitigation for README:* Agent 6 to update the example import path in `src/apps/automation_gui/README.md`.
        *   *Mitigation for external usage:* Broader search or static analysis might be needed if high confidence of external usage is required. For now, assume localized.

*   **`apps/sky_viewer/` -> `src/apps/sky_viewer/`**:
    *   **Import Paths:** No `from apps.sky_viewer...` imports found in the codebase via `grep_search`.
    *   **Preliminary Conclusion:** Likely a standalone application or uses only relative internal imports. Risk of breaking external imports appears low.

*   **`apps/browser/` -> `src/apps/browser/`**:
    *   **Import Paths:** No `from apps.browser...` imports found.
    *   **Preliminary Conclusion:** Similar to `sky_viewer`, likely standalone or uses relative internal imports. Risk of breaking external imports appears low.

*   **`apps/examples/` -> `src/examples/` or `ai_docs/examples_and_tutorials/`**:
    *   **Import Paths:** No `from apps.examples...` imports found.
    *   **Preliminary Conclusion:** Path changes will primarily affect how these examples are found and run, rather than breaking imports in other production code.

#### Documentation & Artifacts Impacts (Primary focus: `docs/` to `ai_docs/`)

*   **Links from `ai_docs/` to `docs/`:**
    *   Significant number of relative links (e.g., `../../docs/DEVELOPER_GUIDE.md`) found in:
        *   `ai_docs/best_practices/README.md`
        *   `ai_docs/architecture_docs/README.md` (Note: Appears to be a duplicate of `ai_docs/architecture/README.md` - this duplication should be resolved by Agent 1/4 before/during link updates).
        *   `ai_docs/architecture/README.md`
        *   `ai_docs/api_docs_and_integrations/README.md`
    *   These will require careful path recalculation after `docs/` content is merged into `ai_docs/` subdirectories.
*   **Internal Links within `docs/`:**
    *   Example: `docs/guides/asset_management.md` links to `../standards/task_management.md`.
    *   These relative links will also need updating based on the new locations within `ai_docs/`.
*   **Links from Codebase to `docs/`:**
    *   `tests/core/utils/test_onboarding_utils.py` contains hardcoded paths to `docs/swarm/onboarding_protocols.md`. These test file paths must be updated.
    *   `src/dreamos/core/comms/debate_schemas.py` has a commented-out example path to `docs/`. (Low risk unless similar active code exists elsewhere).
*   **Overall Impact:** High. Manual updates would be error-prone. Agent 6 will need robust methods (e.g., scripting, careful `grep` and replace) for link updates. Agent 8 will need to validate links post-migration.
*   **Risk:** Broken documentation links leading to outdated or inaccessible information.
*   **Mitigation:** Phased migration of `docs/` content, automated link checking tools if available, comprehensive review by Agent 8.

*(Agent 5 to use tools like `codebase_search` and `grep_search` extensively to find all instances of paths that will change and to map dependencies.)*

### 7.4.2. Risk Register (Initial - Agent 5)

| ID  | Risk Description                                                                 | Likelihood | Impact | Mitigation Strategies                                                                                                                               | Owner (Phase) |
|-----|----------------------------------------------------------------------------------|------------|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------|---------------|
| R01 | Broken Python import paths after `app/` & `apps/` migration to `src/apps/`.         | Medium     | High   | - Detailed `grep` by Agent 5 for all potential import patterns. <br>- Agent 6 to use refactoring tools or careful scripts for updates. <br>- Thorough testing by Agent 8. | Agent 5, 6, 8 |
| R02 | Broken Markdown links after `docs/` merge into `ai_docs/`.                         | High       | Medium | - Agent 5 to `grep` for all link patterns. <br>- Agent 6 to use scripts for link updates. <br>- Automated link checker tool. <br>- Manual validation by Agent 8.     | Agent 5, 6, 8 |
| R03 | Build failures (Poetry, CI) due to incorrect path updates in build scripts.      | Medium     | High   | - Agent 5 to identify all build-related files. <br>- Agent 6 to update paths carefully. <br>- Agent 7/8 to run builds in dev branch before merge.        | Agent 5, 6, 7 |
| R04 | Test failures due to incorrect test discovery paths or broken fixture paths.     | Medium     | High   | - Agent 5 to review `pytest.ini` and test code for paths. <br>- Agent 6 to update paths. <br>- Agent 7 to ensure full test suite runs.                 | Agent 5, 6, 7 |
| R05 | Loss of Git history if `git mv` is not used correctly for all moves.             | Low-Medium | Medium | - Clear instructions for Agent 6 to use `git mv` consistently. <br>- Spot checks by Agent 1/8 post-migration.                                     | Agent 6, 1, 8 |
| R06 | Short-term developer/agent workflow disruption due to new structure.             | High       | Low    | - Clear communication of new structure (updated `README.md`, `ai_docs/`). <br>- Provide migration guide/summary.                                     | Agent 1, 3    |
| R07 | CI pipeline (`ci.yml`) fails due to path changes or dependency issues (poetry vs reqs). | Medium     | High   | - Agent 5 to analyze `ci.yml`. <br>- Agent 6 to update paths. <br>- Consider standardizing CI on `poetry install`. <br>- Agent 7/8 to trigger and verify CI. | Agent 5, 6, 7 |

### 7.4.3. Validation Plan Outline (Initial - Agent 5)

**A. Pre-Reorganization Baseline (Responsibility: Agent 7)**

1.  **Full Test Suite Pass:** Execute all `pytest` tests; confirm 100% pass rate. Document any known intermittent failures if they exist and cannot be immediately fixed.
2.  **Successful Build:** Confirm project builds cleanly using `poetry build` (or current standard build process).
3.  **Key Application Functionality:** Manually verify a checklist of critical functionalities for key applications/services (e.g., DreamOS core agent loop, a sample GUI app from `src/apps` if applicable).
4.  **Documentation Snapshot:** (Optional) Note key entry points or structure of `docs/` if useful for comparison.
5.  **Git Status:** Confirm a clean working tree on the dedicated reorganization branch before changes begin.
6.  **CI Pipeline Status:** Ensure the CI pipeline is green on the pre-reorganization commit.

**B. Post-Reorganization Validation (Responsibility: Agent 8, supported by Agent 7)**

1.  **Code Static Analysis:**
    *   Run linters (`ruff`, `flake8`); ensure no new errors related to moved code.
    *   Run type checkers (`mypy`); ensure no new type errors.
2.  **Build System Verification:**
    *   `poetry install` completes successfully.
    *   `poetry build` (or equivalent) completes successfully.
3.  **Full Test Suite Execution:**
    *   All `pytest` tests pass in the new structure.
    *   Test coverage is maintained or improved.
4.  **Documentation Link Validation:**
    *   Employ an automated Markdown link checker (if feasible by Agent 6/7) across `ai_docs/`.
    *   Manually spot-check critical documents and newly migrated sections for correct links and rendering.
    *   Verify links from codebase (e.g., in test files) point to correct new `ai_docs/` locations.
5.  **Application Smoke Tests:**
    *   Re-execute the manual checklist from B.1.3 for key applications to ensure they are operational.
6.  **CI Pipeline Verification:**
    *   The main CI workflow (`.github/workflows/ci.yml`) executes successfully on the reorganized codebase.
    *   All tests and checks within CI pass.
7.  **Git History Integrity:**
    *   Spot-check a few representative moved files/directories to confirm that `git log --follow <file>` shows history prior to the move.
8.  **Developer/Agent Workflow Spot-Checks:**
    *   Verify common commands for running/testing key modules still work as expected (update developer guides if necessary).

**C. Rollback Strategy (To be detailed further by Agent 5/1 if complex)**

*   Primary rollback mechanism: Revert commits on the dedicated reorganization Git branch.
*   For critical, hard-to-revert issues discovered late: Potentially discard the branch and re-plan problematic migrations from the last known good state (backup of the branch before a major step). 