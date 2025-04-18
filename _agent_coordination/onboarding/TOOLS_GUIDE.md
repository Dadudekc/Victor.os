# Dream.OS Tools Guide

This document provides guidance on the available tools within the `tools/` directory, intended for use by autonomous agents or developers.

## Usage Principles (For Agents)

- **Goal Alignment:** Select the tool that directly achieves your current task objective.
- **Input Precision:** Provide all required arguments accurately. Paths should typically be relative to the project root (`.`) unless the tool specifies otherwise.
- **Output Capture:** If a tool provides output data (e.g., JSON to stdout), ensure your execution mechanism captures it for parsing and use.
- **Idempotency Awareness:** Be aware that some tools are safe to run multiple times (e.g., scanners), while others might have side effects if run repeatedly with the same inputs (e.g., `code_applicator` in append mode).
- **Logging Interpretation:** Pay attention to status messages logged to stderr for progress and potential errors.
- **Exit Code Handling:** Always check the tool's exit code after execution. `0` typically indicates success, while non-zero codes indicate failure or specific conditions (refer to tool documentation).

---

## Agent Communication Tools

### 1. `tools/send_mailbox_message.py`

*   **Agent Goal:** To send a message directly to another agent's mailbox for processing.
*   **Purpose:** Creates a message file (`msg_<uuid>.json`) in the target agent's inbox directory (`<mailbox_root>/<recipient>/inbox/`).
*   **Arguments:**
    *   `--recipient <agent_name>`: (Required) The ID of the agent who should receive this message.
    *   `--payload-json "<json_string>"`: (Required) **You must construct this.** A valid JSON string representing the message payload (conforming to `messaging_format.md`). Example for shell: `--payload-json '{"command": "status_request", "details": "Provide current task ID."}'` (Note: Use single quotes around the whole JSON for shell compatibility, and standard double quotes inside the JSON).
    *   `--sender <agent_name>`: (Optional) Your agent ID. Defaults to `UnknownSender`.
    *   `--mailbox-root <path>`: (Optional) Specifies the root `mailboxes/` directory. If omitted, assumes `mailboxes/` is in the project root (`./mailboxes/`).
*   **Output (stdout/stderr):** Logs success/failure status messages.
*   **File Output:** Creates the `msg_<uuid>.json` file in the target inbox.
*   **Exit Codes:** `0` (Success: Message file created), `1` (Failure: e.g., invalid JSON, invalid recipient, write error).
*   **Agent Usage:** Use for direct agent-to-agent commands or notifications outside the main task list flow. Ensure the `--payload-json` string is valid JSON before calling.
*   **Example Call:** `python tools/send_mailbox_message.py --recipient SupervisorAgent --sender PlanningAgent --payload-json '{"event": "plan_generated", "task_id": "plan_xyz"}'`

---

## Code Generation & Manipulation Tools

### 2. `tools/code_applicator.py`

*   **Agent Goal:** To write or modify code in a specific file.
*   **Purpose:** Applies provided code content to a target file using various modes.
*   **Arguments:**
    *   `--target-file <path>`: (Required) The path (relative to project root) of the file to create or modify.
    *   Input Source (Exactly ONE Required):
        *   `--code-input <string>`: Provide the code directly as a string argument.
        *   `--code-file <path>`: Provide the path to a temporary file containing the code.
        *   `--code-stdin`: Provide the code via standard input (e.g., pipe from another process).
    *   `--mode {overwrite|replace_markers|append}`: (Optional) 
        *   `overwrite` (Default): Replaces the entire file content.
        *   `append`: Adds the code to the end of the file.
        *   `replace_markers`: Replaces content between specific start/end marker lines (ensure markers exist in the target file).
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
    *   `python tools/code_applicator.py --target-file src/new_module.py --code-file /tmp/generated_code.py --create-dirs --mode overwrite`
    *   `python tools/code_applicator.py --target-file src/existing_module.py --code-input "\nprint('Done')\n" --mode append`
    *   `echo "<replacement_code>" | python tools/code_applicator.py --target-file config.py --code-stdin --mode replace_markers --start-marker "# START_CONFIG" --end-marker "# END_CONFIG"`

---

## Project Analysis & Scanning Tools

### 3. `tools/project_scanner.py`

*   **Agent Goal:** To understand the structure of the project, find existing code, or get an overview of file contents.
*   **Purpose:** Scans a project directory, analyzes files (Python AST, basic info for others), identifies functions/classes/routes, and uses caching. Returns a summary of the project structure.
*   **Arguments:**
    *   `project_root`: (Required Positional) Path to the root directory to scan (usually `.`).
    *   `--ignore [<path_prefix> ...]`: (Optional) List of path prefixes to exclude (relative to `project_root`).
    *   `--cache-file <filename>`: (Optional) Name of the cache file (relative to `project_root`). Default: `project_scanner_cache.json`.
    *   `--workers <N>`: (Optional) Number of worker threads.
    *   `--output-json`: (Optional Flag) **Use this flag to get the analysis results.** Prints the analysis dictionary as JSON to **stdout**.
    *   `--save-analysis-file <filename>`: (Optional) Also save the analysis to a file in `project_root`. Default: `project_analysis.json`. Use `""` to disable file saving.
    *   `-v`, `--verbose`: (Optional Flag) Enable detailed logging to stderr.
*   **Output (stdout/stderr):** Logs progress/status to stderr. **If `--output-json` is used, the resulting analysis dictionary is printed to stdout.**
*   **Output Format (JSON):** A dictionary where keys are relative file paths and values are dictionaries containing analysis details (e.g., `language`, `functions`, `classes`, `complexity`, `size_bytes`).
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
      "README.md": {
        "language": ".md",
        "functions": [], "classes": {}, "routes": [],
        "complexity": 50, "is_text": true, "size_bytes": 3000
      }
      ...
    }
    ```
*   **File Output:** Updates the cache file. Optionally saves the full analysis JSON file.
*   **Exit Codes:** `0` (Success: Scan completed), `1` (Failure: e.g., invalid arguments, critical error).
*   **Agent Usage:** Crucial for situational awareness. Run with `--output-json`, capture stdout, and parse the JSON. Use this data to check if functions/classes already exist before generating code, or to get a list of files for further processing.
*   **Example Call (Agent Capture):** `python tools/project_scanner.py . --output-json`
*   **Example Call (Save to File):** `python tools/project_scanner.py . --ignore venv/ --save-analysis-file project_map.json`

### 4. `tools/proposal_security_scanner.py`

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

---

## Recovery & Diagnostics Tools (Simulated)

**IMPORTANT:** These tools currently contain **placeholder logic only**. They print messages indicating simulated actions but **do not perform real operations**. They are intended for testing agent workflows involving recovery or diagnostics.

### 5. `tools/check_confirmation_state.py`

*   **Agent Goal:** (Simulated) Check if a potentially sensitive action requires confirmation.
*   **Purpose:** Simulates this check.
*   **Arguments:** None.
*   **Output:** Prints message to stdout indicating simulated result.
*   **Exit Codes:** `0` (Simulates: Confirmation NOT required), `1` (Simulates: Confirmation REQUIRED).
*   **Agent Usage:** Test agent logic that handles confirmation requirements. **Do not rely on this for real confirmation.**
*   **Example Call:** `python tools/check_confirmation_state.py`

### 6. `tools/reload_agent_context.py`

*   **Agent Goal:** (Simulated) Reload an agent's internal context or memory.
*   **Purpose:** Simulates this action.
*   **Arguments:** `--target <agent_name>` (Required).
*   **Output:** Prints message to stdout indicating simulated success/failure.
*   **Exit Codes:** `0` (Simulates: Success), `1` (Simulates: Failure).
*   **Agent Usage:** Test agent logic for context reloading. **Does not actually reload context.**
*   **Example Call:** `python tools/reload_agent_context.py --target PlanningAgent`

### 7. `tools/diagnostics.py`

*   **Agent Goal:** (Simulated) Run diagnostic checks on the system.
*   **Purpose:** Simulates running checks.
*   **Arguments:** `--level {basic|full}` (Optional), `--auto` (Optional Flag).
*   **Output:** Prints simulated diagnostic steps/findings to stdout.
*   **Exit Codes:** `0` (Simulates: Checks passed), `1` (Simulates: Warnings found).
*   **Agent Usage:** Test agent logic for running diagnostics. **Does not perform real checks.**
*   **Example Call:** `python tools/diagnostics.py --auto`

### 8. `tools/project_context_producer.py`

*   **Agent Goal:** (Simulated) Generate a context summary from logs/files.
*   **Purpose:** Simulates context generation. Primarily intended for use as an imported Python module.
*   **Arguments (as script):** `conversation_log_snippet` (Positional), `project_directory` (Positional), `--output-dict` (Optional Flag).
*   **Output:** Writes simulated `agent_bridge_context.json` or prints dict if `--output-dict`.
*   **Agent Usage:** Can be imported by agents needing simulated context analysis. Running as a script is mainly for testing the placeholder. **Does not perform real analysis.**
*   **Example Call (as script):** `python tools/project_context_producer.py "Error occurred" . --output-dict`

---

*(TODO: Add documentation for any other tools, e.g., cursor_dispatcher.py if it becomes a general tool.)* 