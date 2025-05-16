#!/usr/bin/env python3
"""
DreamOS System Maintenance Tool: Duplicate Directory Cleanup

This module provides automated cleanup of duplicate and nested backup directories,
with safety measures and comprehensive logging.

Usage:
    from dreamos.tools.system_maintenance import cleanup_duplicates
    cleaner = cleanup_duplicates.DuplicatesCleaner(workspace_root)
    cleaner.run_cleanup()

Features:
- Recursive backup chain detection and cleanup
- Safe backup creation before deletions
- Detailed logging and reporting
- Configurable cleanup policies
"""

import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("runtime/logs/cleanup_duplicates.log"),
    ],
)


class DuplicatesCleaner:
    """Manages cleanup of duplicate directories with safety measures."""

    def __init__(self, workspace_root: Path):
        """Initialize the cleaner with workspace root path.

        Args:
            workspace_root (Path): Root directory of the workspace
        """
        self.workspace_root = workspace_root
        self.backup_dir = workspace_root / "runtime" / "backups"
        self.empathy_logs_dir = workspace_root / "runtime" / "logs" / "empathy"
        self.task_migration_dir = workspace_root / "runtime" / "task_migration_backups"
        self.test_dirs = [workspace_root / "src" / "tests", workspace_root / "tests"]

        # Stats for reporting
        self.stats = {
            "backup_chains_removed": 0,
            "space_freed": 0,
            "empathy_logs_consolidated": 0,
            "task_backups_rotated": 0,
            "errors": [],
        }

    def get_dir_size(self, path: Path) -> int:
        """Calculate total size of a directory in bytes."""
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = Path(dirpath) / f
                    if fp.is_file():
                        total += fp.stat().st_size
        except Exception as e:
            logging.warning(f"Error calculating size for {path}: {str(e)}")
        return total

    def backup_before_delete(self, path: Path) -> None:
        """Create a safety backup before deletion."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"pre_cleanup_{timestamp}"
            if not backup_path.exists():
                backup_path.mkdir(parents=True)

            # Create a minimal backup with just the most important files
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith((".json", ".yaml", ".md", ".log")):
                        src_file = Path(root) / file
                        rel_path = src_file.relative_to(path)
                        dst_file = backup_path / rel_path
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
            logging.info(f"Created safety backup at {backup_path}")
        except Exception as e:
            logging.error(f"Failed to create backup for {path}: {str(e)}")
            self.stats["errors"].append(f"Backup creation failed for {path}: {str(e)}")
            raise

    def cleanup_recursive_backups(self) -> None:
        """Clean up deeply nested backup chains while preserving important data."""
        try:
            cleanup_backup_dir = self.backup_dir / "cleanup_backup"
            if not cleanup_backup_dir.exists():
                logging.info("No recursive backups found")
                return

            logging.info("Starting recursive backup cleanup...")

            # Find all nested backup directories with improved detection
            nested_backups = []

            for root, dirs, _ in os.walk(cleanup_backup_dir):
                root_path = Path(root)
                path_str = str(root_path).lower()
                backup_count = path_str.count("backup")

                # Detect paths with multiple backup directories
                if backup_count > 1:
                    nested_backups.append((backup_count, root_path))
                    logging.info(
                        f"Found nested backup (depth {backup_count}): {root_path}"
                    )

            if not nested_backups:
                logging.info("No recursive backup chains found")
                return

            # Sort by backup depth (deepest first)
            nested_backups.sort(reverse=True)  # Will sort by backup_count

            for _, backup_path in nested_backups:
                if (
                    not backup_path.exists()
                ):  # Check again as parent deletion might have removed it
                    continue

                try:
                    # Only remove if it's a nested backup (parent directory exists)
                    parent_is_backup = any(
                        str(backup_path).startswith(str(other[1]))
                        for other in nested_backups
                        if backup_path != other[1]
                    )

                    if parent_is_backup:
                        size = self.get_dir_size(backup_path)
                        self.backup_before_delete(backup_path)
                        shutil.rmtree(backup_path)
                        self.stats["space_freed"] += size
                        self.stats["backup_chains_removed"] += 1
                        logging.info(f"Removed recursive backup: {backup_path}")
                    else:
                        logging.info(f"Keeping top-level backup: {backup_path}")

                except Exception as e:
                    error_msg = f"Failed to remove backup {backup_path}: {str(e)}"
                    logging.error(error_msg)
                    self.stats["errors"].append(error_msg)
                    continue

        except Exception as e:
            error_msg = f"Error during recursive backup cleanup: {str(e)}"
            logging.error(error_msg)
            self.stats["errors"].append(error_msg)

    def consolidate_empathy_logs(self) -> None:
        """Consolidate empathy logs from multiple agents."""
        if not self.empathy_logs_dir.exists():
            logging.info("No empathy logs directory found")
            return

        logging.info("Starting empathy logs consolidation...")

        # Create consolidated directory
        consolidated_dir = self.empathy_logs_dir / "consolidated"
        consolidated_dir.mkdir(exist_ok=True)

        # Process each agent's logs
        for agent_dir in self.empathy_logs_dir.glob("Agent-*"):
            if agent_dir.is_dir() and agent_dir.name != "consolidated":
                agent_num = agent_dir.name.split("-")[1]

                # Move logs to consolidated directory with agent prefix
                for log_file in agent_dir.glob("*.log"):
                    new_name = f"agent{agent_num}_{log_file.name}"
                    shutil.move(str(log_file), str(consolidated_dir / new_name))

                # Remove empty agent directory
                size = self.get_dir_size(agent_dir)
                shutil.rmtree(agent_dir)
                self.stats["space_freed"] += size
                self.stats["empathy_logs_consolidated"] += 1
                logging.info(f"Consolidated logs for {agent_dir.name}")

    def rotate_task_migration_backups(self, keep_last: int = 5) -> None:
        """Rotate task migration backups, keeping only the most recent ones."""
        if not self.task_migration_dir.exists():
            logging.info("No task migration backups directory found")
            return

        logging.info("Starting task migration backup rotation...")

        # Get all backup directories sorted by timestamp
        backup_dirs = []
        for backup_dir in self.task_migration_dir.glob("backup_*"):
            try:
                timestamp = datetime.strptime(backup_dir.name.split("_")[1], "%Y%m%d")
                backup_dirs.append((timestamp, backup_dir))
            except (IndexError, ValueError):
                logging.warning(f"Skipping invalid backup directory: {backup_dir}")
                continue

        # Sort by timestamp (newest first)
        backup_dirs.sort(reverse=True)

        # Remove older backups
        for _, backup_dir in backup_dirs[keep_last:]:
            size = self.get_dir_size(backup_dir)
            self.backup_before_delete(backup_dir)
            shutil.rmtree(backup_dir)
            self.stats["space_freed"] += size
            self.stats["task_backups_rotated"] += 1
            logging.info(f"Removed old task migration backup: {backup_dir}")

    def consolidate_test_directories(self) -> None:
        """Consolidate duplicate test directories."""
        if not all(d.exists() for d in self.test_dirs):
            logging.info("Test directories not found")
            return

        logging.info("Starting test directory consolidation...")

        # Use src/tests as the primary location
        primary_test_dir = self.test_dirs[0]
        secondary_test_dir = self.test_dirs[1]

        # Move unique tests from secondary to primary
        for root, dirs, files in os.walk(secondary_test_dir):
            rel_path = Path(root).relative_to(secondary_test_dir)
            primary_path = primary_test_dir / rel_path

            primary_path.mkdir(parents=True, exist_ok=True)

            for file in files:
                src_file = Path(root) / file
                dst_file = primary_path / file

                if not dst_file.exists():
                    shutil.move(str(src_file), str(dst_file))
                    logging.info(f"Moved test file: {src_file} -> {dst_file}")
                else:
                    # If file exists in both, keep newer version
                    if src_file.stat().st_mtime > dst_file.stat().st_mtime:
                        shutil.move(str(src_file), str(dst_file))
                        logging.info(f"Updated test file: {dst_file}")

        # Remove secondary test directory if empty
        if secondary_test_dir.exists():
            size = self.get_dir_size(secondary_test_dir)
            shutil.rmtree(secondary_test_dir)
            self.stats["space_freed"] += size
            logging.info("Removed secondary test directory")

    def run_cleanup(self) -> None:
        """Run all cleanup operations."""
        try:
            # Create backup directory if it doesn't exist
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # Run cleanup operations
            self.cleanup_recursive_backups()
            self.consolidate_empathy_logs()
            self.rotate_task_migration_backups()
            self.consolidate_test_directories()

            # Save cleanup report
            report = {
                "timestamp": datetime.now().isoformat(),
                "stats": {
                    **self.stats,
                    "space_freed_mb": round(
                        self.stats["space_freed"] / (1024 * 1024), 2
                    ),
                },
            }

            report_path = (
                self.workspace_root / "runtime" / "reports" / "cleanup_report.json"
            )
            report_path.parent.mkdir(parents=True, exist_ok=True)

            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)

            logging.info(f"Cleanup completed. Report saved to {report_path}")

        except Exception as e:
            logging.error(f"Error during cleanup: {str(e)}")
            raise


def main():
    """Main entry point when run as a script."""
    try:
        # Get workspace root
        workspace_root = Path.cwd()

        # Create and run cleaner
        cleaner = DuplicatesCleaner(workspace_root)
        cleaner.run_cleanup()

    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
