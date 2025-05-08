# Post-Reorganization Verification Checklist

**Phase:** 3 (Implementation Preparation & Tooling) -> For use in Phase 4 (Execution & Verification)
**Lead Agent (Execution):** Agent 8 (Quality Assurance & Rollback Lead)
**Developed by:** Agent 7 (Test & Verification Suite Developer)
**Coordinator:** Agent 1 / Co-Captain
**Reference:** `specs/reorganization_phase3_preparation.md` (Section 3.2), `specs/detailed_reorganization_plan_phase2.md` (Section 7.4.3)

## 1. Objective

To provide a detailed checklist for manual verification steps to be performed by Agent 8 *after* the reorganization scripts (Phase 4) have been executed. This complements automated tests and build checks.

## 2. Prerequisites for Starting this Checklist

*   All automated migration scripts (from Agent 6) have been successfully run on the reorganization branch.
*   Automated post-reorganization checks (full test suite, build, linters, type checkers as per Validation Plan Outline B.1, B.2, B.3) have passed successfully.
*   CI Pipeline is green on the post-reorganization commit.

## 3. Manual Verification Checklists

### 3.1. Application Smoke Tests (Post-Reorganization)

*   **Reference:** Baseline established in `specs/verification/pre_reorg_baseline_results.md` (Section 3.3).
*   **Instructions:** For each item, verify functionality in the reorganized codebase. Record Pass/Fail and any observations.

| Application / Feature                     | Expected Behavior (from Baseline)                                 | Actual Behavior (Post-Reorg) | Result (Pass/Fail) | Notes                                                                 |
|-------------------------------------------|-------------------------------------------------------------------|------------------------------|--------------------|-----------------------------------------------------------------------|
| **DreamOS Core Agent System**             |                                                                   |                              |                    |                                                                       |
| Agent Startup                             | Agent starts without errors.                                      |                              |                    |                                                                       |
| Simple Task Claim                         | Agent claims task from `future_tasks.json`.                       |                              |                    |                                                                       |
| Task State Update                         | `working_tasks.json` updated correctly.                           |                              |                    |                                                                       |
| Task Output                               | Expected output/log generated for the simple task.                |                              |                    |                                                                       |
| **`src/apps/automation_gui/` (if main/demo)** |                                                                   |                              |                    |                                                                       |
| GUI Loads                                 | GUI loads without errors.                                         |                              |                    | Check console for errors.                                             |
| Simple Action (e.g., mouse move)        | Action executes as expected from example.                         |                              |                    | Ensure it uses the new `src.apps...` import if applicable in example. |
| **`src/apps/sky_viewer/` (if runnable)**    |                                                                   |                              |                    |                                                                       |
| Application Launch                        | Application launches.                                             |                              |                    |                                                                       |
| Core Viewing Functionality                | Load sample, navigate.                                            |                              |                    |                                                                       |
| **`src/apps/browser/` (if runnable)**       |                                                                   |                              |                    |                                                                       |
| Application Launch                        | Application launches.                                             |                              |                    |                                                                       |
| Basic Browser Interaction                 | Basic interaction works.                                          |                              |                    |                                                                       |
| *(Agent 7/8 to add other key apps/features)* |                                                                   |                              |                    |                                                                       |

### 3.2. Documentation Spot-Checks (Post-Reorganization `ai_docs/`)

*   **Objective:** Verify integrity of key documents and recently migrated/merged content.
*   **Instructions:** For each item, open the document, check rendering, and verify key internal/external links.

| Document Path (in `ai_docs/`)             | Check Items                                                                                                | Result (Pass/Fail) | Notes                                                                                                |
|-------------------------------------------|------------------------------------------------------------------------------------------------------------|--------------------|------------------------------------------------------------------------------------------------------|
| `README.md` (Project Root, if updated)    | Overall rendering, key links (e.g., to `ai_docs/onboarding/developer_guide.md`).                            |                    |                                                                                                      |
| `onboarding/developer_guide.md`           | Content merged from old `docs/DEVELOPER_GUIDE.md` is present and correct. Key sections link correctly.         |                    | Example: Check link to `project_structure.md` (new name for `project_tree.txt` as per ORG-004).        |
| `onboarding/user_onboarding.md`           | Content merged from old `docs/USER_ONBOARDING.md` is present and correct.                                  |                    |                                                                                                      |
| `architecture/README.md`                  | Key architectural diagrams/links are valid. (Ensure `ai_docs/architecture_docs/` was correctly removed/merged). |                    |                                                                                                      |
| `best_practices/README.md`                | Links to standards/protocols (migrated from `docs/standards` etc.) are working.                            |                    |                                                                                                      |
| *A few other key migrated docs (TBD)*     | Check rendering, internal links, and a few external links if any.                                          |                    | E.g., A migrated protocol doc, a design doc.                                                         |
| `specs/reorganization_phase3_preparation.md` | (Self-check) Links to Phase 2 plan are correct.                                                            |                    |                                                                                                      |

### 3.3. Git History Integrity Checks (Spot Checks)

*   **Objective:** Verify `git mv` was used and history is preserved for key moved items.
*   **Instructions:** For a few representative files/directories that were moved, use `git log --follow <new_path_to_item>`.

| Item New Path                                     | Expected Outcome                                       | Actual History (Briefly) | Result (Pass/Fail) | Notes |
|---------------------------------------------------|--------------------------------------------------------|--------------------------|--------------------|-------|
| `src/apps/automation_gui/gui_automation.py`       | Log shows history from `app/automation/...`            |                          |                    |       |
| `archive/archived_scripts/some_script.sh` (pick one) | Log shows history from `_archive/scripts/...`          |                          |                    |       |
| `ai_docs/onboarding/developer_guide.md`           | Log shows history from `docs/DEVELOPER_GUIDE.md`       |                          |                    |       |
| *(Agent 8 to pick 2-3 more examples)*             |                                                        |                          |                    |       |

## 4. Reporting

*   Agent 8 to fill out this checklist meticulously during Phase 4 verification.
*   All findings, Pass/Fail results, and notes should be recorded directly in a copy of this file, likely named `specs/verification/post_reorg_verification_results.md`.
*   Any "Fail" result must be flagged immediately to Agent 1/Co-Captain for investigation and potential rollback/remediation planning. 