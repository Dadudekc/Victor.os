# Project Scanner

## Overview
The `project_scanner.py` script is used for scanning the Dream.OS project. It analyzes the project's structure, performs language-specific analysis (functions, classes, etc.), and generates reports including `project_analysis.json` and `chatgpt_project_context.json`.

## Requirements
The script requires a valid main configuration file (`config.yaml`) for the Dream.OS project, as it uses settings from this file (e.g., default project root if not specified via CLI, paths for tree-sitter grammars).

The default main config file path used by the script is determined by `dreamos.core.config.DEFAULT_CONFIG_PATH` (typically `D:/Dream.os/runtime/config/config.yaml`).

## Running the Script
To run the script from the project's root directory (`D:/Dream.os`), use the following command structure:

```bash
python -m dreamos.tools.analysis.project_scanner.project_scanner [PROJECT_ROOT_TO_SCAN] [OPTIONS]
```

**Arguments & Options:**

*   `PROJECT_ROOT_TO_SCAN` (optional):
    *   The path to the project directory you want to scan.
    *   If not provided, the script defaults to the `paths.project_root` value specified in your main `config.yaml`. If this value in `config.yaml` is, for example, `D:/Dream.os/runtime/config`, then only that subdirectory will be scanned.
    *   **To scan the entire Dream.OS project (e.g., `D:/Dream.os`), you should provide it explicitly:**
        ```bash
        python -m dreamos.tools.analysis.project_scanner.project_scanner D:/Dream.os
        ```
*   `--exclude PATTERN`:
    *   Directory or file patterns to exclude (e.g., `node_modules`, `*.log`). Can be used multiple times.
*   `--force-rescan PATTERN`:
    *   Glob patterns for files to forcibly rescan even if unchanged (e.g., `**/config.py`). Can be used multiple times.
*   `--clear-cache`:
    *   Clear the scanner's dependency/hash cache before scanning.
*   `--no-cache`:
    *   Disable using the cache entirely for this run.
*   `--analysis-output FILE_PATH`:
    *   Output path for the detailed analysis JSON file (default: `[PROJECT_ROOT_TO_SCAN]/project_analysis.json`).
*   `--context-output FILE_PATH`:
    *   Output path for the condensed ChatGPT context JSON file (default: `[PROJECT_ROOT_TO_SCAN]/chatgpt_project_context.json`).
*   `--cache-file FILE_PATH`:
    *   Path to the scanner's dependency cache file (default: `[PROJECT_ROOT_TO_SCAN]/.dreamos_cache/dependency_cache.json`).
*   `--workers NUM_WORKERS`:
    *   Number of worker threads for analysis (default: 4).
*   `--template-path FILE_PATH`:
    *   Path to a custom Jinja2 template file for ChatGPT context generation.
*   `--debug`:
    *   Enable debug logging.

**Example (scan entire project, clear cache):**
```bash
python -m dreamos.tools.analysis.project_scanner.project_scanner D:/Dream.os --clear-cache
```

## Output Files

1.  **`project_analysis.json`**: Contains detailed analysis of each scanned file, including language, functions, classes, routes, complexity, and any identified agent roles.
2.  **`chatgpt_project_context.json`**: A condensed version of the analysis, potentially structured for use as context with LLMs.
3.  **`__init__.py` files**: The script automatically generates/updates `__init__.py` files in Python package directories found during the scan.

These files are typically saved in the scanned project's root or as specified by output arguments.

## Troubleshooting
*   **0 Files Scanned**: If the script reports 0 files scanned when you expect it to scan the whole project, ensure you are providing the correct `PROJECT_ROOT_TO_SCAN` argument (e.g., `D:/Dream.os`). The default might be pointing to a subdirectory like `runtime/config` based on your main `config.yaml`.
*   **Errors during parsing (e.g., AST parsing failed)**: These usually indicate issues with the syntax of specific source files being scanned. The scanner will typically log these and continue.
*   **Configuration Errors**: Ensure your main `config.yaml` (e.g., `D:/Dream.os/runtime/config/config.yaml`) is present and correctly structured, especially paths related to `PROJECT_ROOT` and `tree-sitter-grammars` if used.
