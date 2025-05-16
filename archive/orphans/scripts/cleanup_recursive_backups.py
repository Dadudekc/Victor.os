#!/usr/bin/env python3
"""
Cleanup script for recursive backup directories.
Identifies and removes recursive backup structures while preserving the most recent valid backups.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Set, List

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def is_recursive_backup(path: Path, seen_paths: Set[str] = None) -> bool:
    """Check if a path contains recursive backup structures."""
    if seen_paths is None:
        seen_paths = set()
    
    path_str = str(path.resolve())
    if path_str in seen_paths:
        return True
    seen_paths.add(path_str)
    
    if not path.is_dir():
        return False
        
    # Check for recursive patterns
    backup_indicators = {'backup', 'cleanup_backup', 'backups'}
    parts = set(p.lower() for p in path.parts)
    if len(parts & backup_indicators) > 1:
        return True
        
    # Check subdirectories
    for child in path.iterdir():
        if child.is_dir() and is_recursive_backup(child, seen_paths):
            return True
            
    return False

def find_recursive_backups(root: Path) -> List[Path]:
    """Find all recursive backup directories."""
    recursive_backups = []
    
    for path in root.glob('**/*'):
        if path.is_dir() and is_recursive_backup(path):
            recursive_backups.append(path)
            
    return recursive_backups

def cleanup_recursive_backups(workspace_root: Path) -> None:
    """Clean up recursive backup directories while preserving recent backups."""
    backup_root = workspace_root / 'runtime' / 'cleanup_backups'
    if not backup_root.exists():
        logger.info(f"No backup directory found at {backup_root}")
        return
        
    # Find recursive backups
    recursive_dirs = find_recursive_backups(backup_root)
    if not recursive_dirs:
        logger.info("No recursive backup directories found.")
        return
        
    logger.info(f"Found {len(recursive_dirs)} recursive backup directories:")
    for d in recursive_dirs:
        logger.info(f"  - {d}")
        
    # Create safety backup of the most recent backup
    most_recent = None
    most_recent_time = datetime.min
    for backup_dir in backup_root.iterdir():
        if backup_dir.is_dir() and backup_dir.name.startswith('backup_'):
            try:
                backup_time = datetime.strptime(backup_dir.name, 'backup_%Y%m%d_%H%M%S')
                if backup_time > most_recent_time:
                    most_recent = backup_dir
                    most_recent_time = backup_time
            except ValueError:
                continue
                
    if most_recent:
        safe_backup = backup_root.parent / 'latest_backup'
        if safe_backup.exists():
            shutil.rmtree(safe_backup)
        shutil.copytree(most_recent, safe_backup)
        logger.info(f"Created safety backup at {safe_backup}")
        
    # Remove recursive directories
    for d in recursive_dirs:
        try:
            shutil.rmtree(d)
            logger.info(f"Removed recursive directory: {d}")
        except Exception as e:
            logger.error(f"Error removing {d}: {e}")
            
    logger.info("Cleanup complete!")

if __name__ == '__main__':
    workspace_root = Path(__file__).resolve().parent.parent
    cleanup_recursive_backups(workspace_root) 