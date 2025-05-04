#!/usr/bin/env python3
"""
scripts/maintenance/find_duplicate_tasks.py

Scans JSON and Markdown task lists within the project to find entries
with duplicate descriptions.

MOVED FROM: src/dreamos/tools/scripts/ by Agent 5 (2025-04-28)
"""

import argparse
import json
import logging
import re
from collections import defaultdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Define project root dynamically
# Assumes script is in PROJECT_ROOT/scripts/maintenance
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Default exclude patterns
DEFAULT_EXCLUDE_PATTERNS = [
    ".git",
    "__pycache__",
    ".venv",
    "env",
    "node_modules",
    "build",
    "dist",
    "runtime/logs",
    "_archive",
]

# File name patterns to identify task lists
TASK_FILE_PATTERNS = [
    "*task*.json",
    "*tasks*.json",
    "*task*.md",
    "*tasks*.md",
    "TODO*.md",
]


def is_excluded(path: Path, exclude_patterns: list[str]) -> bool:
    """Check if a path matches any exclude patterns."""
    return any(
        pattern in path.parts or path.name == pattern for pattern in exclude_patterns
    )


def parse_json_file(path: Path) -> list:
    """Parse a JSON task list and return list of (description, file, line) tuples."""
    tasks = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logging.warning(f"Failed to parse JSON file {path}: {e}")
        return tasks

    # Handle different structures (e.g., list of tasks, dict with 'tasks' key)
    task_list = []
    if isinstance(data, list):
        task_list = data
    elif isinstance(data, dict) and "tasks" in data and isinstance(data["tasks"], list):
        task_list = data["tasks"]
    else:
        logging.debug(f"Skipping JSON file with unrecognized task structure: {path}")
        return tasks

    for idx, task in enumerate(task_list, start=1):
        if not isinstance(task, dict):
            continue
        desc = task.get("description", "").strip()
        if desc:
            tasks.append((desc, str(path.relative_to(PROJECT_ROOT)), idx))
    return tasks


def parse_md_file(path: Path) -> list:
    """Parse a Markdown task list and return list of (description, file, line) tuples."""  # noqa: E501
    tasks = []
    # More flexible pattern for Markdown tasks (e.g., *, -, + checklists)
    pattern = re.compile(r"^\s*[*\-+]\s+\[.?\]\s*(.+)")
    try:
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                m = pattern.match(line)
                if m:
                    desc = m.group(1).strip()
                    tasks.append((desc, str(path.relative_to(PROJECT_ROOT)), idx))
    except Exception as e:
        logging.warning(f"Failed to parse Markdown file {path}: {e}")
    return tasks


def find_task_files(scan_dir: Path, exclude_patterns: list[str]) -> list:
    """Discover all potential task list files in the workspace."""
    task_files = []
    logging.info(f"Scanning for task files in: {scan_dir}")
    for pattern in TASK_FILE_PATTERNS:
        for file_path in scan_dir.rglob(pattern):
            if file_path.is_file() and not is_excluded(file_path, exclude_patterns):
                task_files.append(file_path)
                logging.debug(f"Found potential task file: {file_path}")
            elif is_excluded(file_path, exclude_patterns):
                logging.debug(f"Excluding path: {file_path}")

    # Remove duplicates if patterns overlap
    return sorted(list(set(task_files)))


def normalize(text: str) -> str:
    """Normalize text for comparison (lowercase, alphanumeric only)."""
    return re.sub(r"\W+", " ", text.lower()).strip()


def main(scan_dir: Path, exclude_patterns: list[str]):
    task_entries = []
    found_files = find_task_files(scan_dir, exclude_patterns)
    logging.info(f"Found {len(found_files)} potential task files to parse.")

    for file in found_files:
        if file.suffix == ".json":
            task_entries.extend(parse_json_file(file))
        elif file.suffix == ".md":
            task_entries.extend(parse_md_file(file))

    logging.info(f"Parsed {len(task_entries)} task entries in total.")

    groups = defaultdict(list)
    for desc, path, line in task_entries:
        key = normalize(desc)
        if key:  # Don't group empty normalized descriptions
            groups[key].append((desc, path, line))

    duplicates = {k: v for k, v in groups.items() if len(v) > 1}

    if not duplicates:
        print("\nNo duplicate tasks found based on normalized description.")
    else:
        print("\n--- Duplicate Tasks Found ---\n")
        # Sort duplicates by the first description found
        sorted_duplicates = sorted(duplicates.items(), key=lambda item: item[1][0][0])
        for key, entries in sorted_duplicates:
            # Print the most common original description for the group
            original_descs = [e[0] for e in entries]
            most_common_desc = max(set(original_descs), key=original_descs.count)
            print(f"Normalized Key: '{key}'")
            print(f"Task Description (most common): '{most_common_desc}'")
            for desc, path, line in sorted(
                entries, key=lambda x: (x[1], x[2])
            ):  # Sort locations
                print(f"  - {path} (line ~{line})")
            print()
        print("--- End of Duplicates ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find duplicate task descriptions across JSON and Markdown files."
    )
    parser.add_argument(
        "--scan-dir",
        default=str(PROJECT_ROOT),
        type=Path,
        help=f"Directory to scan recursively (default: {PROJECT_ROOT})",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Directory or file name pattern to exclude (can be specified multiple times).",  # noqa: E501
    )
    args = parser.parse_args()
    exclude_list = args.exclude + DEFAULT_EXCLUDE_PATTERNS

    main(scan_dir=args.scan_dir, exclude_patterns=exclude_list)
