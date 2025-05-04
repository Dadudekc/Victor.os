# DreamOS Utility Scripts (`src/dreamos/tools/dreamos_utils/`)

This directory contains utility scripts for maintenance, analysis, or one-off tasks related to the DreamOS core components.

## Running Utility Scripts

**IMPORTANT:** Due to Python's import system and the project structure, scripts in this directory that need to import modules from the `dreamos` package (e.g., `from dreamos.config import ...`) **must** be run as modules from the **project root directory** (the directory containing the `src/` folder).

Do **not** run them directly using `python src/dreamos/tools/dreamos_utils/script_name.py`.

Instead, use the `python -m` flag:

```bash
# Example: Running standardize_task_list.py from the project root
python -m dreamos.tools.dreamos_utils.standardize_task_list --path runtime/task_list.json

# Example: Running pipeline_test_harness.py
python -m dreamos.tools.dreamos_utils.pipeline_test_harness --prompt "Test prompt here"
```

Running scripts this way ensures that Python correctly resolves the package imports (like `dreamos.utils.file_io`). Attempting to run them directly will likely result in `ModuleNotFoundError`.

---

## Individual Script Documentation

### `task_board_updater.py`

**Purpose:** Provides a command-line interface to safely update the status of a task for a specific agent on the main task board JSON file.

**Key Features:**
*   **Safe Updates:** Uses file locking (`filelock` library) to prevent race conditions when multiple agents or processes try to update the board simultaneously.
*   **Retries:** If the lock cannot be acquired immediately, the script will retry several times with exponential backoff.
*   **Corruption Handling:** Detects if the JSON file is empty or malformed. If detected, it backs up the corrupted file (to `runtime/logs/corrupt_board_backups/`) and resets the board structure before applying the update.
*   **Fallback:** If the primary JSON update fails persistently (lock timeout or other critical error), it attempts to append the status update to a separate YAML file (`runtime/manual_status_reports/agent_status.yaml`) as a fallback measure. This fallback also uses file locking.

**Usage:**

Run from the **project root directory** using `python -m`:

```bash
python -m dreamos.tools.dreamos_utils.task_board_updater \
    --agent <agent_id> \
    --task_id <task_id> \
    --status <NEW_STATUS> \
    [--details "Optional description"] \
    [--path /path/to/custom/task_board.json] \
    [--debug]
```

**Arguments:**
*   `--agent`: (Required) ID of the agent reporting the status (e.g., `Agent1`).
*   `--task_id`: (Required) ID of the task being updated.
*   `--status`: (Required) The new status string (e.g., `WORKING`, `COMPLETED`, `FAILED`, `PENDING_REVIEW`).
*   `--details`: (Optional) A string providing more context for the status update.
*   `--path`: (Optional) Override the default task board path (`runtime/task_board.json`).
*   `--debug`: (Optional) Enable verbose debug logging.

**Expected JSON Structure (`task_board.json`):
```json
{
  "agents": {
    "Agent1": {
      "tasks": {
        "task-abc-123": {
          "status": "WORKING",
          "last_updated": "2024-05-18T12:00:00.123Z",
          "description": "Processing data..."
        },
        // ... other tasks for Agent1
      }
    },
    "Agent2": {
      // ... tasks for Agent2
    }
    // ... other agents
  }
}
```

**Dependencies:**
*   `filelock` (`pip install filelock`)
*   `PyYAML` (`pip install PyYAML`)

### `standardize_task_list.py`

**Purpose:** Reads a task list JSON file, standardizes the format of each task object within it according to a predefined schema, and writes the standardized list back to the original file.

**Note:** This is likely intended as a one-time or infrequent utility to migrate older task list formats.

**Key Features:**
*   **Schema Enforcement:** Ensures all tasks conform to a standard set of fields (`task_id`, `task_type`, `name`, `description`, `status`, `priority`, timestamps, etc.).
*   **Value Mapping:** Converts different status strings (e.g., "claimed", "todo", "done") to standard uppercase values (e.g., `CLAIMED`, `PENDING`, `COMPLETED`). Converts priorities similarly (e.g., "low" to `Low`).
*   **ID Handling:** Prioritizes `task_id` field, falls back to `id`, and generates a temporary UUID if neither exists.
*   **Timestamp Handling:** Preserves existing timestamps or adds creation/update timestamps.
*   **Backup:** Creates a timestamped backup of the original file before overwriting.
*   **Atomic Write:** Uses an atomic write operation (via `dreamos.utils.file_io.write_json_atomic`) for safer file updates.
*   **Project Root Detection:** Automatically attempts to find the project root to ensure correct module imports.

**Usage:**

Run from the **project root directory** using `python -m`:

```bash
python -m dreamos.tools.dreamos_utils.standardize_task_list \
    [--path /path/to/target/task_list.json]
```

**Arguments:**
*   `--path`: (Optional) Path to the task list JSON file to standardize. If omitted, it attempts to load the path from `AppConfig` or defaults to `runtime/task_list.json`.

**Input:**
*   A JSON file containing a single list of task objects, potentially with varying field names and value formats.

**Output:**
*   Overwrites the input file with a JSON list where each task object conforms to the standard schema defined within the script.

**Dependencies:**
*   `dreamos.utils.file_io`
*   `dreamos.config`

### `pipeline_test_harness.py`

**Purpose:** Provides a command-line interface to test an end-to-end agent pipeline by sending an initial prompt and monitoring the `AgentBus` for expected success or failure events within a timeout period.

**Key Features:**
*   **Pipeline Trigger:** Initiates a test by publishing a `TASK_REQUEST_SENT` event containing the user-provided prompt and a unique `correlation_id`.
*   **Event Monitoring:** Listens to the `AgentBus` for subsequent events tagged with the same `correlation_id`.
*   **Configurable Outcomes:** Allows specifying the `EventType` name expected for success (default: `TASK_INJECTED_VIA_ROUTER`) and a list of `EventType` names that indicate pipeline failure (defaults listed in script).
*   **Timeout:** Sets a maximum duration to wait for a concluding event.
*   **Payload Validation:** Optionally checks if the payload of the success event contains a specific string.
*   **Result Reporting:** Prints PASS/FAIL/TIMEOUT status along with the final event received (if any).

**Usage:**

Run from the **project root directory** using `python -m`:

```bash
python -m dreamos.tools.dreamos_utils.pipeline_test_harness \
    -p "Your test prompt here" \
    [-t TIMEOUT_SECONDS] \
    [--success-event-type SUCCESS_EVENT_NAME] \
    [--failure-event-types FAILED_EVENT1 FAILED_EVENT2 ...] \
    [--expect-payload-contains "Expected string in success payload"]
```

**Arguments:**
*   `-p`, `--prompt`: (Required) The initial prompt text to trigger the pipeline.
*   `-t`, `--timeout`: (Optional) Maximum time in seconds to wait for a final event (default: 60).
*   `--success-event-type`: (Optional) The string name of the `EventType` enum member that signifies a successful pipeline completion (default: `TASK_INJECTED_VIA_ROUTER`).
*   `--failure-event-types`: (Optional) A space-separated list of `EventType` enum member names that signify a pipeline failure (defaults: `SCRAPER_ERROR`, `ROUTING_FAILED`, `PYAUTOGUI_ERROR`, `INJECTION_FAILED`).
*   `--expect-payload-contains`: (Optional) A string that must be present within the string representation of the success event's payload for the test to pass.

**Dependencies:**
*   `dreamos.core.coordination.agent_bus` (and its underlying requirements).

---

### `archive_agent_mailboxes.py`

**Purpose:** Archives old message files (`.msg`) from the top level of individual agent mailbox directories to keep them tidy.

**Operation:**
1.  Scans each subdirectory within `runtime/agent_comms/agent_mailboxes/` (e.g., `Agent1/`, `Agent2/`).
2.  Looks for files ending in `.msg` directly within these agent directories (e.g., `runtime/agent_comms/agent_mailboxes/Agent1/20240517_some_message.msg`).
3.  It **expects filenames to start with a date** in `YYYYMMDD` format.
4.  If a file's date prefix is **before the current date**, it is moved.
5.  An `archive/` subdirectory is created within the agent's mailbox if it doesn't exist.
6.  Dated subdirectories (`YYYY-MM-DD`) are created within the `archive/` directory.
7.  The old `.msg` file is moved into the corresponding `archive/YYYY-MM-DD/` directory.

**Example:**
*   Source: `runtime/agent_comms/agent_mailboxes/Agent1/20240517_some_message.msg`
*   Destination (if run on May 18th or later): `runtime/agent_comms/agent_mailboxes/Agent1/archive/2024-05-17/20240517_some_message.msg`

**Important:**
*   Only archives files directly inside the agent directory (e.g., `Agent1/`), not from subdirectories like `Agent1/inbox/`.
*   Requires the `YYYYMMDD` date prefix on filenames to function correctly.
*   Files from the current day are **not** archived.

**Usage:**

Run from the **project root directory**, preferably using `python -m` for consistency:

```bash
python -m dreamos.tools.dreamos_utils.archive_agent_mailboxes
```
*(Direct execution `python src/dreamos/tools/dreamos_utils/archive_agent_mailboxes.py` might also work as it lacks internal project imports, but `-m` is recommended.)*

**Dependencies:** None beyond standard Python libraries.

### `get_current_utc_iso.py`

**Purpose:** A simple utility to print the current Coordinated Universal Time (UTC) to standard output in the ISO 8601 format, including milliseconds.

**Output Format:** `YYYY-MM-DDTHH:MM:SS.sssZ` (e.g., `2024-05-18T14:30:00.123Z`)

**Usage:**

Can be run directly or via `python -m` from the project root:

```bash
# Using python -m (recommended for consistency)
python -m dreamos.tools.dreamos_utils.get_current_utc_iso

# Direct execution
python src/dreamos/tools/dreamos_utils/get_current_utc_iso.py
```

**Output:** Prints a single line containing the timestamp to standard output.

**Use Case:** Useful for obtaining a standardized timestamp in shell scripts or other processes within the Dream.OS environment.

**Dependencies:** None beyond standard Python libraries.

### `summarize_agent_comms.py`

**Purpose:** Scans a specified directory for agent communication message files (`.msg`), parses them as JSON, and prints a summary report to standard output.

**Operation:**
1.  Lists all `.msg` files in the target directory.
2.  Attempts to read each file and parse it as JSON.
3.  Expects JSON objects with keys: `sender_agent_id`, `recipient_agent_id`, `message_type`, `payload`, `timestamp_utc_iso`.
4.  Aggregates counts of total messages, processed messages, and messages by type.
5.  Optionally (with `-v`), lists the most recent messages grouped by `sender_agent_id` and `recipient_agent_id`.
6.  Reports any file reading or JSON parsing errors.
7.  Optionally (with `--archive`), moves successfully parsed `.msg` files to an `archive/` subdirectory within the target directory.

**Usage:**

Run from the **project root directory**, preferably using `python -m`:

```bash
python -m dreamos.tools.dreamos_utils.summarize_agent_comms \
    [TARGET_DIRECTORY] \
    [--archive] \
    [-v | --verbose]
```

**Arguments:**
*   `TARGET_DIRECTORY`: (Optional) Path to the directory containing `.msg` files. Defaults to `runtime/agent_comms` relative to the project root.
*   `--archive`: (Optional) If present, move successfully processed `.msg` files into an `archive/` subdirectory within the `TARGET_DIRECTORY`.
*   `-v`, `--verbose`: (Optional) Print detailed lists of recent messages grouped by sender and target.

**Input:**
*   A directory containing files ending in `.msg`, where each file is expected to contain a single JSON object with the standard message structure.

**Output:**
*   Prints a summary report to standard output.
*   Exits with status code 0 on success, 1 if errors were encountered.

**Dependencies:** None beyond standard Python libraries.

### `check_agent_pulse.py`

**Purpose:** Checks a YAML status file for recent heartbeat reports from expected agents to determine which agents are active, stale, or missing.

**Operation:**
1.  Reads agent status reports from a specified YAML file (default: `runtime/manual_status_reports/agent_status.yaml`).
2.  The YAML file is expected to contain a list of report objects, each with at least `agent_id` and `timestamp_utc_iso`.
3.  Compares the timestamp of the *last* report from each agent against the current UTC time.
4.  Agents whose last report is within a configured threshold (default: 15 minutes) are considered `active`.
5.  Agents whose last report is older than the threshold are considered `stale`.
6.  Agents defined in the `EXPECTED_AGENTS` set within the script that have no reports in the file are considered `missing`.
7.  Prints a summary report to standard output detailing active, stale, and missing agents, last seen timestamps, and any errors encountered (e.g., file not found, YAML parsing errors, invalid timestamps).
8.  Optionally imports `get_utc_iso_timestamp` from `dreamos.utils.core` if available, otherwise uses a fallback implementation (useful if run standalone).

**Usage:**

Run from the **project root directory**, preferably using `python -m`:

```bash
python -m dreamos.tools.dreamos_utils.check_agent_pulse
```

**Arguments:**
*   None. Configuration (status file path, stale threshold, expected agents) is currently hardcoded within the script.

**Output:**
*   Prints a status report to standard output.
*   **Exit Codes:**
    *   `0`: All expected agents are active.
    *   `1`: A fatal error occurred (e.g., file read error, YAML parse error).
    *   `2`: No fatal errors, but at least one expected agent is stale or missing.

**Dependencies:**
*   `PyYAML` (`pip install PyYAML`)
*   (Optional) `dreamos.utils.core` for the preferred timestamp function.

print("---------------------------------")
