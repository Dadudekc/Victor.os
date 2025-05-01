# scripts/maintenance/migrate_future_tasks_to_split.py

import json
from pathlib import Path

# Paths
BOARD_DIR = Path("runtime/agent_comms/project_boards")
FUTURE_TASKS = BOARD_DIR / "future_tasks.json"
READY_QUEUE = BOARD_DIR / "task_ready_queue.json"
BACKLOG = BOARD_DIR / "task_backlog.json"
ARCHIVE = BOARD_DIR / "future_tasks_migrated_ARCHIVE.json"


# Ensure output files exist
def ensure_file(path: Path):
    BOARD_DIR.mkdir(parents=True, exist_ok=True)  # Ensure parent dir exists
    if not path.exists():
        print(f"Initializing empty file: {path}")
        path.write_text("[]", encoding="utf-8")
    else:
        print(f"File already exists: {path}")


print("Ensuring output files exist...")
ensure_file(READY_QUEUE)
ensure_file(BACKLOG)

# Load source
print(f"Loading source file: {FUTURE_TASKS}")
if not FUTURE_TASKS.exists():
    print("ERROR: future_tasks.json not found. Migration cannot proceed.")
    exit(1)

try:
    with open(FUTURE_TASKS, "r", encoding="utf-8") as f:
        tasks = json.load(f)
except json.JSONDecodeError as e:
    print(
        f"ERROR: future_tasks.json contains invalid JSON: {e}. Migration cannot proceed."
    )
    exit(1)
except Exception as e:
    print(f"ERROR: Failed to read future_tasks.json: {e}. Migration cannot proceed.")
    exit(1)

if not isinstance(tasks, list):
    print(
        "ERROR: future_tasks.json does not contain a valid JSON list. Migration cannot proceed."
    )
    exit(1)

# Initialize pools
ready = []
backlog = []

print("Starting migration logic...")
# Migration logic
for task in tasks:
    if not isinstance(task, dict):
        print(f"WARNING: Skipping invalid task entry (not a dict): {task}")
        backlog.append(task)  # Put invalid entries in backlog for review
        continue

    status = task.get("status", "").upper()
    assigned = task.get("assigned_agent")
    task_id = task.get("task_id")
    description = task.get("description")

    # Basic validity check (must have an ID)
    if not task_id:
        print(f"WARNING: Skipping task with missing task_id: {task}")
        backlog.append(task)
        continue

    # Eligible for ready queue: PENDING status and not currently assigned
    if status == "PENDING" and not assigned:
        print(f"  -> Moving {task_id} to Ready Queue")
        ready.append(task)
    else:
        # All others go to backlog (CLAIMED, WORKING, BLOCKED, COMPLETED*, non-PENDING, assigned PENDING, etc.)
        print(
            f"  -> Moving {task_id} to Backlog (Status: {status}, Assigned: {assigned})"
        )
        backlog.append(task)

# Confirm results
print(f"\nMigration complete. Tasks analyzed: {len(tasks)}")
print(f"  -> Ready Queue: {len(ready)} tasks")
print(f"  -> Backlog: {len(backlog)} tasks")

# Write outputs atomically - Using Python's write for simplicity here.
# Replace with safe_writer_cli call if strict atomicity/locking is needed now.
try:
    print(f"Writing {len(ready)} tasks to {READY_QUEUE}")
    READY_QUEUE.write_text(json.dumps(ready, indent=2), encoding="utf-8")
    print(f"Writing {len(backlog)} tasks to {BACKLOG}")
    BACKLOG.write_text(json.dumps(backlog, indent=2), encoding="utf-8")
except Exception as e:
    print(f"ERROR: Failed to write output files: {e}. Original file not archived.")
    exit(1)

# Archive original
try:
    print(f"Archiving original {FUTURE_TASKS} to {ARCHIVE}")
    FUTURE_TASKS.rename(ARCHIVE)
    print(f"Migration successful. Original archived.")
except Exception as e:
    print(
        f"ERROR: Failed to archive original file {FUTURE_TASKS}: {e}. Manual cleanup needed."
    )
    exit(1)
