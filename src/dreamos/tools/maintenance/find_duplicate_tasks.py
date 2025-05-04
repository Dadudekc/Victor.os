"""
src/dreamos/tools/maintenance/find_duplicate_tasks.py

Scans JSON and Markdown task lists within the project to find entries
with duplicate descriptions.

Resurrected from: _archive/scripts/maintenance/find_duplicate_tasks.py
"""

import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple  # Added for better type hinting

# Rely on external configuration for logging level
logger = logging.getLogger(__name__)

# Define project root dynamically
# Assumes script is in PROJECT_ROOT/src/dreamos/tools/maintenance
# PROJECT_ROOT should ideally come from config or a shared utility
try:
    # Try to import find_project_root if it exists
    # NOTE: This creates a potential dependency cycle if find_project_root needs this tool
    # A better pattern is to pass PROJECT_ROOT or config object in.
    # For now, let's assume it works or we pass it in.
    from dreamos.utils.project_root import find_project_root

    PROJECT_ROOT = find_project_root()
except ImportError:
    logger.warning("Could not import find_project_root. Relying on path calculation.")
    # Fallback calculation (adjust as needed if script location changes)
    PROJECT_ROOT = Path(__file__).resolve().parents[4]

# Default exclude patterns (Consider moving to config)
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
    ".vscode",
    ".idea",
]

# File name patterns to identify task lists (Consider moving to config)
TASK_FILE_PATTERNS = [
    "*task*.json",
    "*tasks*.json",
    "*task*.md",
    "*tasks*.md",
    "TODO*.md",
    "*backlog.json",
]


def is_excluded(path: Path, exclude_patterns: List[str]) -> bool:
    """Check if a path matches any exclude patterns."""
    # {{ EDIT START: Ensure string comparisons and safe match }}
    path_str = str(path)
    path_parts_set = set(path.parts)
    for pattern in exclude_patterns:
        pattern_str = str(pattern)  # Ensure pattern is also a string
        # Check if pattern is a directory/file name match in parts
        if pattern_str in path_parts_set:
            return True
        # Check if pattern is exact filename match
        if path.name == pattern_str:
            return True
        # Attempt glob match safely
        try:
            if path.match(pattern_str):
                return True
        except ValueError:
            # Handle cases where pattern is not a valid glob, compare as substring
            if pattern_str in path_str:
                return True
        # Fallback substring check (less precise)
        # if pattern_str in path_str:
        #     return True
    return False
    # {{ EDIT END }}


def parse_json_file(path: Path) -> List[Tuple[str, str, int]]:
    """Parse a JSON task list and return list of (description, file, line) tuples."""
    tasks = []
    try:
        # Use line numbers approximating the start of the task object
        # Reading line by line to get approx line number is too slow here.
        # We estimate based on typical JSON formatting.
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            data = json.loads(content)
    except Exception as e:
        logger.warning(f"Failed to parse JSON file {path}: {e}")
        return tasks

    task_list = []
    if isinstance(data, list):
        task_list = data
    elif isinstance(data, dict) and "tasks" in data and isinstance(data["tasks"], list):
        task_list = data["tasks"]
    else:
        logger.debug(f"Skipping JSON file with unrecognized task structure: {path}")
        return tasks

    # Estimate line numbers - crude but better than nothing
    lines_in_file = content.count("\n")
    approx_lines_per_task = (lines_in_file / len(task_list)) if task_list else 10

    for idx, task in enumerate(task_list):
        if not isinstance(task, dict):
            continue
        desc = task.get("description", "").strip()
        if desc:
            # Use estimated line number
            line_num_est = int(idx * approx_lines_per_task) + 1
            tasks.append((desc, str(path.relative_to(PROJECT_ROOT)), line_num_est))
    return tasks


def parse_md_file(path: Path) -> List[Tuple[str, str, int]]:
    """Parse a Markdown task list and return list of (description, file, line) tuples."""
    tasks = []
    # More flexible pattern for Markdown tasks (e.g., *, -, + checklists)
    # Handles optional status like [x], [ ], [-], etc.
    pattern = re.compile(r"^\s*[*\-+]\s+\[[\sx\-~*]?\]\s*(.+)")
    try:
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                m = pattern.match(line)
                if m:
                    desc = m.group(1).strip()
                    if desc:
                        tasks.append((desc, str(path.relative_to(PROJECT_ROOT)), idx))
    except Exception as e:
        logger.warning(f"Failed to parse Markdown file {path}: {e}")
    return tasks


def find_task_files(scan_dir: Path, exclude_patterns: List[str]) -> List[Path]:
    """Discover all potential task list files in the workspace."""
    task_files = []
    logger.info(f"Scanning for task files in: {scan_dir}")
    if not scan_dir.is_dir():
        logger.error(f"Scan directory does not exist or is not a directory: {scan_dir}")
        return []

    for pattern in TASK_FILE_PATTERNS:
        try:
            logger.debug(f"Searching with pattern: {pattern} in {scan_dir}")
            for file_path in scan_dir.rglob(pattern):
                logger.debug(f"Found path: {file_path}")
                # {{ EDIT START: Add explicit file and hidden file check }}
                if not file_path.is_file():
                    logger.debug(f"Skipping non-file path: {file_path}")
                    continue
                if file_path.name.startswith("."):
                    logger.debug(f"Skipping hidden file: {file_path}")
                    continue
                # {{ EDIT END }}

                # Check exclusion before checking if it's a file to avoid logging excluded dirs
                if is_excluded(file_path, exclude_patterns):
                    logger.debug(f"Excluding path based on patterns: {file_path}")
                    continue

                # Already checked if is_file earlier
                task_files.append(file_path)
                logger.debug(f"Added potential task file: {file_path}")

        except PermissionError:
            logger.warning(
                f"Permission denied accessing files in {scan_dir} for pattern {pattern}. Skipping."
            )
        except Exception as e:
            logger.error(
                f"Error during file search for pattern {pattern} in {scan_dir}: {e}"
            )

    # Remove duplicates and sort
    unique_files = sorted(list(set(task_files)))
    logger.info(
        f"Found {len(unique_files)} unique potential task files after filtering."
    )
    return unique_files


def normalize(text: Any) -> str:  # Accept Any type initially
    """Normalize text for comparison (lowercase, alphanumeric only)."""
    # {{ EDIT START: Ensure input is string before processing }}
    if not isinstance(text, str):
        text = str(text)  # Convert Path or other types to string
    if not text:
        return ""
    # {{ EDIT END }}
    # Keep spaces for better key readability, remove other non-alphanumeric
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_duplicate_tasks(
    scan_dir: Path = PROJECT_ROOT,
    exclude_patterns: List[str] = DEFAULT_EXCLUDE_PATTERNS,
) -> Dict[str, List[Tuple[str, str, int]]]:
    """Finds and returns duplicate tasks based on normalized descriptions.

    Args:
        scan_dir: The directory to scan recursively for task files.
        exclude_patterns: A list of patterns to exclude from the scan.

    Returns:
        A dictionary where keys are normalized descriptions and values are lists
        of (original_description, file_path, line_number) tuples for duplicates.
    """
    task_entries: List[Tuple[str, str, int]] = []
    found_files = find_task_files(scan_dir, exclude_patterns)
    logger.info(f"Found {len(found_files)} potential task files to parse.")

    for file in found_files:
        if file.suffix == ".json":
            task_entries.extend(parse_json_file(file))
        elif file.suffix == ".md":
            task_entries.extend(parse_md_file(file))

    logger.info(f"Parsed {len(task_entries)} task entries in total.")

    groups: Dict[str, List[Tuple[str, str, int]]] = defaultdict(list)
    for desc, path, line in task_entries:
        key = normalize(desc)
        if key:  # Don't group empty normalized descriptions
            groups[key].append((desc, path, line))

    duplicates = {k: v for k, v in groups.items() if len(v) > 1}

    if not duplicates:
        logger.info("No duplicate tasks found based on normalized description.")
    else:
        logger.warning(f"Found {len(duplicates)} groups of duplicate tasks.")
        # Optionally log the duplicates here or let the caller handle reporting
        # Example logging:
        # sorted_duplicates = sorted(duplicates.items(), key=lambda item: item[1][0][0])
        # for key, entries in sorted_duplicates:
        #     logger.warning(f"Duplicate Key: '{key}'")
        #     for desc, path, line in entries:
        #         logger.warning(f"  - {path} (line ~{line}): '{desc[:80]}...'")

    return duplicates


# Removed the __main__ block and argparse, function is now callable.
