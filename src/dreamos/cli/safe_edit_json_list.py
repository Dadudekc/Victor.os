"""Command-line interface for safely editing items in a JSON list file."""

import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

# --- File Locking ---
try:
    import filelock

    FILELOCK_AVAILABLE = True
except ImportError:
    filelock = None
    FILELOCK_AVAILABLE = False
    logging.warning(
        "safe_edit_json_list: filelock library not found. File editing will not be fully concurrency-safe."
    )

# --- JSON Schema Validation --- ADDED START
try:
    import jsonschema

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    jsonschema = None
    JSONSCHEMA_AVAILABLE = False
    logging.warning(
        "safe_edit_json_list: jsonschema library not found. Schema validation disabled."
    )
# --- JSON Schema Validation --- ADDED END

# --- Path Setup (copied from safe_writer_cli.py for consistency) --- START
# This assumes the script is run from the project root (D:\Dream.os)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (
    SCRIPT_DIR.parent.parent.parent
)  # src/dreamos/cli -> src/dreamos -> src -> .
SRC_PATH = SCRIPT_DIR.parent.parent  # src/dreamos/cli -> src/dreamos -> src
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
# --- Path Setup --- END

# --- Logging Setup ---
log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level_str, logging.INFO),
    format="%(asctime)s - safe_edit_json_list - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
# --- Logging Setup End ---


class SafeEditError(Exception):
    """Custom exception for errors during safe JSON list editing."""

    pass


def _atomic_write_json(target_path: Path, data: List[Dict[str, Any]]) -> None:
    """Writes JSON data atomically using a temporary file and rename."""
    temp_file_path = target_path.with_suffix(f".tmp_{uuid.uuid4().hex}")
    try:
        with open(temp_file_path, "w", encoding="utf-8") as f_temp:
            json.dump(data, f_temp, indent=2)
        os.replace(temp_file_path, target_path)
        logger.debug(f"Atomically wrote updated JSON to {target_path}")
    except (IOError, OSError, TypeError) as e:
        # Cleanup failed temp file if it exists
        if temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except OSError:
                pass  # Ignore cleanup error
        raise SafeEditError(f"Failed during atomic write to {target_path}: {e}") from e


@click.command()
@click.option(
    "--target-file",
    required=True,
    type=click.Path(
        exists=True, dir_okay=False, writable=True, readable=True, path_type=Path
    ),
    help="The path to the JSON list file to edit.",
)
@click.option(
    "--action",
    required=True,
    type=click.Choice(["add", "remove", "update"], case_sensitive=False),
    help="Action to perform: add, remove, or update an item.",
)
@click.option(
    "--item-id-key",
    default="task_id",
    show_default=True,
    help="The dictionary key within list items used for identification (e.g., 'task_id', 'id').",
)
@click.option("--item-id", help="The ID of the item to remove or update.")
@click.option(
    "--item-data",
    help="JSON string representing the item to add or the updates to apply.",
)
@click.option(
    "--lock-timeout",
    type=int,
    default=10,
    show_default=True,
    help="Timeout in seconds for acquiring the file lock.",
)
@click.option(
    "--schema-file",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="Optional path to a JSON schema file to validate the entire list against before writing.",
)
def safe_edit_json_list(
    target_file: Path,
    action: str,
    item_id_key: str,
    item_id: Optional[str],
    item_data: Optional[str],
    lock_timeout: int,
    schema_file: Optional[Path],
):
    """Safely ADD, REMOVE, or UPDATE items in a JSON list file using locking."""
    logger.info(f"Attempting action '{action}' on file: {target_file}")

    # --- Input Validation ---
    if action in ["remove", "update"] and not item_id:
        click.echo(f"Error: --item-id is required for action '{action}'.", err=True)
        sys.exit(1)
    if action in ["add", "update"] and not item_data:
        click.echo(
            f"Error: --item-data (as JSON string) is required for action '{action}'.",
            err=True,
        )
        sys.exit(1)

    parsed_item_data = None
    if item_data:
        try:
            parsed_item_data = json.loads(item_data)
            if not isinstance(parsed_item_data, dict):
                raise ValueError("item-data must be a JSON object (dictionary).")
        except json.JSONDecodeError as e:
            click.echo(f"Error: Invalid JSON provided for --item-data: {e}", err=True)
            sys.exit(1)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    # --- JSON Schema Validation --- ADDED START
    schema = None
    if schema_file:
        if not JSONSCHEMA_AVAILABLE or not jsonschema:
            logger.warning(
                f"--schema-file provided ({schema_file}), but jsonschema library is not available. Skipping validation."
            )
        else:
            try:
                with open(schema_file, "r", encoding="utf-8") as f_schema:
                    schema = json.load(f_schema)
                logger.info(f"Loaded validation schema from {schema_file}")
            except (IOError, json.JSONDecodeError) as e:
                click.echo(
                    f"Error: Failed to load or parse schema file {schema_file}: {e}",
                    err=True,
                )
                sys.exit(1)
    # --- JSON Schema Validation --- ADDED END

    # --- Locking and File Operations ---
    lock_path = target_file.with_suffix(target_file.suffix + ".lock")
    lock = None
    lock_acquired = False

    if FILELOCK_AVAILABLE and filelock:
        lock = filelock.FileLock(lock_path, timeout=lock_timeout)
    else:
        logger.warning(
            f"Proceeding without file lock for {target_file} due to missing library."
        )

    try:
        # Acquire lock
        if lock:
            logger.debug(f"Acquiring lock for {target_file}...")
            lock.acquire()
            lock_acquired = True
            logger.debug(f"Lock acquired for {target_file}.")

        # Read current data
        logger.debug(f"Reading current data from {target_file}...")
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                # Handle empty file case - treat as empty list
                content = f.read().strip()
                if not content:
                    data = []
                else:
                    data = json.loads(content)
            if not isinstance(data, list):
                raise SafeEditError(
                    f"Target file {target_file} does not contain a valid JSON list."
                )
        except json.JSONDecodeError as e:
            raise SafeEditError(f"Failed to decode JSON from {target_file}: {e}") from e
        except IOError as e:
            raise SafeEditError(f"Failed to read {target_file}: {e}") from e

        original_count = len(data)
        modified = False
        found_item = None

        # Perform action
        if action == "add":
            logger.debug(f"Adding new item: {parsed_item_data}")
            # Optionally check if ID already exists?
            data.append(parsed_item_data)
            modified = True

        elif action == "remove":
            logger.debug(f"Attempting to remove item with {item_id_key}={item_id}")
            initial_len = len(data)
            data = [
                item
                for item in data
                if not (
                    isinstance(item, dict) and str(item.get(item_id_key)) == item_id
                )
            ]
            if len(data) < initial_len:
                modified = True
                logger.info(f"Removed item with {item_id_key}={item_id}")
            else:
                logger.warning(
                    f"Item with {item_id_key}={item_id} not found for removal."
                )
                # Decide if not found is an error or just a no-op
                # For robustness, treat as no-op for now.
                # click.echo(f"Warning: Item with {item_id_key}={item_id} not found.", err=True)

        elif action == "update":
            logger.debug(f"Attempting to update item with {item_id_key}={item_id}")
            item_index = -1
            for i, item in enumerate(data):
                if isinstance(item, dict) and str(item.get(item_id_key)) == item_id:
                    item_index = i
                    found_item = item  # Keep original for logging/comparison
                    break

            if item_index != -1:
                logger.debug(
                    f"Found item at index {item_index}. Applying updates: {parsed_item_data}"
                )
                # Simple merge: update existing keys, add new ones
                data[item_index].update(parsed_item_data)
                modified = True
                logger.info(f"Updated item with {item_id_key}={item_id}")
            else:
                logger.warning(
                    f"Item with {item_id_key}={item_id} not found for update."
                )
                # Decide if not found is an error or just a no-op
                # click.echo(f"Warning: Item with {item_id_key}={item_id} not found.", err=True)

        # Write back if modified
        if modified:
            logger.info(
                f"Data modified (original count: {original_count}, new count: {len(data)}). Writing back to {target_file}"
            )

            # --- JSON Schema Validation --- ADDED START
            if schema and JSONSCHEMA_AVAILABLE and jsonschema:
                try:
                    logger.debug(
                        f"Validating modified data against schema from {schema_file}..."
                    )
                    jsonschema.validate(instance=data, schema=schema)
                    logger.info("Schema validation passed.")
                except jsonschema.ValidationError as e:
                    # Log the full error for debugging, but maybe only show concise error to user?
                    logger.error(
                        f"Schema validation failed for modified data: {e}",
                        exc_info=False,
                    )
                    # Potentially log data that failed validation if not too large/sensitive
                    # logger.debug(f"Data that failed validation: {json.dumps(data, indent=2)}")
                    click.echo(
                        f"Error: Modified data failed schema validation (schema: {schema_file}). Changes not written. Validation error: {e.message}",
                        err=True,
                    )
                    # Do not write the invalid data - exit before _atomic_write_json
                    sys.exit(1)
            # --- JSON Schema Validation --- ADDED END

            _atomic_write_json(target_file, data)
            click.echo(
                f"Success: File {target_file} updated (action: {action}).", err=False
            )
        else:
            logger.info(
                f"No modifications made for action '{action}' (item not found or no changes). File not rewritten."
            )
            click.echo(
                f"Success: No changes needed for file {target_file} (action: {action}).",
                err=False,
            )

    except filelock.Timeout as e:
        logger.error(f"Timeout ({lock_timeout}s) acquiring lock for {target_file}.")
        click.echo(f"Error: Timeout acquiring lock for {target_file}", err=True)
        sys.exit(1)
    except SafeEditError as e:
        logger.error(f"Failed action '{action}' on {target_file}: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        click.echo(f"Error: An unexpected error occurred: {e}", err=True)
        sys.exit(1)
    finally:
        # Release lock
        if lock_acquired and lock and lock.is_locked:
            try:
                lock.release()
                logger.debug(f"Lock released for {target_file}.")
            except Exception as e:
                logger.error(
                    f"Failed to release lock for {target_file}: {e}", exc_info=True
                )


if __name__ == "__main__":
    safe_edit_json_list()
