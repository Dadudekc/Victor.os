"""
src/dreamos/tools/maintenance/find_duplicate_tasks.py

Scans JSON and Markdown task lists within the project to find entries
with duplicate descriptions.

Resurrected from: _archive/scripts/maintenance/find_duplicate_tasks.py
"""

import json
import logging
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

# Rely on external configuration for logging level
logger = logging.getLogger(__name__)

# Constants
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
REPORT_DIR = PROJECT_ROOT / "reports"
DEFAULT_EXCLUDE_PATTERNS = [
    "**/node_modules/**",
    "**/__pycache__/**",
    "**/.git/**",
    "**/venv/**",
    "**/env/**",
    "**/dist/**",
    "**/build/**",
    "**/.idea/**",
    "**/.vscode/**",
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

# Backup directory
BACKUP_DIR = PROJECT_ROOT / "runtime" / "backups" / "task_cleanup"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


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


def parse_json_file(file_path: Path) -> List[Tuple[str, str, int, Dict[str, Any]]]:
    """Parse a JSON file containing tasks and return a list of (description, file_path, line_number, metadata) tuples."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Try to repair common JSON issues
        content = repair_json_content(content)

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file {file_path}: {str(e)}")
            return []

        tasks = []
        if isinstance(data, list):
            for i, task in enumerate(data, 1):
                if isinstance(task, dict) and "description" in task:
                    metadata = {k: v for k, v in task.items() if k != "description"}
                    tasks.append((task["description"], str(file_path), i, metadata))
        elif isinstance(data, dict):
            for i, (key, task) in enumerate(data.items(), 1):
                if isinstance(task, dict) and "description" in task:
                    metadata = {k: v for k, v in task.items() if k != "description"}
                    tasks.append((task["description"], str(file_path), i, metadata))

        return tasks
    except Exception as e:
        logger.error(f"Error processing JSON file {file_path}: {str(e)}")
        return []


def parse_md_file(file_path: Path) -> List[Tuple[str, str, int, Dict[str, Any]]]:
    """Parse a markdown file containing tasks and return a list of (description, file_path, line_number, metadata) tuples."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        tasks = []
        current_task = None
        current_metadata = {}
        line_number = 0

        for i, line in enumerate(lines, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Check for task markers
            if line.startswith("- [ ]") or line.startswith("- [x]"):
                # Save previous task if exists
                if current_task:
                    tasks.append(
                        (current_task, str(file_path), line_number, current_metadata)
                    )

                # Start new task
                current_task = line[6:].strip()  # Remove "- [ ] " or "- [x] "
                current_metadata = {
                    "status": "completed" if line.startswith("- [x]") else "pending",
                    "task_type": "markdown_task",
                }
                line_number = i

            # Check for metadata in YAML frontmatter
            elif line.startswith("---") and i < len(lines):
                yaml_content = []
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith("---"):
                    yaml_content.append(lines[j])
                    j += 1

                if yaml_content:
                    try:
                        metadata = yaml.safe_load("".join(yaml_content))
                        if isinstance(metadata, dict):
                            current_metadata.update(metadata)
                    except yaml.YAMLError:
                        pass

        # Add the last task if exists
        if current_task:
            tasks.append((current_task, str(file_path), line_number, current_metadata))

        return tasks
    except Exception as e:
        logger.error(f"Error processing markdown file {file_path}: {str(e)}")
        return []


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
) -> Dict[str, List[Tuple[str, str, int, Dict[str, Any]]]]:
    """Finds and returns duplicate tasks based on normalized descriptions.

    Args:
        scan_dir: The directory to scan recursively for task files.
        exclude_patterns: A list of patterns to exclude from the scan.

    Returns:
        A dictionary where keys are normalized descriptions and values are lists
        of (original_description, file_path, line_number, metadata) tuples for duplicates.
    """
    task_entries: List[Tuple[str, str, int, Dict[str, Any]]] = []
    found_files = find_task_files(scan_dir, exclude_patterns)
    logger.info(f"Found {len(found_files)} potential task files to parse.")

    for file in found_files:
        if file.suffix == ".json":
            tasks = parse_json_file(file)
            for desc, path, line, metadata in tasks:
                task_entries.append((desc, path, line, metadata))
        elif file.suffix == ".md":
            tasks = parse_md_file(file)
            for desc, path, line, metadata in tasks:
                task_entries.append((desc, path, line, metadata))

    logger.info(f"Parsed {len(task_entries)} task entries in total.")

    groups: Dict[str, List[Tuple[str, str, int, Dict[str, Any]]]] = defaultdict(list)
    for desc, path, line, metadata in task_entries:
        key = normalize(desc)
        if key:  # Don't group empty normalized descriptions
            groups[key].append((desc, path, line, metadata))

    duplicates = {k: v for k, v in groups.items() if len(v) > 1}

    if not duplicates:
        logger.info("No duplicate tasks found based on normalized description.")
    else:
        logger.warning(f"Found {len(duplicates)} groups of duplicate tasks.")

    return duplicates


def backup_file(file_path: Path) -> Optional[Path]:
    """Create a backup of a file before modifying it."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"{file_path.name}.{timestamp}.bak"
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to backup {file_path}: {e}")
        return None


def get_task_metadata(task: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant metadata from a task."""
    return {
        "task_id": task.get("task_id", ""),
        "task_type": task.get("task_type", ""),
        "priority": task.get("priority", ""),
        "assigned_agent": task.get("assigned_agent", ""),
        "status": task.get("status", ""),
        "created_at": task.get("created_at", ""),
        "timestamp_completed_utc": task.get("timestamp_completed_utc", ""),
    }


def determine_canonical_task(
    entries: List[Tuple[str, str, int, Dict[str, Any]]],
) -> Tuple[str, str, int, Dict[str, Any]]:
    """Determine the canonical version of a duplicate task.

    Args:
        entries: List of (description, file_path, line_number, metadata) tuples

    Returns:
        The canonical task entry
    """
    # First try to find a task with a task_id
    for entry in entries:
        if entry[3].get("task_id"):
            return entry

    # Then try to find a task with status "in_progress" or "assigned"
    for entry in entries:
        status = entry[3].get("status", "").lower()
        if status in ["in_progress", "assigned"]:
            return entry

    # Then try to find a task with a priority
    for entry in entries:
        if entry[3].get("priority"):
            return entry

    # Then try to find a task with an assigned agent
    for entry in entries:
        if entry[3].get("assigned_agent"):
            return entry

    # Finally, just return the first entry
    return entries[0]


def generate_markdown_report(
    duplicates: Dict[str, List[Tuple[str, str, int, Dict[str, Any]]]],
) -> None:
    """Generate a detailed markdown report of duplicate tasks."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_path = REPORT_DIR / "duplicate_tasks_report.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Duplicate Tasks Report\n\n")
        f.write(f"Generated: {timestamp}\n\n")

        if not duplicates:
            f.write("✅ No duplicate tasks found.\n")
            return

        # Summary statistics
        total_duplicates = sum(len(entries) for entries in duplicates.values())
        unique_duplicates = len(duplicates)
        f.write("## Summary\n\n")
        f.write(f"- Total duplicate entries: {total_duplicates}\n")
        f.write(f"- Unique duplicate groups: {unique_duplicates}\n\n")

        # Per-file statistics
        file_stats = defaultdict(int)
        for entries in duplicates.values():
            for desc, file_path, line, _ in entries:
                file_stats[file_path] += 1

        f.write("### Duplicates by File\n\n")
        f.write("| File | Duplicate Count |\n")
        f.write("|------|----------------|\n")
        for file_path, count in sorted(
            file_stats.items(), key=lambda x: x[1], reverse=True
        ):
            f.write(f"| `{file_path}` | {count} |\n")
        f.write("\n")

        # Detailed duplicate groups
        f.write("## Detailed Duplicate Groups\n\n")

        for normalized_desc, entries in sorted(
            duplicates.items(), key=lambda x: x[1][0][0]
        ):
            canonical = determine_canonical_task(entries)

            f.write("### Duplicate Group\n\n")
            f.write(f"Normalized Description: `{normalized_desc}`\n\n")
            f.write(
                "| Original Description | File | Line | Task ID | Type | Priority | Agent | Status |\n"
            )
            f.write(
                "|---------------------|------|------|---------|------|----------|-------|--------|\n"
            )

            for desc, file_path, line, metadata in entries:
                is_canonical = (desc, file_path, line, metadata) == canonical
                task_id = metadata.get("task_id", "")
                task_type = metadata.get("task_type", "")
                priority = metadata.get("priority", "")
                agent = metadata.get("assigned_agent", "")
                status = metadata.get("status", "")

                # Mark canonical version with a star
                if is_canonical:
                    desc = f"⭐ {desc}"

                f.write(
                    f"| {desc} | `{file_path}` | {line} | {task_id} | {task_type} | {priority} | {agent} | {status} |\n"
                )
            f.write("\n")


def auto_fix_duplicates(
    duplicates: Dict[str, List[Tuple[str, str, int, Dict[str, Any]]]],
    dry_run: bool = False,
) -> None:
    """Attempt to automatically fix duplicate tasks by removing duplicates."""
    fixed_files: Set[Path] = set()

    for normalized_desc, entries in duplicates.items():
        canonical = determine_canonical_task(entries)
        canonical_desc, canonical_file, _, _ = canonical

        for desc, file_path, line, _ in entries:
            if (desc, file_path, line) == (canonical_desc, canonical_file, line):
                continue

            file_path = Path(PROJECT_ROOT) / file_path
            if file_path not in fixed_files:
                if not dry_run:
                    backup_file(file_path)
                fixed_files.add(file_path)

            if file_path.suffix == ".json":
                fix_json_duplicate(file_path, desc, line, dry_run)
            elif file_path.suffix == ".md":
                fix_md_duplicate(file_path, desc, line, dry_run)


def fix_json_duplicate(
    file_path: Path, desc: str, line: int, dry_run: bool = False
) -> None:
    """Remove a duplicate task from a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            data = json.loads(content)

        if isinstance(data, list):
            data = [
                task for task in data if task.get("description", "").strip() != desc
            ]
        elif isinstance(data, dict) and "tasks" in data:
            data["tasks"] = [
                task
                for task in data["tasks"]
                if task.get("description", "").strip() != desc
            ]

        if not dry_run:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Removed duplicate from {file_path}")
        else:
            logger.info(f"[DRY RUN] Would remove duplicate from {file_path}")

    except Exception as e:
        logger.error(f"Failed to fix duplicate in {file_path}: {e}")


def fix_md_duplicate(
    file_path: Path, desc: str, line: int, dry_run: bool = False
) -> None:
    """Remove a duplicate task from a Markdown file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Find and remove the line containing the duplicate task
        pattern = re.compile(
            r"^\s*[*\-+]\s+\[[\sx\-~*]?\]\s*" + re.escape(desc) + r"\s*$"
        )
        new_lines = [line for line in lines if not pattern.match(line)]

        if not dry_run:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            logger.info(f"Removed duplicate from {file_path}")
        else:
            logger.info(f"[DRY RUN] Would remove duplicate from {file_path}")

    except Exception as e:
        logger.error(f"Failed to fix duplicate in {file_path}: {e}")


def repair_json_content(content: str) -> str:
    """Attempt to repair common JSON issues in the content.

    Args:
        content: The JSON content to repair

    Returns:
        The repaired JSON content
    """
    # Remove invalid control characters
    content = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", content)

    # Remove trailing commas in arrays and objects
    content = re.sub(r",\s*]", "]", content)
    content = re.sub(r",\s*}", "}", content)

    # Remove comments
    content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    # Fix missing quotes around property names
    content = re.sub(r"([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', content)

    # Fix single quotes to double quotes
    content = re.sub(r"'([^']*)'", r'"\1"', content)

    # Fix missing commas between array/object elements
    content = re.sub(r'"\s*}\s*"', '", "', content)
    content = re.sub(r'"\s*]\s*"', '", "', content)

    # Fix missing commas between properties
    content = re.sub(r'"\s*"\s*:', '", ":', content)

    # Fix missing commas between values
    content = re.sub(r'"\s*"\s*}', '", "}', content)
    content = re.sub(r'"\s*"\s*]', '", "]', content)

    # Fix missing commas between objects
    content = re.sub(r"}\s*{", "}, {", content)

    # Fix missing commas between arrays
    content = re.sub(r"]\s*\[", "], [", content)

    return content


def main() -> int:
    """Main entry point for the script."""
    try:
        # Ensure report directory exists
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

        # Find duplicate tasks
        duplicates = find_duplicate_tasks()

        if not duplicates:
            logger.info("No duplicate tasks found.")
            return 0

        # Generate report
        generate_markdown_report(duplicates)

        # Print summary
        logger.info(f"Found {len(duplicates)} groups of duplicate tasks:")
        for normalized_desc, entries in sorted(
            duplicates.items(), key=lambda x: x[1][0][0]
        ):
            logger.info(f"\nDuplicate group: {normalized_desc}")
            for desc, file_path, line, metadata in entries:
                logger.info(f"  - {file_path} (line {line}): {desc}")

        return 0

    except Exception as e:
        logger.error(f"Error running duplicate task finder: {e}")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
