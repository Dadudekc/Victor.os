# Phase 1: Reorganization Proposal (Initial Draft)

This document outlines the initial findings and proposal for project reorganization as per the multi-agent strategy.

## Agent 1: Lead Analyst & Coordinator

### Objective:
Co-lead the reorganization effort with Agent 4, oversee the discovery and planning phase, collate findings, identify patterns and redundancies, and drive the execution of Phase 1.

### Initial Observations (High-Level Patterns & Redundancies):

Based on a preliminary review of the root directory structure, the following potential redundancies or areas for consolidation have been identified:

*   **Archives:**
    *   `_archive/`
    *   `archive/`
    *   *Consideration: Consolidate into a single, clearly defined archive directory.*

*   **Sandboxes:**
    *   `dev_sandbox/`
    *   `sandbox/`
    *   *Consideration: Merge into a unified sandbox or development testing area with clear guidelines.*

*   **Applications/Modules:**
    *   `app/` (currently contains `automation/`)
    *   `apps/` (contains `sky_viewer/`, `examples/`, `browser/`)
    *   `src/` (contains `dreamos/`, `dreamscape/`, `tools/` - appears to be the main Python source root)
    *   *Decision: `app/automation/` and the contents of `apps/` (`sky_viewer/`, `examples/`, `browser/`) will be consolidated into a new `src/apps/` directory. Agent 4 to detail the internal structure. Agent 2's dependency analysis will inform final placement if any issues arise.*

*   **Documentation:**
    *   `ai_docs/` (defined as a persistent knowledge base)
    *   `docs/` (purpose to be clarified by Agent 3)
    *   *Decision: Merge `docs/` into `ai_docs/` to serve as the single source of truth for all project documentation. Agent 3's simulated findings support this; Agent 4 to detail the merged structure within `ai_docs/`.*

*   **Cache/Build/Ignored Directories:**
    *   `htmlcov/` (likely test coverage reports)
    *   `.ruff_cache/`
    *   `.dreamos_cache/`
    *   `.venv/` (Python virtual environment)
    *   `.mypy_cache/`
    *   `__pycache__/` (Python bytecode cache)
    *   `.pytest_cache/`
    *   `node_modules/` (Node.js dependencies)
    *   *Action for Agent 2: Verify these are all appropriately handled by `.gitignore` and confirm their specific roles (e.g., build outputs vs. local dev caches).*

### Next Steps for Phase 1:

1.  **Agent 2 (Code & Build Structure Analyst):**
    *   Analyze code dependencies (`*.py`, `*.js`) focusing on `app/`, `apps/`, `bridge/`, `runtime/`, `scripts/`, `assets/`, `src/`.
    *   Examine build scripts (`setup.py`, `package.json`, `Makefile`, `pyproject.toml`), CI/CD (`.github/workflows/`), testing configs (`pytest.ini`).
    *   Investigate and confirm the purpose/handling of cache directories.
    *   **Initial Findings (Simulated):**
        *   `.gitignore` appears comprehensive and correctly handles common cache/temporary directories (`__pycache__/`, `.pytest_cache/`, `.venv/`, `.mypy_cache/`, `.ruff_cache/`, `.dreamos_cache/`, `htmlcov/`, `node_modules/`).
        *   `setup.py` is minimal and points to `src/` as the package root (`packages=find_packages(where="src")`, `package_dir={"": "src"}`).
        *   `pyproject.toml` (using Poetry) also confirms `src/` as the source root for `dreamos` and `dreamscape` packages (`packages = [{ include = "dreamos", from = "src" }, { include = "dreamscape", from = "src" }]`). It lists extensive dependencies and dev tools (pytest, ruff, mypy, black, isort).
        *   `pytest.ini` sets `pythonpath = src`, further confirming `src/` as the primary source directory for tests.
        *   `.github/workflows/ci.yml` exists and runs pytest. It currently uses `pip install -r requirements.txt` for dependencies, which might need alignment with the Poetry setup indicated in `pyproject.toml`.

2.  **Agent 3 (Documentation, Artifacts & Usage Analyst):**
    *   *Note: Gemini will assist with these tasks.*
    *   Examine content and purpose of `ai_docs/`, `docs/`, `specs/`, `prompts/`, `reports/`, `analytics/`, `audit/`.
    *   Determine the nature of content in `_archive/`, `archive/`, `dev_sandbox/`, `sandbox/`.
    *   Identify existing structure documentation and current workflows.
    *   **Initial Findings (Simulated):**
        *   **`docs/` vs. `ai_docs/`**: `docs/` is extensive (contains `architecture/`, `protocols/`, `guides/`, `USER_ONBOARDING.md`, `DEVELOPER_GUIDE.md`, etc.). `ai_docs/` was previously scaffolded with similar-themed directories (`architecture_design_docs/`, `best_practices/`, etc.). There is a strong potential for overlap and consolidation. The guiding principle might be to merge general development/project documentation from `docs/` into the structured `ai_docs/` knowledge base, ensuring `ai_docs/` becomes the single source of truth for all project documentation.
        *   **`_archive/` vs. `archive/`**: `_archive/` contains `scripts/` and `tests/`. `archive/` contains `legacy_automation/` and, tellingly, `from_underscore_archive/`. This confirms redundancy and suggests `archive/` is the intended primary archive, but consolidation and cleanup are needed.
        *   *Decision: `_archive/` will be merged into `archive/`. Agent 4 to detail the merged structure.*
        *   **`dev_sandbox/` vs. `sandbox/`**: `dev_sandbox/` contains a single file (`agent_file_manager_stub.py`). `sandbox/` is extensive with many sub-projects and experimental modules. `dev_sandbox/` appears to be a candidate for merging into the larger `sandbox/` or being archived if obsolete.
        *   *Decision: `dev_sandbox/` contents will be merged into `sandbox/`. Agent 4 to determine the best location (e.g., `sandbox/legacy_stubs/` or `sandbox/misc_utils/`).

3.  **Agent 1 (Lead Analyst & Coordinator):**
    *   Collate findings from Agents 2 & 3.
    *   Refine this proposal based on detailed analysis.
    *   In coordination with Agent 4, develop and finalize the target structure proposal and oversee Phase 1 execution.
    *   Specifically investigate the relationship and optimal structure for `src/`, `app/`, and `apps/`.
    *   Develop a preliminary target structure proposal.

4.  **Agent 4 (Co-Lead & Target Structure Design):**
    *   Collaborate with Agent 1 on overall Phase 1 leadership.
    *   Begin detailing the target internal structure for the consolidated directories:
        *   `src/apps/` (integrating `app/automation/` and current `apps/*` contents like `sky_viewer/`, `examples/`, `browser/`. Agent 4 to define the internal layout e.g., `src/apps/automation/`, `src/apps/sky_viewer/`, etc.).
        *   `ai_docs/` (after merging `docs/`. Agent 4 to detail the merged structure.
        *   `archive/` (after merging `_archive/`. Agent 4 to detail the merged structure.
        *   `sandbox/` (after merging `dev_sandbox/`. Agent 4 to determine the best location (e.g., `sandbox/legacy_stubs/` or `sandbox/misc_utils/`).
    *   Document these detailed structures for review and Phase 2 implementation planning.

5.  **Agent 6 (Support & Verification):**
    *   Assist Agent 1 and 3 by gathering detailed information for merge operations. Initially:
        *   List the full contents (files and subdirectories) of `docs/`.
        *   List the full contents (files and subdirectories) of `_archive/`.
    *   Perform verification checks on proposed file/directory moves before execution.

6.  **All Agents (Ongoing Task - Coordinated by Agent 1 & 4): Codebase Audit & Refinement (`PROJECT: AUTOMATE THE SWARM`)**
    *   Systematically review, clean, and organize the Dream.OS codebase file-by-file or module-by-module as assigned.
    *   Focus on: reducing complexity, improving folder structure (aligned with Agent 4's designs), enhancing naming clarity, adding/improving docstrings and comments, and identifying areas for refactoring.
    *   This is a continuous effort alongside specific reorganization tasks.

---

## Phase 1 Consolidation Targets & Preliminary Structure (Detailed by Agent 4)

Based on initial findings, the following preliminary target structure is proposed for discussion and refinement:

1.  **`src/`**: Primary Python source root.
    *   `src/dreamos/` (Core package)
    *   `src/dreamscape/` (Core package)
    *   `src/apps/` (New consolidated home for `app/automation/` and applications from the current `apps/` directory e.g., `sky_viewer/`, `examples/`, `browser/`. Agent 4 to define the internal layout e.g., `src/apps/automation/`, `src/apps/sky_viewer/`, etc.).
    *   `src/tools/` (Existing, for CLI tools or utilities closely tied to the Python packages if not fitting into `dreamos` or `dreamscape`.)

2.  **`ai_docs/`**: Single source of truth for all documentation.
    *   Systematically merge content from the current `docs/` directory into `ai_docs/`. Agent 4 to detail the merged structure.
    *   Organize based on the existing `ai_docs/` categories or refine/expand these categories as needed.
    *   Ensure `USER_ONBOARDING.md` and `DEVELOPER_GUIDE.md` are integrated.

3.  **`archive/`**: Single, unified archive directory.
    *   Merge all relevant content from `_archive/` into `archive/`. Agent 4 to detail the merged structure.
    *   Establish clear criteria for what constitutes archived material.

4.  **`sandbox/`**: Unified sandbox and experimental code directory.
    *   Merge `dev_sandbox/agent_file_manager_stub.py` (and any other `dev_sandbox` contents) into an appropriate subdirectory within `sandbox/`. Agent 4 to determine the best location (e.g., `sandbox/legacy_stubs/` or `sandbox/misc_utils/`).

5.  **`tests/`**: Centralized directory for all tests.
    *   Structure should ideally mirror the `src/` directory structure for clarity (e.g., `tests/dreamos/`, `tests/apps/`).

6.  **`scripts/`**: For standalone operational or utility scripts (e.g., shell scripts, helper Python scripts not part of the core installable packages).
    *   Evaluate if any scripts currently in `_archive/scripts/` are still relevant and should be moved here or to `src/tools/`.

7.  **`prompts/`**: Retain for LLM prompts; structure to be reviewed by relevant agents if extensive.

8.  **`specs/`**: Retain for project planning, mission documents, and this reorganization plan.

9.  **`runtime/`**: Retain for dynamic runtime data, logs, agent states, etc. Already well-managed by `.gitignore`.

10. **`assets/`**: Retain for static assets used by applications (images, UI elements, etc.).

11. **`reports/`, `analytics/`, `audit/`**: Agent 3 Initial Analysis & Recommendations:
    *   **`reports/` Directory:**
        *   **Current State:** Contains a mix of specific reports (e.g., `final_bridge_report.json`), general scanner outputs (`project_analysis.json`, `dependency_cache.json`), an `audit/` subdirectory with audit results, and a `.dreamos_cache/`.
        *   **Recommendation:**
            *   Relocate general scanner outputs (`project_analysis.json`, `dependency_cache.json`, `chatgpt_project_context.json`, `import-graph.json`, `todo_report.md`) to the project root or a dedicated `runtime/scanner_outputs/` directory.
            *   Relocate `.dreamos_cache/` to the project root and ensure it's in `.gitignore`.
            *   `reports/` should then be a cleaner directory for actual generated reports and could retain `reports/audit/` for audit-specific report files.
            *   Consider renaming `reports/` to `generated_reports/` for clarity.
    *   **`analytics/` Directory:**
        *   **Current State:** Contains Python scripts (e.g., `temporal_ledger_auditor.py`), `analytics_standards.json`, and `docs/`, `scripts/` subdirectories. Appears to be a source/tooling directory for analytics capabilities.
        *   **Recommendation:** Evaluate if `analytics/` and its contents should be integrated into the main `src/` structure (e.g., as `src/tools/analytics/` or `src/dreamos/analytics_tools/`) if these are core system tools. If they are standalone utility scripts, consider `scripts/analytics/`. The contained `docs/` and `scripts/` should follow their parent's relocation.
    *   **`audit/` Directory (Root):**
        *   **Current State:** Contains `audit/src/dreamos/`, appearing to be a mirrored copy of the main `dreamos` source.
        *   **Recommendation:** Investigate the purpose and currency of this mirrored source. If it's for specific, point-in-time audit processes, document its lifecycle. If obsolete, archive or delete. Its existence should be justified. The results of audits (potentially run on this mirrored code) appear to be correctly stored in `reports/audit/`.
    *   **Consolidation Note:** Depending on findings from the above, these might be consolidated, moved under a general `artifacts/` directory, or integrated elsewhere (e.g., specific reports into `ai_docs/` if they are long-lived documentation). *This original note from the proposal remains relevant and will depend on decisions made based on the above recommendations.*

12. **Root Files**: Maintain essential root files like `.gitignore`, `pyproject.toml`, `README.md`, `LICENSE`, etc.

This structure aims to achieve the goals of flattening, organizing, and integrating, while leveraging `src/` as the standard for Python code.

*This is a living document and will be updated as Phase 1 progresses.*

## Team Roles

- **Co-Captain**: Gemini (AI Assistant) - Facilitating overall project success and supporting Agent 1.
- **Agent 1**: Gemini (AI Assistant) - Lead Analyst & Coordinator.
- **Agent 2**: Gemini (AI Assistant) - Will assist with planning, execution, and verification of Phase 1 reorganization tasks.
- **Agent 4**: Gemini (AI Assistant) - Co-Lead & Target Structure Design for Phase 1 & 2.
- **Agent 6**: Gemini (AI Assistant) - Will contribute to reorganization tasks as assigned. 