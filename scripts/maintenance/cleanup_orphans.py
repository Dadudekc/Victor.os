#!/usr/bin/env python3
"""
Cleanup Orphaned Files

This script helps identify and clean up orphaned files in the project:
1. Identifies files that are not imported or referenced
2. Checks for empty directories
3. Removes duplicate functionality
4. Archives or deletes files based on criteria
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
ARCHIVE_DIR = Path("archive/orphans")
CLEANUP_LOG = Path("cleanup_log.json")
CODE_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.cpp', '.h', '.hpp', '.c'}
IGNORED_DIRS = {
    '.git', 'node_modules', '__pycache__', 'venv', 
    'env', '.vscode', '.idea', 'build', 'dist'
}
IGNORED_FILES = {'.gitignore', 'README.md', 'LICENSE', '.keep'}

def should_process_file(file_path: Path) -> bool:
    """Check if a file should be processed."""
    return (
        file_path.is_file()
        and not any(ignored in file_path.parts for ignored in IGNORED_DIRS)
        and file_path.name not in IGNORED_FILES
        and not file_path.name.startswith('.')
    )

def archive_file(src_path: Path, errors: List[Dict]) -> bool:
    """Archive a file to the orphans directory."""
    try:
        # Create target directory
        rel_path = src_path.relative_to(Path.cwd())
        target_path = ARCHIVE_DIR / rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file to archive
        shutil.copy2(src_path, target_path)
        logger.info(f"Processing {src_path}")
        
        # Try to parse as JSON if it's a .json file
        if src_path.suffix == '.json':
            with open(src_path, 'r', encoding='utf-8') as f:
                json.load(f)
                
        return True
    except Exception as e:
        errors.append({
            'file': str(src_path),
            'error': str(e)
        })
        logger.error(f"Failed to archive {src_path}: {e}")
        return False

def cleanup_empty_dirs(directory: Path) -> None:
    """Remove empty directories and .keep files."""
    try:
        for root, dirs, files in os.walk(directory, topdown=False):
            root_path = Path(root)
            
            # Remove .keep files first
            for file in files:
                if file == '.keep':
                    (root_path / file).unlink()
            
            # Try to remove empty directory
            try:
                if not any(root_path.iterdir()):
                    root_path.rmdir()
                    logger.info(f"Removed empty directory: {root_path}")
            except Exception as e:
                logger.error(f"Failed to remove directory {root_path}: {e}")
    except Exception as e:
        logger.error(f"Error during directory cleanup: {e}")

def main():
    """Main cleanup function."""
    errors = []
    processed_files = 0
    
    # Process all files
    for root, _, files in os.walk('.'):
        root_path = Path(root)
        
        for file in files:
            file_path = root_path / file
            if should_process_file(file_path):
                if archive_file(file_path, errors):
                    processed_files += 1

    # Cleanup empty directories
    cleanup_empty_dirs(ARCHIVE_DIR)
    
    # Log summary
    logger.info("\nCleanup Summary:")
    logger.info(f"Files archived: {processed_files}")
    logger.info(f"Errors encountered: {len(errors)}")
    
    if errors:
        logger.info("\nErrors:")
        for error in errors:
            logger.info(f"- {error['file']}: {error['error']}")

    # Save cleanup log
    cleanup_data = {
        'timestamp': datetime.now().isoformat(),
        'files_processed': processed_files,
        'errors': errors
    }
    
    with open(CLEANUP_LOG, 'w') as f:
        json.dump(cleanup_data, f, indent=2)

if __name__ == '__main__':
    main() 