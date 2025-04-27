"""
Command-Line Interface (CLI) tool to inject tasks into the Dream.OS task list.

Usage:
  python scripts/inject_task.py --action RUN_TERMINAL_COMMAND --params '{"command": "echo Hello from CLI"}'
  python scripts/inject_task.py --action GET_EDITOR_CONTENT --priority 1
  python scripts/inject_task.py --action OPEN_FILE --params '{"file_path": "/path/to/your/file.txt"}' --task-id custom_open_task
"""

import argparse
import json
import os
import sys
import uuid
import time
from datetime import datetime
import traceback
from pathlib import Path

# Assuming TaskStatus might be defined elsewhere, but for standalone use:
class TaskStatus:
    PENDING = "PENDING"

# Define the path to the input file relative to the project root
# Assumes this script is run from project root or `scripts/` dir
try:
    # Find project root (assuming script is in project_root/scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    # Fallback to current working directory if not at repository root (no .git folder)
    if not os.path.exists(os.path.join(project_root, ".git")):
        project_root = os.getcwd()
except NameError:
     # __file__ not defined (e.g., interactive) - assume CWD is project root
     project_root = os.getcwd()

# EDIT START: load JSON schema for task validation
# Compute schema path relative to repository root using project_root
SCHEMA_PATH = Path(project_root) / "src" / "dreamos" / "utils" / "task_schema.json"
TASK_SCHEMA = None
try:
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        TASK_SCHEMA = json.load(f)
except Exception as e:
    print(f"Warning: Could not load task schema from {SCHEMA_PATH}: {e}", file=sys.stderr)
# Import jsonschema validate and ValidationError for schema-based checks
try:
    from jsonschema import validate as _validate, ValidationError as _SchemaValidationError
except ImportError:
    _validate = None
    _SchemaValidationError = Exception
# EDIT END

DEFAULT_INPUT_FILE = os.path.join(project_root, "run", "input_tasks.jsonl")

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Inject one or more tasks into the Dream.OS task list."
    )
    # mutually exclusive modes: single task vs batch
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--action", help="Action for a single task (e.g. RUN_TERMINAL_COMMAND)."
    )
    group.add_argument(
        "--batch-file", type=str,
        help="Path to JSON or JSONL file with multiple tasks to inject."
    )
    parser.add_argument(
        "--params", type=str, default="{}",
        help="JSON string of parameters for single action mode."
    )
    parser.add_argument(
        "--task-id", type=str, default=None,
        help="Specific ID for single task (optional)."
    )
    parser.add_argument(
        "--priority", type=int, default=50,
        help="Priority for single task (lower is higher priority)."
    )
    parser.add_argument(
        "--target-agent", type=str, default=None,
        help="Target agent ID for single task."
    )
    parser.add_argument(
        "--depends-on", type=str, default="",
        help="Comma-separated task IDs this single task depends on."
    )
    parser.add_argument(
        "--input-file", type=str, default=DEFAULT_INPUT_FILE,
        help=f"Output task file (default: {DEFAULT_INPUT_FILE})."
    )
    # Metadata enrichment and retry
    parser.add_argument(
        "--platform", type=str,
        help="Platform name metadata for single or batch mode."
    )
    parser.add_argument(
        "--audience", type=str,
        help="Audience metadata for single or batch mode."
    )
    parser.add_argument(
        "--schedule-time", type=str,
        help="Scheduled time (ISO) metadata for single or batch mode."
    )
    parser.add_argument(
        "--retries", type=int, default=3,
        help="Number of file-write retries on failure."
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="In batch mode, abort on first invalid entry instead of skipping."
    )
    return parser.parse_args()

def validate_task_entry(task_data: dict) -> bool:
    """
    Validates required fields for a task entry using JSON schema.
    Returns True if valid, prints errors and returns False otherwise.
    """
    # EDIT START: schema-based validation using jsonschema if available
    if TASK_SCHEMA and _validate:
        try:
            _validate(instance=task_data, schema=TASK_SCHEMA)
            return True
        except _SchemaValidationError as e:
            print(f"Invalid task entry: {e.message}", file=sys.stderr)
            return False
    # fallback: basic checks
    missing_fields = []
    if 'action' not in task_data or not isinstance(task_data['action'], str) or not task_data['action'].strip():
        missing_fields.append('action')
    if 'params' not in task_data or not isinstance(task_data['params'], dict):
        missing_fields.append('params')
    if missing_fields:
        print(f"Invalid task entry, missing or invalid fields: {missing_fields}", file=sys.stderr)
        return False
    return True

def main():
    args = parse_arguments()

    # Validate and parse JSON params
    try:
        params_dict = json.loads(args.params)
        if not isinstance(params_dict, dict):
            raise ValueError("Params must be a JSON object (dictionary).")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON string provided for --params: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate task ID if not provided
    task_id = args.task_id or f"cli_injected_{uuid.uuid4().hex[:8]}"

    # Parse dependencies
    dependencies = [dep.strip() for dep in args.depends_on.split(',') if dep.strip()]

    # Construct the task object with metadata enrichment
    task = {
        "task_id": task_id,
        "action": args.action,
        "params": params_dict,
        "status": TaskStatus.PENDING,
        "priority": args.priority,
        "depends_on": dependencies,
        "retry_count": 0,
        "repair_attempts": 0,
        "injected_at": datetime.now().isoformat(),
        "injected_by": "cli_tool"
    }
    # Add optional metadata fields
    metadata = {}
    if args.platform:
        metadata['platform'] = args.platform
    if args.audience:
        metadata['audience'] = args.audience
    if args.schedule_time:
        metadata['scheduled_time'] = args.schedule_time
    if metadata:
        task['metadata'] = metadata

    if args.target_agent:
        task["target_agent"] = args.target_agent
    # Optional: Add default target_agent logic based on action here if desired
    # elif args.action in ["RUN_TERMINAL_COMMAND", ...]: task["target_agent"] = "CursorControlAgent"

    # Ensure the run directory exists
    input_file_dir = os.path.dirname(args.input_file)
    try:
        os.makedirs(input_file_dir, exist_ok=True)
    except OSError as e:
        print(f"Error: Could not create directory {input_file_dir}: {e}", file=sys.stderr)
        sys.exit(1)

    # Helper to write tasks with retry logic
    def write_task_line(line: str) -> bool:
        for attempt in range(1, args.retries + 1):
            try:
                with open(args.input_file, 'a', encoding='utf-8') as f:
                    f.write(line + '\n')
                return True
            except Exception as write_err:
                if attempt < args.retries:
                    time.sleep(0.5 * attempt)
                    continue
                print(f"Error: Failed to write after {args.retries} attempts: {write_err}", file=sys.stderr)
                return False

    # Batch injection path
    if args.batch_file:
        try:
            raw = Path(args.batch_file).read_text(encoding='utf-8')
            entries = json.loads(raw) if raw.lstrip().startswith('[') else [json.loads(l) for l in raw.splitlines() if l.strip()]
        except Exception as e:
            print(f"Error loading batch file {args.batch_file}: {e}", file=sys.stderr)
            sys.exit(1)
        # Non-blocking validation: inject valid entries, skip invalid
        accepted = 0
        skipped = 0
        error_positions = []
        for idx, t in enumerate(entries, start=1):
            if not validate_task_entry(t):
                error_positions.append(idx)
                if args.strict:
                    print(f"Error: invalid entry at position {idx}, aborting due to strict mode.", file=sys.stderr)
                    sys.exit(1)
                skipped += 1
                continue
            # Valid entry: enrich metadata and write
            if args.platform:
                t.setdefault('metadata', {})['platform'] = args.platform
            if args.audience:
                t.setdefault('metadata', {})['audience'] = args.audience
            if args.schedule_time:
                t.setdefault('metadata', {})['scheduled_time'] = args.schedule_time
            line = json.dumps(t)
            if write_task_line(line):
                accepted += 1
            else:
                skipped += 1
        # Summary
        print(f"Batch injection complete: {accepted} injected, {skipped} skipped.")
        if error_positions:
            print(f"Skipped invalid entries at positions: {error_positions}", file=sys.stderr)
        sys.exit(0)

    # Single task injection
    # Validate single task
    if not validate_task_entry(task):
        sys.exit(1)
    task_json_line = json.dumps(task)
    if write_task_line(task_json_line):
        print(f"Successfully injected task '{task_id}' into {args.input_file}")
        print(f"Task details: {task_json_line}")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main() 
