# Proposal: Resolving `pyproject.toml` Edit Blocker

**Version:** 1.0
**Date:** {{iso_timestamp_utc}}
**Status:** DRAFT
**Author:** Agent5

## 1. Problem Statement

Autonomous agents (specifically Agent5) have repeatedly failed to add Python dependencies to the `pyproject.toml` file using the standard `edit_file` tool. This failure blocks the implementation and testing of features requiring external libraries, such as the Cursor Bridge (`pyautogui`, `pyperclip`, `pytesseract`), Social Media Manager (`undetected-chromedriver`, `selenium`), and potentially others. Manual intervention is currently required for dependency management, hindering autonomous operation.

The exact cause of the `edit_file` failure on `pyproject.toml` is unknown but presumed to be related to file size, complexity (TOML structure), or potential interactions with concurrent processes or file locking mechanisms (though less likely for `pyproject.toml`).

## 2. Goal

Enable reliable, autonomous management of Python dependencies specified in `pyproject.toml`.

## 3. Proposed Solutions

### Option 1: Dedicated Dependency Management Tool/Capability

- **Description:** Implement a dedicated CLI tool or agent capability specifically for adding/removing/updating dependencies in `pyproject.toml`. This tool would handle parsing the TOML structure safely, modifying the correct sections (e.g., `[tool.poetry.dependencies]`), and writing the file back atomically.
- **Implementation:**
    - Use a robust TOML library (e.g., `tomlkit` which preserves formatting, or `tomli`/`tomllib` for basic parsing/writing).
    - Create a new CLI script (e.g., `src/dreamos/cli/manage_deps.py`) with commands like `add-dep <package>`, `remove-dep <package>`.
    - Alternatively, create an agent capability (e.g., `system.manage_dependency`) that encapsulates this logic.
- **Pros:** Most robust and maintainable solution; isolates dependency logic; less prone to errors than generic file edits.
- **Cons:** Requires initial development effort for the tool/capability.

### Option 2: Enhanced `edit_file` Robustness (Investigative)

- **Description:** Investigate *why* `edit_file` fails specifically for `pyproject.toml`. Potential causes:
    - **Size/Complexity:** The current `edit_file` approach might struggle with larger/structured files.
    - **Concurrency/Locking:** Unlikely, but worth checking if other processes access the file.
    - **Tool Bug:** A specific bug in the `edit_file` application logic.
- **Implementation:** Requires deeper debugging of the `edit_file` tool's interaction with this specific file. This may involve adding more detailed logging to the tool or attempting edits with varying context sizes.
- **Pros:** Fixes the existing tool without adding new ones (if successful).
- **Cons:** May not be feasible if the issue is inherent to the generic edit approach; potentially time-consuming investigation.

### Option 3: Manual Edits + Validation Hook (Short-Term Workaround)

- **Description:** Continue with manual edits of `pyproject.toml` when required by agents, but implement an automated validation hook (e.g., pre-commit hook or CI step) that ensures the file remains valid TOML and potentially checks for dependency conflicts using `poetry check`.
- **Implementation:**
    - Add a `check-toml` hook to `.pre-commit-config.yaml`.
    - Add a `poetry check` execution step in CI or a local validation script.
    - Agents would request manual edits when blocked on dependencies.
- **Pros:** Requires minimal immediate development; ensures basic file integrity.
- **Cons:** Does *not* solve the autonomy problem; relies on manual intervention; slows down development cycles.

### Option 4: Containerization

- **Description:** Define project dependencies within container definitions (e.g., `Dockerfile`, `docker-compose.yml`) instead of solely relying on `pyproject.toml` for runtime environments. Agents could potentially trigger container builds/updates.
- **Implementation:** Requires setting up container infrastructure and defining service dependencies within container files. Agents would need capabilities to interact with Docker/container orchestration.
- **Pros:** Encapsulates environment and dependencies reliably; good for deployment consistency.
- **Cons:** Significant infrastructure overhead; adds complexity to local development and agent interaction; doesn't directly solve editing `pyproject.toml` for source consistency, only for runtime environment setup.

## 4. Recommendation

**Option 1 (Dedicated Dependency Management Tool/Capability)** is the recommended long-term solution. It directly addresses the need for reliable, autonomous dependency updates in a structured way, aligning best with Dream.OS principles of specialized tools and robust automation.

**Option 3 (Manual Edits + Validation Hook)** can serve as an acceptable short-term workaround to unblock current tasks while Option 1 is being developed.

## 5. Next Steps (If Option 1 Approved)

1.  Create task: `IMPLEMENT-DEP-MANAGER-TOOL-001` - Implement `src/dreamos/cli/manage_deps.py` using `tomlkit`.
2.  Create task: `INTEGRATE-DEP-MANAGER-CAP-001` - Expose dependency management as an agent capability.
3.  Update agent protocols/training to use the new tool/capability instead of attempting `edit_file` on `pyproject.toml`. 