#!/usr/bin/env python3
"""
Script to clean up identified duplicate directories in the codebase.
This script will:
1. Clean up recursive backup directories
2. Consolidate duplicate test directories
3. Clean up duplicate log directories
4. Remove redundant task migration backups
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Set
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
log = logging.getLogger(__name__)

class DuplicateDirectoryCleaner:
    """Handles cleaning up duplicate directories safely."""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.backup_dir = workspace_root / "runtime" / "cleanup_backups" / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def backup_directory(self, dir_path: Path) -> Path:
        """Create a backup of a directory before removing it."""
        try:
            relative_path = dir_path.relative_to(self.workspace_root)
            backup_path = self.backup_dir / relative_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            if dir_path.exists():
                shutil.copytree(dir_path, backup_path)
                log.info(f"Backed up {dir_path} to {backup_path}")
            return backup_path
        except Exception as e:
            log.error(f"Failed to backup {dir_path}: {e}")
            raise
            
    def remove_directory(self, dir_path: Path) -> bool:
        """Safely remove a directory after backing it up."""
        try:
            if not dir_path.exists():
                return True
                
            # Create backup first
            self.backup_directory(dir_path)
            
            # Remove directory
            shutil.rmtree(dir_path)
            log.info(f"Removed directory: {dir_path}")
            return True
        except Exception as e:
            log.error(f"Failed to remove {dir_path}: {e}")
            return False
            
    def cleanup_recursive_backups(self) -> None:
        """Clean up deeply nested backup directories."""
        backup_root = self.workspace_root / "runtime" / "backups"
        if not backup_root.exists():
            return
            
        # Find all cleanup_backup directories
        for backup_dir in backup_root.rglob("cleanup_backup"):
            if len(str(backup_dir.relative_to(backup_root)).split(os.sep)) > 3:
                log.info(f"Removing deeply nested backup: {backup_dir}")
                self.remove_directory(backup_dir)
                
    def consolidate_test_directories(self) -> None:
        """Consolidate duplicate test directories."""
        src_tests = self.workspace_root / "src" / "tests"
        root_tests = self.workspace_root / "tests"
        
        if src_tests.exists() and root_tests.exists():
            # Merge src/tests into tests/
            for item in src_tests.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(src_tests)
                    target = root_tests / rel_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)
                    log.info(f"Copied {item} to {target}")
                    
            # Remove src/tests after successful merge
            self.remove_directory(src_tests)
            
    def cleanup_empathy_logs(self) -> None:
        """Clean up duplicate empathy log directories."""
        empathy_logs = self.workspace_root / "runtime" / "logs" / "empathy"
        if not empathy_logs.exists():
            return
            
        # Keep Agent-3 logs, remove others if identical
        agent3_dir = empathy_logs / "Agent-3"
        if not agent3_dir.exists():
            return
            
        for agent_dir in empathy_logs.iterdir():
            if agent_dir.name != "Agent-3" and agent_dir.is_dir():
                # Check if directory structure is identical
                if self._are_dirs_identical(agent3_dir, agent_dir):
                    self.remove_directory(agent_dir)
                    
    def cleanup_task_migration_backups(self) -> None:
        """Clean up redundant task migration backups."""
        backup_dir = self.workspace_root / "runtime" / "task_migration_backups"
        if not backup_dir.exists():
            return
            
        # Keep only the latest backup for each date
        backups_by_date = {}
        for backup in backup_dir.iterdir():
            if backup.is_dir() and backup.name.startswith("backup_"):
                date = backup.name.split("_")[1]  # Extract YYYYMMDD
                if date not in backups_by_date or backup.name > backups_by_date[date].name:
                    backups_by_date[date] = backup
                    
        # Remove all except the latest backup for each date
        for backup in backup_dir.iterdir():
            if backup.is_dir() and backup.name.startswith("backup_"):
                date = backup.name.split("_")[1]
                if backup != backups_by_date[date]:
                    self.remove_directory(backup)
                    
    def _are_dirs_identical(self, dir1: Path, dir2: Path) -> bool:
        """Check if two directories have identical structure and file contents."""
        try:
            dir1_files = set(f.relative_to(dir1) for f in dir1.rglob("*") if f.is_file())
            dir2_files = set(f.relative_to(dir2) for f in dir2.rglob("*") if f.is_file())
            
            if dir1_files != dir2_files:
                return False
                
            for rel_path in dir1_files:
                file1 = dir1 / rel_path
                file2 = dir2 / rel_path
                if not self._are_files_identical(file1, file2):
                    return False
                    
            return True
        except Exception:
            return False
            
    def _are_files_identical(self, file1: Path, file2: Path) -> bool:
        """Check if two files have identical contents."""
        try:
            return file1.read_bytes() == file2.read_bytes()
        except Exception:
            return False
            
def main():
    """Main entry point."""
    workspace_root = Path(__file__).resolve().parent.parent
    cleaner = DuplicateDirectoryCleaner(workspace_root)
    
    try:
        # Clean up recursive backup directories
        log.info("Cleaning up recursive backup directories...")
        cleaner.cleanup_recursive_backups()
        
        # Consolidate test directories
        log.info("Consolidating test directories...")
        cleaner.consolidate_test_directories()
        
        # Clean up empathy logs
        log.info("Cleaning up empathy log directories...")
        cleaner.cleanup_empathy_logs()
        
        # Clean up task migration backups
        log.info("Cleaning up task migration backups...")
        cleaner.cleanup_task_migration_backups()
        
        log.info("Cleanup completed successfully!")
        
    except Exception as e:
        log.error(f"Cleanup failed: {e}")
        raise
        
if __name__ == "__main__":
    main() 