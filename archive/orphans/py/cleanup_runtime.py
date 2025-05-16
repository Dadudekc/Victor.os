#!/usr/bin/env python3
"""
Runtime Directory Cleanup Script

This script handles the cleanup and reorganization of the runtime directory
structure according to the cleanup plan.
"""

import json
import logging
import os
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Configure logging
log_dir = Path("runtime/logs/operations")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f'cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
)


class RuntimeCleanup:
    def __init__(self):
        self.runtime_dir = Path("runtime")
        self.backup_dir = (
            self.runtime_dir
            / "backups"
            / f'cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        )
        self.moves_log = []
        self.errors = []

    def create_backup(self):
        """Create a backup of the runtime directory."""
        logging.info(f"Creating backup in {self.backup_dir}")
        try:
            # Create backup directory if it doesn't exist
            self.backup_dir.parent.mkdir(parents=True, exist_ok=True)

            # Create backup
            shutil.copytree(
                self.runtime_dir,
                self.backup_dir,
                ignore=shutil.ignore_patterns("backups", "cleanup.log"),
            )
            logging.info("Backup created successfully")
            return True
        except Exception as e:
            error_msg = f"Failed to create backup: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            self.errors.append(error_msg)
            return False

    def create_new_structure(self):
        """Create the new directory structure."""
        new_dirs = [
            "tasks/board",
            "tasks/definitions",
            "tasks/temp",
            "logs/agents",
            "logs/tests",
            "logs/operations",
            "bridge/outbox",
            "bridge/analysis",
            "bridge/inbox",
        ]

        for dir_path in new_dirs:
            full_path = self.runtime_dir / dir_path
            try:
                full_path.mkdir(parents=True, exist_ok=True)
                logging.info(f"Created directory: {full_path}")
            except Exception as e:
                error_msg = f"Failed to create directory {full_path}: {str(e)}\n{traceback.format_exc()}"
                logging.error(error_msg)
                self.errors.append(error_msg)

    def move_files(self, source_pattern, target_dir, file_pattern="*"):
        """Move files from source to target directory."""
        source_dir = self.runtime_dir / source_pattern
        target_dir = self.runtime_dir / target_dir

        if not source_dir.exists():
            logging.warning(f"Source directory does not exist: {source_dir}")
            return

        # Create target directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)

        for file_path in source_dir.glob(file_pattern):
            if file_path.is_file():
                target_path = target_dir / file_path.name
                try:
                    # Handle file name conflicts
                    if target_path.exists():
                        base = target_path.stem
                        suffix = target_path.suffix
                        counter = 1
                        while target_path.exists():
                            target_path = target_dir / f"{base}_{counter}{suffix}"
                            counter += 1

                    shutil.move(str(file_path), str(target_path))
                    self.moves_log.append(
                        {
                            "source": str(file_path),
                            "target": str(target_path),
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    logging.info(f"Moved {file_path} to {target_path}")
                except Exception as e:
                    error_msg = f"Failed to move {file_path}: {str(e)}\n{traceback.format_exc()}"
                    logging.error(error_msg)
                    self.errors.append(error_msg)

    def consolidate_temp_dirs(self):
        """Consolidate all temp directories."""
        temp_dirs = ["temp", "temp_task_definitions", "temp_tasks", "temp_io_test"]

        for dir_name in temp_dirs:
            self.move_files(dir_name, "tasks/temp")

    def consolidate_task_dirs(self):
        """Consolidate task-related directories."""
        # Move task board files
        self.move_files("task_board", "tasks/board")

        # Move task definition files
        self.move_files("temp_task_definitions", "tasks/definitions")

        # Move task files
        self.move_files("tasks", "tasks/board")
        self.move_files("temp_tasks", "tasks/temp")

    def consolidate_log_dirs(self):
        """Consolidate log directories."""
        log_moves = {
            "logs": "logs/operations",
            "testlogs": "logs/tests",
            "agent_logs": "logs/agents",
            "operational_logs": "logs/operations",
        }

        for source, target in log_moves.items():
            self.move_files(source, target)

    def consolidate_bridge_dirs(self):
        """Consolidate bridge-related directories."""
        bridge_moves = {
            "bridge": "bridge/inbox",
            "bridge_outbox": "bridge/outbox",
            "bridge_analysis": "bridge/analysis",
        }

        for source, target in bridge_moves.items():
            self.move_files(source, target)

    def cleanup_empty_dirs(self):
        """Remove empty directories."""
        for root, dirs, files in os.walk(self.runtime_dir, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                try:
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        logging.info(f"Removed empty directory: {dir_path}")
                except Exception as e:
                    error_msg = f"Failed to remove directory {dir_path}: {str(e)}\n{traceback.format_exc()}"
                    logging.error(error_msg)
                    self.errors.append(error_msg)

    def save_moves_log(self):
        """Save the moves log to a JSON file."""
        log_file = self.runtime_dir / "cleanup_moves.json"
        try:
            with open(log_file, "w") as f:
                json.dump(
                    {
                        "moves": self.moves_log,
                        "errors": self.errors,
                        "timestamp": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                )
            logging.info(f"Saved moves log to {log_file}")
        except Exception as e:
            error_msg = f"Failed to save moves log: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            self.errors.append(error_msg)

    def run(self):
        """Run the complete cleanup process."""
        logging.info("Starting runtime directory cleanup")

        # Create backup
        if not self.create_backup():
            logging.error("Aborting cleanup due to backup failure")
            return False

        try:
            # Create new structure
            self.create_new_structure()

            # Consolidate directories
            self.consolidate_temp_dirs()
            self.consolidate_task_dirs()
            self.consolidate_log_dirs()
            self.consolidate_bridge_dirs()

            # Cleanup
            self.cleanup_empty_dirs()

            # Save moves log
            self.save_moves_log()

            if self.errors:
                logging.warning(f"Cleanup completed with {len(self.errors)} errors")
                return False
            else:
                logging.info("Cleanup completed successfully")
                return True

        except Exception as e:
            error_msg = f"Cleanup failed: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            self.errors.append(error_msg)
            return False


if __name__ == "__main__":
    cleanup = RuntimeCleanup()
    success = cleanup.run()
    exit(0 if success else 1)
