import argparse
import datetime
import json
import logging
import shutil
import sys
from pathlib import Path

# --- Configuration ---
# These could be made configurable via args or a separate config file
DEFAULT_BACKUP_DIR = "runtime/task_migration_backups"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"

# --- Logger Setup ---
logger = logging.getLogger("TaskFlowMigration")


def setup_logging(log_level_str: str = "INFO", log_file: Path | None = None):
    """Configures logging for the script."""
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logger.setLevel(log_level)

    formatter = logging.Formatter(LOG_FORMAT)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if log_file:
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        logger.info(f"Logging to file: {log_file}")


# --- Core Migration Functions (Placeholders) ---


def create_backup(source_files: list[Path], backup_base_dir: Path) -> Path | None:
    """Creates timestamped backups of source files. Returns backup directory path or None on failure."""
    logger.info(f"Attempting to back up files: {', '.join(map(str, source_files))}")
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = backup_base_dir / f"backup_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        for src_file in source_files:
            if src_file.exists():
                shutil.copy2(src_file, backup_dir / src_file.name)
                logger.info(f"Backed up {src_file} to {backup_dir / src_file.name}")
            else:
                logger.warning(
                    f"Source file {src_file} not found for backup. Skipping."
                )
        logger.info(f"Backup completed in directory: {backup_dir}")
        return backup_dir
    except Exception as e:
        logger.error(f"Backup failed: {e}", exc_info=True)
        return None


def read_jsonl_file(file_path: Path) -> list[dict]:
    """Reads a JSONL file and returns a list of dictionaries. Handles errors."""
    tasks = []
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}. Returning empty list.")
        return tasks
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    if line.strip():
                        tasks.append(json.loads(line.strip()))
                except json.JSONDecodeError as e:
                    logger.error(
                        f"JSON decode error in {file_path} at line {line_num}: {e}. Skipping line: '{line.strip()}'"
                    )
        logger.info(f"Successfully read {len(tasks)} tasks from {file_path}")
        return tasks
    except Exception as e:
        logger.error(f"Failed to read or parse {file_path}: {e}", exc_info=True)
        return []  # Return empty list on major read error


def transform_task(task_data: dict, source_file_type: str) -> dict | None:
    """
    Transforms a task from an old format to the new task_board.json format.
    Uses src/dreamos/coordination/tasks/task-schema.json as the target.
    """
    task_id = task_data.get("task_id")
    if not task_id:
        logger.warning(f"Task missing 'task_id', cannot be migrated: {task_data}")
        return None

    logger.debug(f"Transforming task {task_id} from {source_file_type}")

    # Initialize with defaults from new schema, then selectively override/map
    new_task = {
        "task_id": task_id,
        "action": task_data.get(
            "task_type", task_data.get("name", "migrated_task")
        ),  # Best effort for action
        "params": {
            # Store original name and description if not directly mapped elsewhere
            "original_name": task_data.get("name"),
            "original_description": task_data.get("description"),
            "original_tags": task_data.get("tags"),
            "original_estimated_duration": task_data.get("estimated_duration"),
            "original_task_type": task_data.get("task_type"),
        },
        "status": "PENDING",  # Default, will be overridden by mapping
        "priority": task_data.get(
            "priority"
        ),  # Assuming priority types are compatible or will be parsed
        "depends_on": task_data.get("dependencies", []),
        "retry_count": 0,
        "repair_attempts": 0,
        "failure_count": 0,  # Legacy?
        "injected_at": task_data.get(
            "created_at", datetime.datetime.now(datetime.timezone.utc).isoformat()
        ),
        "injected_by": task_data.get("created_by", "TaskMigrationScript"),
        "started_at": None,
        "completed_at": None,
        "result_status": None,
        "result_data": None,
        "error_message": None,
        "progress": None,
        "scoring": None,
        # Attempt to carry over history if it exists in the old task
        "history": task_data.get("history", []),  # Start with old history
    }

    # Priority conversion (string to int if needed, simple example)
    if isinstance(new_task["priority"], str):
        p_map = {"CRITICAL": 1, "HIGH": 5, "MEDIUM": 10, "LOW": 20, "CHORE": 30}
        new_task["priority"] = p_map.get(new_task["priority"].upper(), 10)
    elif not isinstance(new_task["priority"], int):
        new_task["priority"] = 10  # Default if unmappable

    # Status mapping
    old_status = str(task_data.get("status", "")).upper()
    # Assuming target statuses: PENDING, ACTIVE, COMPLETED, FAILED, PAUSED, DEFERRED
    if old_status in ["DONE", "COMPLETED"]:
        new_task["status"] = "COMPLETED"
        # Try to get a completion timestamp from history, fallback to injected_at
        completion_ts = new_task["injected_at"]
        if isinstance(task_data.get("history"), list):
            for entry in reversed(task_data["history"]):
                if str(entry.get("action", "")).upper() in ["COMPLETED", "DONE"]:
                    completion_ts = entry.get("timestamp", completion_ts)
                    break
        new_task["completed_at"] = completion_ts
        new_task["result_status"] = "SUCCESS"
        new_task["progress"] = 1.0
    elif old_status == "IN_PROGRESS":
        new_task["status"] = "ACTIVE"  # Or PENDING if board requires explicit claim
        # Try to get a start timestamp from history, fallback to injected_at
        start_ts = new_task["injected_at"]
        if isinstance(task_data.get("history"), list):
            for entry in task_data["history"]:
                if str(entry.get("action", "")).upper() == "CLAIMED":
                    start_ts = entry.get("timestamp", start_ts)
                    break  # First claim is likely start
        new_task["started_at"] = start_ts
    elif old_status == "PAUSED":
        new_task["status"] = "PAUSED"  # Assuming new schema supports PAUSED
    elif old_status == "DEFERRED":
        new_task["status"] = "DEFERRED"  # Assuming new schema supports DEFERRED
    elif old_status == "PENDING":
        new_task["status"] = "PENDING"
    # else, it remains PENDING from initialization

    # Add migration history entry (ensure history is a list)
    if not isinstance(new_task["history"], list):
        new_task["history"] = []
    new_task["history"].append(
        {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "agent": "TaskMigrationScript",
            "action": f"MIGRATED_FROM_{source_file_type}",
            "details": f"Original status: {old_status}. Original task_id: {task_id}",
        }
    )

    # Store other original fields in params, maybe under a sub-key
    new_task["params"]["_migration_info"] = {
        "original_name": task_data.get("name"),
        "original_description": task_data.get("description"),
        "original_tags": task_data.get("tags"),
        "original_estimated_duration": task_data.get("estimated_duration"),
        "original_task_type": task_data.get("task_type"),
        "original_notes": task_data.get("notes"),
        "original_assigned_agent": task_data.get("assigned_agent")
        or task_data.get("assigned_to"),
        "original_parent_task_id": task_data.get("parent_task_id"),
        # Avoid storing raw task or full history here if history is carried over top-level
    }
    # Clean up None values from the sub-dictionary for tidiness
    new_task["params"]["_migration_info"] = {
        k: v for k, v in new_task["params"]["_migration_info"].items() if v is not None
    }

    # Validate required fields from schema
    required_fields = [
        "task_id",
        "action",
        "status",
        "priority",
        "injected_at",
        "injected_by",
    ]
    is_valid = True
    for req_field in required_fields:
        if req_field not in new_task or new_task[req_field] is None:
            # Try to set a default if possible
            if req_field == "action" and not new_task.get("action"):
                new_task["action"] = "default_migrated_action"
                logger.warning(
                    f"Task {task_id} missing 'action', defaulted to '{new_task['action']}'."
                )
            elif req_field == "injected_by" and not new_task.get("injected_by"):
                new_task["injected_by"] = "TaskMigrationScript"
                logger.warning(
                    f"Task {task_id} missing 'injected_by', defaulted to '{new_task['injected_by']}'."
                )
            # Add other potential default logic here if needed

            # Re-check after attempting defaults
            if req_field not in new_task or new_task[req_field] is None:
                logger.error(
                    f"Task {task_id} missing required field '{req_field}' after transformation and defaulting attempts. Cannot migrate."
                )
                is_valid = False
                break  # Stop checking this task

    if not is_valid:
        return None

    return new_task


def merge_into_task_board(
    task_board_path: Path, new_tasks: list[dict], dry_run: bool = False
) -> tuple[int, int]:
    """
    Merges new tasks into task_board.json.
    Handles existing tasks based on task_id (currently skips duplicates).
    Returns (tasks_added, tasks_skipped_duplicates).
    """
    tasks_added = 0
    tasks_skipped_duplicates = 0

    existing_tasks = []
    if task_board_path.exists():
        existing_tasks = read_jsonl_file(
            task_board_path
        )  # Assuming task_board is also jsonl for consistency
        # If task_board is a single JSON array, this needs to change:
        # with open(task_board_path, 'r') as f: existing_tasks = json.load(f)

    existing_task_ids = {t.get("task_id") for t in existing_tasks if t.get("task_id")}

    final_task_list = existing_tasks[:]  # Make a copy

    for task in new_tasks:
        task_id = task.get("task_id")
        if not task_id:
            logger.warning(f"Skipping task due to missing task_id: {task}")
            continue

        if task_id in existing_task_ids:
            logger.info(
                f"Task ID {task_id} already exists in {task_board_path}. Skipping duplicate."
            )
            tasks_skipped_duplicates += 1
        else:
            final_task_list.append(task)
            existing_task_ids.add(
                task_id
            )  # Add to set to catch duplicates within the new_tasks list too
            tasks_added += 1

    if not dry_run:
        try:
            # Assuming task_board is also jsonl
            with open(task_board_path, "w", encoding="utf-8") as f:
                for entry in final_task_list:
                    json.dump(entry, f)
                    f.write("\\n")
            logger.info(
                f"Successfully wrote {len(final_task_list)} tasks to {task_board_path}"
            )
        except Exception as e:
            logger.error(
                f"Failed to write updated task board to {task_board_path}: {e}",
                exc_info=True,
            )
            # Potentially re-raise or handle as a critical failure
    else:
        logger.info(
            f"[DRY RUN] Would write {len(final_task_list)} tasks to {task_board_path} ({tasks_added} new, {tasks_skipped_duplicates} duplicates skipped from source)."
        )

    return tasks_added, tasks_skipped_duplicates


def deprecate_old_files(files_to_deprecate: list[Path], dry_run: bool = False):
    """Renames old task files by appending '.deprecated'."""
    logger.info("--- Starting Deprecation of Old Task Files ---")
    for old_file in files_to_deprecate:
        if old_file.exists():
            deprecated_name = old_file.with_suffix(old_file.suffix + ".deprecated")
            logger.info(f"Preparing to deprecate {old_file} to {deprecated_name}")
            if not dry_run:
                try:
                    old_file.rename(deprecated_name)
                    logger.info(
                        f"Successfully deprecated {old_file} to {deprecated_name}"
                    )
                except Exception as e:
                    logger.error(f"Failed to deprecate {old_file}: {e}", exc_info=True)
            else:
                logger.info(
                    f"[DRY RUN] Would deprecate {old_file} to {deprecated_name}"
                )
        else:
            logger.warning(f"Old file {old_file} not found for deprecation. Skipping.")


def main():
    parser = argparse.ArgumentParser(
        description="Task Flow Migration Script: Migrates tasks from old JSONL files to a new task_board.jsonl."
    )
    parser.add_argument(
        "--working-tasks",
        type=Path,
        default=Path("working_tasks.json"),
        help="Path to working_tasks.jsonl",
    )
    parser.add_argument(
        "--future-tasks",
        type=Path,
        default=Path("future_tasks.json"),
        help="Path to future_tasks.jsonl",
    )
    parser.add_argument(
        "--task-ready-queue",
        type=Path,
        default=Path("task_ready_queue.json"),
        help="Path to task_ready_queue.jsonl (optional)",
    )
    parser.add_argument(
        "--task-board",
        type=Path,
        required=True,
        help="Path to the target task_board.jsonl",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path(DEFAULT_BACKUP_DIR),
        help="Directory to store backups.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Path to a log file. If None, logs to console only.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without making changes.",
    )
    parser.add_argument(
        "--deprecate-old",
        action="store_true",
        help="After successful migration (not in dry-run), deprecate old task files.",
    )

    args = parser.parse_args()

    # Setup logging
    log_file_path = (
        args.log_file
        if args.log_file
        else Path(
            f"task_migration_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
    )
    setup_logging(args.log_level, log_file_path)

    logger.info("--- Starting Task Flow Migration ---")
    if args.dry_run:
        logger.info(
            "*** DRY RUN MODE ENABLED: No actual file changes will be made to task files. ***"
        )

    # 1. Backup files
    source_files_to_backup = [args.working_tasks, args.future_tasks]
    if (
        args.task_ready_queue and args.task_ready_queue.exists()
    ):  # Only backup if specified and exists
        source_files_to_backup.append(args.task_ready_queue)
    if args.task_board.exists():  # Backup task_board if it exists
        source_files_to_backup.append(args.task_board)

    if not args.dry_run:  # No backup needed for dry run (or make it optional?)
        backup_location = create_backup(source_files_to_backup, args.backup_dir)
        if not backup_location:
            logger.critical("Backup failed. Aborting migration.")
            return 1  # Indicate failure
    else:
        logger.info("[DRY RUN] Skipping backup creation.")

    # 2. Read old tasks
    all_old_tasks_transformed = []

    working_tasks_data = read_jsonl_file(args.working_tasks)
    for task in working_tasks_data:
        transformed = transform_task(task, args.working_tasks.name)
        if transformed:
            all_old_tasks_transformed.append(transformed)

    future_tasks_data = read_jsonl_file(args.future_tasks)
    for task in future_tasks_data:
        transformed = transform_task(task, args.future_tasks.name)
        if transformed:
            all_old_tasks_transformed.append(transformed)

    if args.task_ready_queue.exists():  # Only process if it exists
        task_ready_queue_data = read_jsonl_file(args.task_ready_queue)
        for task in task_ready_queue_data:
            transformed = transform_task(task, args.task_ready_queue.name)
            if transformed:
                all_old_tasks_transformed.append(transformed)
    else:
        logger.info(f"Optional file {args.task_ready_queue} not found. Skipping.")

    logger.info(
        f"Total tasks read and transformed (pre-deduplication): {len(all_old_tasks_transformed)}"
    )

    # 3. Merge into task_board.json
    # The transform_task needs to be robust enough to handle variations.
    # The merge_into_task_board handles duplicates based on task_id.
    tasks_added, tasks_skipped = merge_into_task_board(
        args.task_board, all_old_tasks_transformed, args.dry_run
    )

    logger.info(
        f"Migration summary: Tasks added to board = {tasks_added}, Tasks skipped (duplicates from source files) = {tasks_skipped}"
    )

    # 4. Deprecate old files (if requested and not dry run)
    if args.deprecate_old and not args.dry_run:
        if tasks_added > 0 or (
            tasks_added == 0
            and len(all_old_tasks_transformed) > 0
            and tasks_skipped == len(all_old_tasks_transformed)
        ):
            # Deprecate if new tasks were added, or if all tasks read were already on the board (meaning migration effectively covered them)
            logger.info("Proceeding with deprecation of old task files.")
            files_to_deprecate_paths = [args.working_tasks, args.future_tasks]
            if args.task_ready_queue.exists():
                files_to_deprecate_paths.append(args.task_ready_queue)
            deprecate_old_files(
                files_to_deprecate_paths, args.dry_run
            )  # dry_run here is for safety, already checked
        else:
            logger.warning(
                "Deprecation skipped: No new tasks were successfully added to the task board from the source files, or source files were empty."
            )
    elif args.deprecate_old and args.dry_run:
        logger.info(
            "[DRY RUN] Deprecation step would run if not in dry mode and tasks were processed."
        )

    logger.info("--- Task Flow Migration Finished ---")
    if args.dry_run:
        logger.info("*** DRY RUN COMPLETED ***")
    return 0


if __name__ == "__main__":
    # Example Usage (from command line):
    # python scripts/task_flow_migration.py --task-board runtime/task_board.jsonl --backup-dir runtime/task_migration_backups --log-file runtime/migration.log --deprecate-old --dry-run
    # python scripts/task_flow_migration.py --task-board runtime/task_board.jsonl --working-tasks runtime/working_tasks.json --future-tasks runtime/future_tasks.json --deprecate-old
    sys.exit(main())
