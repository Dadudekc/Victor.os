# Specification: classify_files Tool

**Task ID:** CREATE-CLASSIFY-FILES-TOOL-001
**Depends on:** None
**Blocks:** ORPHANED-FILE-CATEGORIZATION-001

## 1. Purpose
To analyze project files based on an import graph and other metadata, classifying them into predefined categories for auditing and cleanup.

## 2. Inputs
- **`import_graph_path`** (str): Path to the `import-graph.json` file.
- **`project_root`** (str): Path to the project's root directory.
- **`output_categories`** (list[str]): List of valid classification categories (from the parent task).
- **`classification_criteria`** (dict[str, str]): Dictionary mapping category names to their descriptive criteria (from the parent task).
- **(Optional) `manifest_path`** (str): Path to a project manifest file (if available) for a complete file list.

## 3. Core Logic
- **Load Data:** Read the `import-graph.json`.
- **Identify Files:** Determine the full list of files to analyze (either from the graph keys or a manifest, falling back to a directory scan if needed).
- **Iterate & Classify:** For each file:
    - Apply rules based on `classification_criteria`.
    - **Rule Implementation (Examples):**
        - `used_dynamically`: Requires searching config files, subprocess calls in code (`grep`), `if __name__ == "__main__":` blocks.
        - `agent_entrypoints`: Check typical agent naming conventions, imports in known launchers (e.g., TaskNexus, mailbox runners).
        - `test_utilities`: Check if path includes `/tests/` or `_test.py` suffix AND is not imported outside of test directories.
        - `deprecated_or_old_versions`: Check filename/path for keywords (legacy, v1, backup, unused, archive).
        - `migration_pending`: Search project TODOs, comments (`grep`).
        - `config_only`: Check file extension (.json, .yaml, .toml, .ini) AND lack of executable code/imports.
        - `plugin_modules`: Check common plugin directory structures or registration patterns.
        - `tool_scripts`: Check path (`/tools`, `/scripts`) or shebang `#!/usr/bin/env python`.
        - `dashboard_or_gui`: Check common UI filenames/paths.
        - `truly_orphaned`: Check if file is NOT imported anywhere (using graph) AND doesn't meet other criteria.
    - Assign the *first matching category* based on a defined priority order (e.g., check for dynamic use before checking for orphaned status).
- **Handle Ambiguity:** If a file matches multiple criteria, establish a clear precedence rule. If no criteria match, assign a default category like 'unclassified'.

## 4. Outputs
- **`classification_report_path`** (str): Path to output the results.
- **Output Format (JSON):**
  ```json
  {
    "metadata": {
      "timestamp": "<ISO timestamp>",
      "import_graph_source": "<path>",
      "categories_used": [...]
    },
    "classifications": {
      "<file_path_relative_to_root>": "<assigned_category>",
      ...
    }
  }
  ```

## 5. Implementation Notes
- Should be implemented as a standalone Python script runnable from the CLI.
- Use standard libraries (json, pathlib, os, re, argparse).
- Consider using `ripgrep` via `subprocess` for efficient text searching if needed for criteria like 'used_dynamically' or 'migration_pending'.
- Robust error handling for file I/O and parsing.
- Clear logging output.
