# Tools Usage Guide

This guide provides an overview of all available tools in the `_agent_coordination/tools` directory, including their purpose and usage.

| Tool File | Description |
|-----------|-------------|
| context_planner.py | Consolidates keyword-matching logic into a single NLP-driven parser. |
| autonomy_swarm_reminder.txt | Reference document for reminding agents of autonomy protocols. |
| competition_protocol.txt | Details the Competitor Loop execution protocol for swarm competition. |
| broadcast_directive.py | Broadcasts directives to all agent mailboxes. |
| swarm_resume_directive.txt | Example directive for resuming the swarm. |
| supervisor_task_consolidator.py | Aggregates and deduplicates tasks from multiple agents. |
| set_project.py | CLI tool to switch the active project context for all agents. |
| parse_feedback_stats.py | Parses feedback logs and usage stats into structured format. |
| run_agent.py | Entrypoint script to launch individual agents with proper context. |
| code_applicator.py | Applies generated code diffs back into the codebase automatically. |
| reset_tasks.py | Clears and reinitializes the task list for a fresh run. |
| swarm_orchestrator.py | Orchestrates complex multi-agent workflows from directives. |
| compile_lore.py | Generates Devlog and lore documentation from task history. |
| monitor_console.py | Provides a console-based dashboard for real-time metrics. |
| demo_local_channel.py | Demonstration script for the LocalBlobChannel C2 transport. |
| find_potential_scripts.py | Searches codebase for candidate script files based on tasks. |
| run_qa.py | Tool for running QA checks and formatting on generated output. |
| log_analyzer.py | Analyzes log files to surface errors and performance metrics. |

For usage examples, see individual tool headers or run with `--help`.

# Dream.OS Tools Guide

This document provides guidance on the available tools within the `_agent_coordination/tools/` directory, intended for use by autonomous agents or developers.

## Usage Principles (For Agents)

- **Goal Alignment:** Select the tool that directly achieves your current task objective.
- **Input Precision:** Provide all required arguments accurately. Paths should typically be relative to the **determined project root** (as per onboarding) unless the tool specifies otherwise. Tools assuming Current Working Directory (CWD) expect it to be the project root.
- **Output Capture:** If a tool provides output data (e.g., JSON to stdout), ensure your execution mechanism captures it for parsing and use.
- **Idempotency Awareness:** Be aware that some tools are safe to run multiple times (e.g., scanners), while others might have side effects if run repeatedly with the same inputs (e.g., `code_applicator` in append mode).
- **Logging Interpretation:** Pay attention to status messages logged to stderr for progress and potential errors.
- **Exit Code Handling:** Always check the tool's exit code after execution. `0` typically indicates success, while non-zero codes indicate failure or specific conditions (refer to tool documentation).

---

## Code Generation & Manipulation Tools

### 1. `code_applicator.py`

*   **Agent Goal:** To write or modify code in a specific file.
*   **Purpose:** Applies provided code content to a target file using various modes. Handles paths relative to the project root.
*   **Arguments:**
    *   `--target-file <path>`: (Required) The path (relative to project root) of the file to create or modify.
    *   Input Source (Exactly ONE Required):
        *   `--code-input <string>`: Provide the code directly as a string argument.
        *   `--code-file <path>`: Provide the path (relative to project root) to a file containing the code.
        *   `--code-stdin`: Provide the code via standard input (e.g., pipe from another process).
    *   `--mode {overwrite|replace_markers|append}`: (Optional)
        *   `overwrite` (Default): Replaces the entire file content (atomic write).
        *   `append`: Adds the code to the end of the file.
        *   `replace_markers`: Replaces content between specific start/end marker lines (atomic write; markers must exist). Default markers: `# CODE_APPLICATOR_START`, `# CODE_APPLICATOR_END`.
    *   `--create-dirs`: (Optional Flag) If the target file's directory doesn't exist, create it.
    *   `--backup`: (Optional Flag) Create a `.bak` copy of the original file before changes.
    *   `--start-marker <string>`: (Optional) Custom start marker for `replace_markers` mode.
    *   `--end-marker <string>`: (Optional) Custom end marker for `replace_markers` mode.
    *   `-v`, `--verbose`: (Optional Flag) Enable more detailed logging.
*   **Output (stdout/stderr):** Logs actions (e.g., "Overwrote file", "Appended to file") and errors.
*   **File Output:** Creates or modifies the file specified by `--target-file`.
*   **Exit Codes:** `0` (Success: Code applied), `1` (Failure: e.g., invalid arguments, file errors, marker errors).
*   **Agent Usage:** Primary tool for implementing code changes. Select the appropriate input source and mode based on the task.
*   **Example Calls:**
    *   `python tools/code_applicator.py --target-file src/new_module.py --code-file tmp/generated_code.py --create-dirs --mode overwrite`
    *   `python tools/code_applicator.py --target-file src/existing_module.py --code-input "\nprint('Done')\n" --mode append`
    *   `echo "<replacement_code>" | python tools/code_applicator.py --target-file config.py --code-stdin --mode replace_markers --start-marker "# START_CONFIG" --end-marker "# END_CONFIG"`

---

## Project Analysis & Planning Tools

### 2. `project_scanner.py`

*   **Agent Goal:** To understand the structure of the project, find existing code, or get an overview of file contents.
*   **Purpose:** Scans a project directory (from project root), analyzes files (Python AST, basic info for others), identifies functions/classes/routes, and uses caching based on file hashes. Returns a summary of the project structure. Uses multi-threading.
*   **Arguments (passed to `perform_scan` function, likely used internally):**
    *   `project_root`: (Required) Path to the root directory to scan (usually `.`).
    *   `additional_ignore_patterns`: (Optional) List of path prefixes/globs to exclude.
    *   `cache_file_name`: (Optional) Name of the cache file (relative to `project_root`). Default: `project_scanner_cache.json`.
    *   `num_workers`: (Optional) Number of worker threads.
*   **Output (stdout/stderr):** Logs progress/status to stderr. **No primary output to stdout unless explicitly designed for interaction (check source if needed).** The main result is the returned analysis dictionary and the updated cache file.
*   **Output Format (Returned Dict / Saved File):** A dictionary where keys are relative file paths and values are dictionaries containing analysis details (e.g., `language`, `functions`, `classes`, `complexity`, `size_bytes`).
    ```json
    {
      "src/main.py": {
        "language": ".py",
        "functions": [{"name": "run", "args": [], "lineno": 10, ...}],
        "classes": { ... },
        "routes": [],
        "complexity": 5,
        "size_bytes": 200
      },
      "README.md": {"language": ".md", ... }
      // ...
    }
    ```
*   **File Output:** Updates the cache file (`project_scanner_cache.json` by default).
*   **Agent Usage:** Primarily intended to be used as an imported Python module by agents needing project structure awareness. An agent would call `perform_scan()` to get the analysis dictionary. Crucial for situational awareness, checking for existing code, etc.
*   **Example Usage (Python):**
    ```python
    from tools.project_scanner import perform_scan
    analysis = perform_scan(project_root='.')
    if 'src/utils.py' in analysis:
        print("Found utils.py")
    ```

### 3. `context_planner.py`

*   **Agent Goal:** To determine what information (files, code definitions, usages) is needed to complete a complex task described in natural language.
*   **Purpose:** Analyzes a task description (e.g., "Refactor `old_func` in `main.py` to use `NewClass` from `utils.py`") and generates a structured plan of actions using other tools (like `grep_search`, `read_file`, `codebase_search`) to gather the required context before attempting the main task.
*   **Arguments (as Python function `generate_context_plan_v3`):**
    *   `task_description`: (Required `str`) The natural language description of the task.
*   **Output (Return Value):** A list of dictionaries, where each dictionary represents a step in the context-gathering plan. Each step includes:
    *   `description`: Human-readable explanation of the step.
    *   `action`: The tool/API action to perform (e.g., `grep_search`, `read_file`).
    *   `target`: The primary target for the action (e.g., symbol name, file path).
    *   `params`: A dictionary of parameters for the action (e.g., `{"query": "...", "case_sensitive": false}`).
    *   `store_as`: (Optional) An identifier to store the result of this step for potential use in later steps (e.g., using a found file path in a subsequent `read_file`).
*   **Agent Usage:** Intended to be imported and used by higher-level planning agents. Call `generate_context_plan_v3(task_description)` to get the context plan. Execute the steps in the plan using the appropriate tool calls (or internal API calls) to gather information before proceeding with the main task logic (like code generation).
*   **Example Usage (Python):**
    ```python
    from tools.context_planner import generate_context_plan_v3
    task = "Fix the `calculate_total` function in `billing.py` using the `get_rate` function from `rates.py`"
    plan = generate_context_plan_v3(task)
    # Agent would then iterate through 'plan' and execute each step
    # e.g., if plan[0]['action'] == 'read_file', call read_file(target=plan[0]['target'])
    ```

### 4. `project_context_producer.py`

*   **Agent Goal:** To get a very basic overview of potentially relevant files based on recent logs or the project structure.
*   **Purpose:** Extracts potential file paths mentioned in a log snippet using regex and lists all Python files in the project directory. Outputs this information.
*   **Arguments (as script):**
    *   `conversation_log_snippet`: (Required Positional) Snippet of conversation log. Can be 'stdin' to read from stdin.
    *   `project_directory`: (Required Positional) Path to the project root directory.
    *   `--output-dict`: (Optional Flag) Print the context dictionary to stdout instead of writing a file.
    *   `-v`, `--verbose`: (Optional Flag) Enable detailed logging.
*   **Output (stdout/stderr):** Logs progress to stderr. If `--output-dict` is used, prints the context JSON to stdout.
*   **File Output:** By default, writes the context to `agent_bridge_context.json` in the project root. Contains log length, project root path, paths mentioned in the log snippet, and a list of all Python files found.
*   **Exit Codes:** `0` (Success), `1` (Failure: e.g., project dir not found, write error).
*   **Agent Usage:** Can provide a quick, basic list of mentioned files or all Python files. May be less sophisticated than `project_scanner` or `context_planner` for deeper analysis.
*   **Example Call:** `python tools/project_context_producer.py "Error in main.py line 50" . --output-dict`

---

## Security & State Management Tools

### 5. `proposal_security_scanner.py`

*   **Agent Goal:** To check a file containing proposed changes for potentially risky operations before they are approved or executed.
*   **Purpose:** Scans a text file (e.g., Markdown containing agent proposals) for keywords/patterns defined in `RISKY_KEYWORDS` (e.g., `os.remove`, `eval(`).
*   **Arguments:**
    *   `proposals_file`: (Required Positional) Path to the text/markdown file containing proposals.
    *   `--log-file <path>`: (Optional) Path where findings should be logged. Default: `security_scan.log` in the same directory as `proposals_file`.
    *   `-v`, `--verbose`: (Optional Flag) Enable detailed logging to stderr.
*   **Output (stdout/stderr):** Logs a summary of the scan (number of proposals checked, number of findings) to stderr.
*   **File Output:** Appends detailed findings (including context snippets) to the specified log file.
*   **Exit Codes:** `0` (Success: Scan completed, *regardless* of whether findings were logged), `1` (Failure: e.g., cannot read input file, cannot write to log file).
*   **Agent Usage:** Intended for Supervisor or Security agents. Run this tool on proposal files. Check the log file afterwards for any logged findings. An exit code of `0` only means the scan ran, not that the proposals are safe.
*   **Example Call:** `python tools/proposal_security_scanner.py _agent_coordination/onboarding/rulebook_update_proposals.md --log-file logs/security.log -v`

### 6. `check_confirmation_state.py`

*   **Agent Goal:** Check if a potentially sensitive action requires explicit user confirmation before proceeding.
*   **Purpose:** Checks for the existence of a specific flag file in the Current Working Directory (CWD), which is assumed to be the project root.
*   **Arguments:**
    *   `--flag-file <filename>`: (Optional) Name of the flag file to check for. Default: `CONFIRMATION_REQUIRED.flag`.
    *   `-v`, `--verbose`: (Optional Flag) Enable detailed logging.
*   **Output (stdout/stderr):** Logs whether the flag file was found.
*   **File Output:** None.
*   **Exit Codes:** `0` (Confirmation NOT required: Flag file not found), `1` (Confirmation REQUIRED: Flag file found).
*   **Agent Usage:** Use before performing potentially sensitive operations (defined by system policy). Check the exit code to determine if confirmation is needed.
*   **Example Call:** `python tools/check_confirmation_state.py`

### 7. `reload_agent_context.py` (Simulated)

*   **Agent Goal:** (Simulated) Reload an agent's internal context or memory.
*   **Purpose:** **Placeholder only.** Simulates sending a context reload signal. Does not perform any real action.
*   **Arguments:** `--target <agent_name>` (Required).
*   **Output (stdout/stderr):** Prints message to stderr indicating simulated success.
*   **File Output:** None.
*   **Exit Codes:** `0` (Simulated Success).
*   **Agent Usage:** For testing agent workflows that might involve context reloading. **Do not rely on this for actual context management.**
*   **Example Call:** `python tools/reload_agent_context.py --target PlanningAgent`

---

## Diagnostics Tools

### 8. `diagnostics.py`

*   **Agent Goal:** To verify the basic structure and integrity of the agent coordination environment.
*   **Purpose:** Performs checks on the existence and type (directory/file) of key paths (`_agent_coordination`, `tools`, `protocols`, `mailboxes`) and optionally validates JSON files and checks for essential protocol documents. Assumes CWD is project root.
*   **Arguments:**
    *   `--level {basic|full}`: (Optional) `basic` checks core directories. `full` performs all checks including JSON validation and essential protocol file presence. Default: `basic`.
    *   `--auto`: (Optional Flag) Currently only affects logging detail.
    *   `-v`, `--verbose`: (Optional Flag) Enable detailed logging.
*   **Output (stdout/stderr):** Logs the results of each check (PASSED/FAILED/SKIPPED) and a final summary to stderr.
*   **File Output:** None.
*   **Exit Codes:** `0` (Success: All checks for the specified level passed), `1` (Failure: One or more checks failed for the specified level).
*   **Agent Usage:** Can be run during agent initialization or troubleshooting to verify the environment structure. Check the exit code to determine if critical components are missing or invalid.
*   **Example Call:** `python tools/diagnostics.py --level full`

---

*(Ensure this guide is kept up-to-date as tools are added, removed, or modified.)* 