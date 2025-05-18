# Protocol: Safe File Moving & Refactoring (v0.1 - DRAFT)

**Objective:** Define a standardized, safe procedure for agents to move or rename files and directories within the project structure, minimizing disruption and ensuring dependencies are handled.

**Scope:** This protocol applies to agent-driven refactoring involving file/directory moves or renames within the version-controlled project. It does *not* cover temporary file handling or movements outside the main project structure.

**Core Principles:**

*   **Atomicity:** Prefer `git mv` for simultaneous file system move and version control staging.
*   **Pre-computation:** Analyze source and destination before moving (list contents, check for conflicts).
*   **Dependency Awareness:** Identify and update import paths or references affected by the move.
*   **Verification:** Validate changes post-move (static analysis, tests).
*   **Cleanup:** Remove empty source directories after successful moves.
*   **Rollback:** Be prepared to revert changes if validation fails.

**Procedure:**

1.  **Identify Target(s):** Clearly define the file(s) or directory(ies) to be moved (`source_path`) and the target destination (`destination_path`).
2.  **Analyze Destination:**
    *   Use `list_dir` on the parent of `destination_path`.
    *   Check if a file/directory with the same target name already exists at `destination_path`.
    *   **Conflict Resolution:** If a conflict exists:
        *   **Option A (Rename):** Choose a new, unique name for the item at the destination (e.g., append `_v2`, `_old`, or a more descriptive suffix/prefix). Update `destination_path`.
        *   **Option B (Abort):** If renaming is not feasible or desirable, abort the move for the conflicting item and log the reason. Do *not* overwrite existing files without explicit instruction or a separate merging protocol.
3.  **Analyze Source (if moving a directory):**
    *   Use `list_dir` on `source_path` to understand its contents.
4.  **Identify Dependencies (Crucial Step):**
    *   Use `grep_search` (or similar static analysis tools if available) across the relevant codebase (e.g., `src/`, `tests/`) for import statements or path constructions referencing `source_path` or files within it.
    *   Examples: `from my_old_module import ...`, `Path("path/to/old_dir")`, `include("old/path/file.txt")`.
    *   Maintain a list of files that will require import/path updates.
5.  **Execute Move:**
    *   Use `run_terminal_cmd` with `git mv <source_path> <destination_path>`.
    *   Handle potential command failures (e.g., file not found, permissions). Log errors if they occur.
6.  **Update Dependencies:**
    *   For each file identified in Step 4:
        *   Use `read_file` to get the content.
        *   Use `edit_file` to carefully update the import statements or path references to point to the new `destination_path`. Ensure edits are precise and minimal.
7.  **Cleanup Source Directory (if applicable):**
    *   If the original `source_path` was a directory and its contents were moved (not the directory itself), check if it's now empty (ignoring `.gitkeep`, `__pycache__`, etc.).
    *   Use `run_terminal_cmd` with `Remove-Item` (or `rmdir`/`rm -rf`) to delete the empty source directory.
8.  **Verification:**
    *   Run relevant static analysis checks (e.g., `flake8 src/`, `python -m py_compile <modified_file>`).
    *   *Optional/Future:* Run relevant unit/integration tests if configured and safe to do so.
9.  **Commit:**
    *   Use `run_terminal_cmd` with `git add .` (or specific paths) to stage all related changes (moves, edits, deletions).
    *   Use `run_terminal_cmd` with `git commit -m "refactor: Move <source> to <destination> and update references"` (or similar descriptive message). Handle pre-commit hook failures by re-staging and retrying the commit.
10. **Logging:** Log each major step (analysis, move, update, validation, commit) with relevant paths and outcomes.

**Failure Handling:**

*   If any step fails critically (e.g., `git mv` error, validation failures after updates):
    *   Log the failure point and error details.
    *   Attempt to revert the changes using `git restore .` or `git reset --hard` (use with caution).
    *   Create a task detailing the failed refactoring attempt for manual review or a different agent approach.

---
*Initial Draft - Requires further refinement and testing.* 