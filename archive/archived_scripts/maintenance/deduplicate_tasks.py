#!/usr/bin/env python3
"""
scripts/maintenance/deduplicate_tasks.py

Deduplicates tasks across JSON files found in a specified directory.
Primarily intended for cleaning up task lists.

MOVED FROM: src/dreamos/tools/scripts/ by Agent 5 (2025-04-28)
"""

import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Define project root dynamically
# Assumes script is in PROJECT_ROOT/scripts/maintenance
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TASK_DIR = PROJECT_ROOT / "tasks"  # Default to top-level tasks dir
DEFAULT_OUTPUT_FILENAME = "tasks_deduplicated.json"


def load_tasks(dir_path: Path) -> list:
    """Loads tasks from all JSON files in the directory."""
    tasks = []
    if not dir_path.is_dir():
        logging.error(f"Task directory not found: {dir_path}")
        return tasks

    logging.info(f"Loading tasks from JSON files in: {dir_path}")
    for file_path in dir_path.glob("*.json"):
        if file_path.name == DEFAULT_OUTPUT_FILENAME:  # Avoid reading previous output
            continue
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Handle list of tasks or dict with 'tasks' key
                task_list = []
                if isinstance(data, list):
                    task_list = data
                elif (
                    isinstance(data, dict)
                    and "tasks" in data
                    and isinstance(data["tasks"], list)
                ):
                    task_list = data["tasks"]
                else:
                    logging.warning(
                        f"Skipping file with unrecognized structure: {file_path}"
                    )
                    continue

                # Add source file info?
                for task in task_list:
                    if isinstance(task, dict):
                        task["_source_file"] = str(file_path.relative_to(PROJECT_ROOT))
                tasks.extend(task_list)
                logging.debug(f"Loaded {len(task_list)} tasks from {file_path.name}")
        except json.JSONDecodeError:
            logging.warning(f"Skipping invalid JSON file: {file_path}")
        except Exception as e:
            logging.warning(f"Failed to load tasks from {file_path}: {e}")
    return tasks


def deduplicate_tasks(tasks: list) -> list:
    """Deduplicates tasks based on a combination of key fields."""
    seen = set()
    unique_tasks = []
    duplicates_count = 0
    for task in tasks:
        if not isinstance(task, dict):
            continue  # Skip non-dict items

        # Define the key for uniqueness check (adjust fields as needed)
        # Using description and potentially phase/id if available and reliable
        description = task.get("description", "").strip().lower()
        task_id = task.get("id")  # noqa: F841
        phase = task.get("phase")  # noqa: F841
        # Simple key based on description for now
        key = description

        # More robust key (example):
        # key = (
        #     description,
        #     phase,
        #     # Consider other fields if needed for uniqueness
        # )

        if not key:  # Skip tasks with empty descriptions
            continue

        if key not in seen:
            seen.add(key)
            unique_tasks.append(task)
        else:
            duplicates_count += 1
            logging.debug(f"Duplicate found (key='{key}'): {task.get('description')}")

    logging.info(
        f"Removed {duplicates_count} duplicate tasks based on the defined key."
    )
    return unique_tasks


def main(task_dir: Path, output_file: Path):
    tasks = load_tasks(task_dir)
    if not tasks:
        logging.warning("No tasks loaded. Nothing to deduplicate.")
        return

    unique = deduplicate_tasks(tasks)

    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(unique, f, indent=2, ensure_ascii=False)
        logging.info(
            f"Deduplication complete. Saved {len(unique)} unique tasks to {output_file}"
        )
    except Exception as e:
        logging.error(f"Failed to write deduplicated tasks to {output_file}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Deduplicate tasks found in JSON files within a directory."
    )
    parser.add_argument(
        "--task-dir",
        default=str(DEFAULT_TASK_DIR),
        type=Path,
        help=f"Directory containing task JSON files (default: {DEFAULT_TASK_DIR})",
    )
    parser.add_argument(
        "--output-file",
        default=None,
        type=Path,
        help=f"Output file for deduplicated tasks (defaults to [task-dir]/{DEFAULT_OUTPUT_FILENAME})",  # noqa: E501
    )
    args = parser.parse_args()

    output_path = args.output_file or (args.task_dir / DEFAULT_OUTPUT_FILENAME)

    main(task_dir=args.task_dir, output_file=output_path)
