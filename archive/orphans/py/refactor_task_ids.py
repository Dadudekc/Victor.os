"""Task ID Refactoring Tool: Updates legacy task IDs to new consolidated format.

This script scans the codebase for old task ID references and updates them to the new
consolidated format. It maintains a mapping of old to new IDs and updates all references
in code, documentation, and logs.
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Get the absolute path of the script's directory
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.absolute()

# Configure logging with more detailed format
log_file = PROJECT_ROOT / "task_id_refactor.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(str(log_file))],
)

# Task ID mapping from old to new format
TASK_ID_MAPPING = {
    # CLI Tasks
    "REFACTOR-PBM-CLI-001": "CLI-001",
    # Core Tasks
    "DIAGNOSE-WORKING-TASKS-LOCK-001": "CORE-001",
    "CAPTAIN8-PRIORITY1-PBM-COMPLETE-API-001": "CORE-002",
    # Agent Tasks
    "AGENT-IDENTITY-SKILLS-001": "AGENT-001",
    "AGENT-EVENT-HANDLING-001": "AGENT-002",
    "AGENT-DOCUMENTATION-001": "AGENT-003",
    # Testing Tasks
    "TEST-AGENT-FRAMEWORK-001": "TEST-001",
    "FLAKE8-FIXES-001": "TEST-002",
    # Task Management
    "TASK-REVIEW-PROTOCOL-001": "TASK-001",
}

# File patterns to scan
INCLUDE_PATTERNS = ["*.py", "*.md", "*.json", "*.yaml", "*.yml"]

# Directories to exclude
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    "env",
    ".pytest_cache",
    "build",
    "dist",
}


def find_files_to_scan(root_dir: Path) -> List[Path]:
    """Find all files that need to be scanned for task ID references."""
    files_to_scan = []

    try:
        for pattern in INCLUDE_PATTERNS:
            logging.info(f"Scanning for pattern: {pattern}")
            for file_path in root_dir.rglob(pattern):
                # Skip excluded directories
                if any(excluded in file_path.parts for excluded in EXCLUDE_DIRS):
                    logging.debug(f"Skipping excluded directory: {file_path}")
                    continue
                files_to_scan.append(file_path)
                logging.debug(f"Added file to scan: {file_path}")
    except Exception as e:
        logging.error(f"Error scanning files: {e}")
        raise

    return files_to_scan


def update_task_references(
    file_path: Path, task_mapping: Dict[str, str]
) -> Tuple[int, Set[str]]:
    """Update task ID references in a single file.

    Returns:
        Tuple of (number of replacements made, set of old task IDs found)
    """
    if not file_path.exists():
        logging.warning(f"File does not exist: {file_path}")
        return 0, set()

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logging.warning(f"Skipping binary file: {file_path}")
        return 0, set()
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return 0, set()

    replacements = 0
    found_ids = set()

    # Find all potential task ID references
    for old_id, new_id in task_mapping.items():
        # Match task IDs in various formats
        patterns = [
            rf"\b{old_id}\b",  # Exact match
            rf'"{old_id}"',  # In quotes
            rf"'{old_id}'",  # In single quotes
            rf"\[{old_id}\]",  # In brackets
            rf"\({old_id}\)",  # In parentheses
        ]

        for pattern in patterns:
            try:
                if re.search(pattern, content):
                    found_ids.add(old_id)
                    # Replace with new ID, maintaining the surrounding format
                    content = re.sub(
                        pattern, lambda m: m.group(0).replace(old_id, new_id), content
                    )
                    replacements += 1
                    logging.debug(
                        f"Found and replaced {old_id} with {new_id} in {file_path}"
                    )
            except Exception as e:
                logging.error(f"Error processing pattern {pattern} in {file_path}: {e}")

    if replacements > 0:
        try:
            # Create backup
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            file_path.rename(backup_path)
            logging.info(f"Created backup: {backup_path}")

            # Write updated content
            file_path.write_text(content, encoding="utf-8")
            logging.info(f"Updated {replacements} references in {file_path}")
        except Exception as e:
            logging.error(f"Error updating file {file_path}: {e}")
            # Try to restore from backup if it exists
            if backup_path.exists():
                try:
                    backup_path.rename(file_path)
                    logging.info(f"Restored from backup: {file_path}")
                except Exception as restore_error:
                    logging.error(f"Error restoring from backup: {restore_error}")

    return replacements, found_ids


def main():
    """Main function to orchestrate the task ID refactoring process."""
    try:
        logging.info(f"Starting task ID refactoring in {PROJECT_ROOT}")

        files_to_scan = find_files_to_scan(PROJECT_ROOT)
        logging.info(f"Found {len(files_to_scan)} files to scan")

        total_replacements = 0
        all_found_ids = set()

        for file_path in files_to_scan:
            try:
                replacements, found_ids = update_task_references(
                    file_path, TASK_ID_MAPPING
                )
                total_replacements += replacements
                all_found_ids.update(found_ids)
            except Exception as e:
                logging.error(f"Error processing file {file_path}: {e}")

        # Generate report
        report = {
            "total_files_scanned": len(files_to_scan),
            "total_replacements": total_replacements,
            "old_task_ids_found": sorted(list(all_found_ids)),
            "mapping_used": TASK_ID_MAPPING,
            "timestamp": "2024-03-19T00:00:00Z",
        }

        # Save report
        report_path = (
            PROJECT_ROOT / "runtime" / "task_board" / "task_id_refactor_report.json"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            logging.info(f"Refactoring complete. Report saved to {report_path}")
        except Exception as e:
            logging.error(f"Error saving report to {report_path}: {e}")
            # Try alternate location
            alt_report_path = PROJECT_ROOT / "task_id_refactor_report.json"
            try:
                with open(alt_report_path, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2)
                logging.info(f"Report saved to alternate location: {alt_report_path}")
            except Exception as alt_error:
                logging.error(f"Error saving report to alternate location: {alt_error}")

        logging.info(f"Total replacements: {total_replacements}")
        logging.info(f"Found old task IDs: {', '.join(sorted(all_found_ids))}")

    except Exception as e:
        logging.error(f"Fatal error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
