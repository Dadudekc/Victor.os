#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Template Script for Safe JSON List File Manipulation.

Loads a JSON file expected to contain a list, performs a specified modification
(e.g., append, update, delete based on args), validates the change,
and saves atomically. Exits with status code 0 on success, non-zero on failure.
"""

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- Setup Logging ---
# Basic logging config, adjust format/level as needed for integration
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    stream=sys.stderr,  # Log to stderr to separate from potential JSON output
)
logger = logging.getLogger("SafeJsonEditor")

# --- Core Functions ---


def load_json_list(file_path: Path) -> Optional[List[Dict[str, Any]]]:
    """Loads JSON data from a file, expecting a list. Handles errors gracefully."""
    if not file_path.exists():
        logger.error(f"Error: Target file does not exist: {file_path}")
        return None
    try:
        content = file_path.read_text(encoding="utf-8").strip()
        if not content:
            logger.warning(
                f"Warning: File is empty: {file_path}. Returning empty list."
            )
            return []  # Return empty list for empty file

        data = json.loads(content)
        if not isinstance(data, list):
            logger.error(f"Error: File does not contain a JSON list: {file_path}")
            return None
        logger.info(f"Successfully loaded {len(data)} items from {file_path}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {e}")
        return None
    except IOError as e:
        logger.error(f"IOError reading file {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading file {file_path}: {e}", exc_info=True)
        return None


def atomic_write_json(file_path: Path, data: List[Dict[str, Any]]):
    """Writes data to a file atomically using a temporary file and rename."""
    temp_file_path = None  # Define outside try block
    try:
        # Create temp file in the same directory to ensure rename works across filesystems  # noqa: E501
        temp_fd, temp_path_str = tempfile.mkstemp(
            dir=file_path.parent, prefix=file_path.stem + "_", suffix=".tmp.json"
        )
        temp_file_path = Path(temp_path_str)

        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)  # Use indent for readability

        # Attempt to replace the original file with the temporary file
        os.replace(temp_file_path, file_path)
        logger.info(f"Atomically wrote {len(data)} items to {file_path}")
        temp_file_path = None  # Prevent cleanup attempt in finally block

    except OSError as e:
        logger.error(f"OSError during atomic write to {file_path}: {e}")
        raise  # Re-raise to indicate failure
    except Exception as e:
        logger.error(
            f"Unexpected error during atomic write to {file_path}: {e}", exc_info=True
        )
        raise  # Re-raise
    finally:
        # Clean up temp file if something went wrong before os.replace
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink()
                logger.debug(f"Cleaned up temporary file: {temp_file_path}")
            except OSError as unlink_e:
                logger.error(
                    f"Error: Failed to remove temporary file {temp_file_path}: {unlink_e}"  # noqa: E501
                )


def add_item_to_list(
    data: List[Dict[str, Any]], item_to_add: Dict[str, Any], id_field: str = "task_id"
) -> bool:
    """Adds a new item, checking for duplicate IDs."""
    item_id = item_to_add.get(id_field)
    if not item_id:
        logger.error(f"Error: Item to add is missing the ID field '{id_field}'.")
        return False

    if any(existing_item.get(id_field) == item_id for existing_item in data):
        logger.error(
            f"Error: Item with ID '{item_id}' already exists. Cannot add duplicate."
        )
        return False

    data.append(item_to_add)
    logger.info(f"Added item with ID: {item_id}")
    return True


# --- Main Execution ---


def main():
    parser = argparse.ArgumentParser(
        description="Safely load, modify, and save a JSON list file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target_file", type=str, help="Path to the target JSON file.")
    parser.add_argument(
        "--add-json",
        type=str,
        metavar="JSON_STRING",
        help="A JSON string representing the dictionary object to add to the list.",
    )
    # Add other arguments for different operations (e.g., --update-id, --update-data, --delete-id)  # noqa: E501
    # parser.add_argument("--update-id", type=str, help="ID of the item to update.")
    # parser.add_argument("--update-json", type=str, help="JSON string of updates to apply.")  # noqa: E501
    # parser.add_argument("--delete-id", type=str, help="ID of the item to delete.")
    parser.add_argument(
        "--id-field",
        type=str,
        default="task_id",
        help="The dictionary key to use as the unique identifier for items (default: task_id).",  # noqa: E501
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging."
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")

    target_file_path = Path(args.target_file).resolve()
    logger.info(f"Target file: {target_file_path}")

    # --- Load ---
    data = load_json_list(target_file_path)
    if data is None:
        logger.critical("Failed to load or parse the target JSON file. Aborting.")
        sys.exit(1)

    # --- Modify ---
    modified = False
    if args.add_json:
        try:
            item_to_add = json.loads(args.add_json)
            if not isinstance(item_to_add, dict):
                raise ValueError("Input JSON must be an object/dictionary.")
            if add_item_to_list(data, item_to_add, args.id_field):
                modified = True
            else:
                logger.error("Failed to add item.")
                sys.exit(2)  # Specific exit code for modification failure
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding --add-json argument: {e}")
            sys.exit(1)
        except ValueError as e:
            logger.error(f"Invalid data in --add-json argument: {e}")
            sys.exit(1)

    # Add elif blocks here for other operations like update, delete
    # elif args.update_id and args.update_json:
    #     # Implement update logic
    #     pass
    # elif args.delete_id:
    #     # Implement delete logic
    #     pass

    if not modified:
        logger.info("No modifications performed.")
        # Optionally exit here if no operation was specified, or just proceed to save (no-op save)  # noqa: E501
        # sys.exit(0)

    # --- Save ---
    try:
        atomic_write_json(target_file_path, data)
    except Exception as e:
        logger.critical(f"Failed to save the updated JSON file: {e}. Aborting.")
        sys.exit(3)  # Specific exit code for save failure

    # --- Validate (Optional but recommended) ---
    logger.info("Validating saved file by reloading...")
    reloaded_data = load_json_list(target_file_path)
    if reloaded_data is None:
        logger.critical(
            "CRITICAL: Failed to reload and validate the saved file! State may be corrupt."  # noqa: E501
        )
        sys.exit(4)  # Specific exit code for validation failure
    elif len(reloaded_data) != len(data):  # Basic sanity check
        logger.critical(
            f"CRITICAL: Validation failed! Item count mismatch after save (Expected: {len(data)}, Found: {len(reloaded_data)}). State may be corrupt."  # noqa: E501
        )
        sys.exit(4)
    else:
        logger.info("Validation successful. File saved correctly.")

    logger.info("Script completed successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
