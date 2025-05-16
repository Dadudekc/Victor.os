#!/usr/bin/env python3
"""
Safe backup utility that prevents recursive backup structures.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Set, List, Optional

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class SafeBackup:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.backup_root = workspace_root / 'runtime' / 'cleanup_backups'
        self.excluded_patterns = {
            'backup_', 'cleanup_backup', 'backups',
            '.git', '__pycache__', 'node_modules'
        }
        
    def _is_excluded(self, path: Path) -> bool:
        """Check if a path should be excluded from backup."""
        path_str = str(path)
        return any(pattern in path_str for pattern in self.excluded_patterns)
        
    def _get_backup_name(self) -> str:
        """Generate a timestamp-based backup name."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f'backup_{timestamp}'
        
    def create_backup(self, source_dir: Optional[Path] = None) -> Path:
        """Create a backup while preventing recursive structures."""
        if source_dir is None:
            source_dir = self.workspace_root
            
        # Create backup directory
        backup_name = self._get_backup_name()
        backup_dir = self.backup_root / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy files while excluding problematic patterns
        def _copy_filtered(src: Path, dst: Path):
            if self._is_excluded(src):
                logger.debug(f"Skipping excluded path: {src}")
                return
                
            if src.is_file():
                shutil.copy2(src, dst)
            elif src.is_dir():
                dst.mkdir(exist_ok=True)
                for item in src.iterdir():
                    _copy_filtered(item, dst / item.name)
                    
        logger.info(f"Creating backup in: {backup_dir}")
        _copy_filtered(source_dir, backup_dir)
        
        # Cleanup old backups (keep last 5)
        self._cleanup_old_backups(keep=5)
        
        return backup_dir
        
    def _cleanup_old_backups(self, keep: int = 5):
        """Remove old backups, keeping the specified number of most recent ones."""
        if not self.backup_root.exists():
            return
            
        backups = []
        for backup_dir in self.backup_root.iterdir():
            if backup_dir.is_dir() and backup_dir.name.startswith('backup_'):
                try:
                    timestamp = datetime.strptime(
                        backup_dir.name, 'backup_%Y%m%d_%H%M%S'
                    )
                    backups.append((timestamp, backup_dir))
                except ValueError:
                    continue
                    
        # Sort by timestamp (newest first) and remove old backups
        backups.sort(reverse=True)
        for _, backup_dir in backups[keep:]:
            logger.info(f"Removing old backup: {backup_dir}")
            shutil.rmtree(backup_dir)

def main():
    workspace_root = Path(__file__).resolve().parent.parent
    backup_tool = SafeBackup(workspace_root)
    
    # Create a new backup
    backup_dir = backup_tool.create_backup()
    logger.info(f"✅ Backup created successfully at: {backup_dir}")

if __name__ == '__main__':
    main() 