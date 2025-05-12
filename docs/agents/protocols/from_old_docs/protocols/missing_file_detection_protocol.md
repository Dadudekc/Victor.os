# Protocol: Missing File Reference Detection and Resolution

**Version:** 1.0
**Date:** [Current Date]
**Status:** Active (Effective Immediately per General Directive)

## 1. Purpose

This protocol defines the standard procedure for identifying potential references to non-existent files within the Dream.OS codebase and initiating corrective actions. Its goal is to proactively detect and resolve issues caused by missing files (e.g., configuration files, modules, assets) referenced in code, thereby improving system stability and reducing runtime errors.

**Note:** This protocol prioritizes detection and **manual/task-based resolution** over automatic file creation due to the risks associated with generating potentially incorrect or empty placeholder files.

## 2. Scope

This protocol applies to:
*   Regular codebase health checks performed by designated agents or automated tooling.
*   Situations where agents encounter `FileNotFoundError` or similar errors during task execution that suggest a referenced file is missing.

## 3. Procedure

### 3.1 Trigger Conditions

This protocol is triggered when:
*   A scheduled codebase scan (e.g., using a dedicated tool or script) is performed.
*   An agent encounters a persistent error indicating a missing file required for its operation, after basic path validation.

### 3.2 Detection & Scanning Method

1.  **Identify Potential References:** Utilize static analysis techniques to identify potential file references within the codebase (`src/`). Methods include:
    *   **Python Imports:** Analyze `import` statements using `ast` parsing to find modules that cannot be resolved to existing `.py` or `__init__.py` files within the project structure.
    *   **File Operations:** Use pattern matching (e.g., `grep_search`) to find common file access patterns (`open(...)`, `Path(...)`, `read_file(...)`, `load_config(...)`, etc.) and extract the referenced file paths/names.
    *   **Configuration Files:** Scan known configuration files (`.yaml`, `.json`) for file path values.
    *   *(Future Enhancement: Utilize the `project_scanner.py` tool if enhanced to specifically track and validate file references found during analysis.)*
2.  **Verify Existence:** For each potential file reference identified, check if the corresponding file actually exists at the expected location relative to the project root or the referencing file.
3.  **Filter False Positives:** Attempt basic filtering to reduce noise (e.g., ignore references within comments, known external libraries, or clearly dynamic paths that cannot be statically validated).

### 3.3 Reporting

1.  **Generate Report:** Consolidate findings into a structured report (e.g., JSON or Markdown file saved to `runtime/analysis_reports/missing_files_report_[TIMESTAMP].md`).
2.  **Report Content:** Each entry in the report should include:
    *   `missing_file_path`: The suspected path of the missing file.
    *   `referencing_file`: The file(s) containing the reference.
    *   `referencing_line(s)`: The line number(s) where the reference occurs.
    *   `reference_context`: A snippet of the code containing the reference.
    *   `detection_method`: How the reference was found (e.g., "Import AST", "Grep Pattern").
    *   `confidence`: (Optional) A heuristic score indicating confidence that the reference is valid and the file is truly missing.

### 3.4 Resolution Actions

1.  **Review Report:** A designated agent (e.g., Captain Agent 8, or an agent assigned a specific maintenance task) reviews the generated `missing_files_report`.
2.  **Triage Findings:** For each reported missing file:
    *   Determine if the reference is valid (not dead code, etc.).
    *   Determine if the file is genuinely missing or just misplaced/renamed.
    *   Determine the expected content or purpose of the file.
3.  **Create Resolution Tasks:** Based on the triage, create specific tasks in the `future_tasks.json` board:
    *   **Task Type:** `BUG_FIX`, `MAINTENANCE`, or `INVESTIGATION`.
    *   **Description:** Detail the missing file, the referencing location, and the required action (e.g., "Restore file X from source control", "Create file Y with default config schema", "Refactor code in Z to remove reference to obsolete file W").
    *   **Priority:** Assign based on the criticality of the missing file.
    *   **Note:** If a missing file is identified as a blocker during the execution of a high-priority directive (e.g., from General Victor or Commander THEA), the assigned agent should, per the `command_directives_protocol.md`, immediately attempt to reconstruct or restore the missing file with appropriate content based on available context and inferred requirements, showcasing advanced implementation capabilities within reason. This action should be logged and reported.
4.  **Execute Tasks:** Agents claim and execute these resolution tasks according to standard procedures. Creating a file should only occur as part of executing such a specific task, ensuring appropriate content is generated.

## 4. Responsibilities

*   **Scanning Agent/Tool:** Responsible for executing the detection scans and generating the report.
*   **Reviewing Agent (e.g., Captain):** Responsible for reviewing the report, triaging findings, and creating actionable resolution tasks.
*   **Executing Agents:** Responsible for implementing the specific fixes defined in the resolution tasks.

## 5. Review Cycle

This protocol document should be reviewed periodically (e.g., every major release cycle or upon significant changes to project structure/tooling) to ensure its effectiveness and incorporate improved detection methods.
