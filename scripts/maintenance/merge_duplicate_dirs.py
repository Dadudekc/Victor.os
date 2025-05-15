#!/usr/bin/env python3
"""
Script to find and merge duplicate directories in the workspace.
Identifies duplicates based on content hash and provides options for merging.
"""

import os
import sys
import hashlib
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DuplicateDirectoryMerger:
    def __init__(self, root_dir: Path, exclude_patterns: Set[str] = None):
        self.root_dir = root_dir
        self.exclude_patterns = exclude_patterns or {
            '__pycache__', 
            'venv', 
            '.git', 
            'node_modules',
            '.pytest_cache'
        }
        self.dir_hashes: Dict[str, List[Path]] = defaultdict(list)
        
    def compute_dir_hash(self, dir_path: Path) -> str:
        """
        Compute a hash for the directory based on its contents.
        Includes file names, sizes, and content hashes.
        """
        if not dir_path.is_dir():
            return ""
            
        hasher = hashlib.sha256()
        
        try:
            # Get all files and subdirs, sorted for consistency
            all_items = sorted(dir_path.rglob('*'))
            
            for item in all_items:
                if any(pat in str(item) for pat in self.exclude_patterns):
                    continue
                    
                rel_path = str(item.relative_to(dir_path))
                hasher.update(rel_path.encode())
                
                if item.is_file():
                    # Update with file size and content hash
                    hasher.update(str(item.stat().st_size).encode())
                    with open(item, 'rb') as f:
                        while chunk := f.read(8192):
                            hasher.update(chunk)
                            
        except (PermissionError, OSError) as e:
            logger.warning(f"Error accessing {dir_path}: {e}")
            return ""
            
        return hasher.hexdigest()
        
    def find_duplicates(self) -> None:
        """
        Find all duplicate directories under root_dir.
        """
        logger.info(f"Scanning for duplicate directories in {self.root_dir}")
        
        # Get all directories
        all_dirs = [
            d for d in self.root_dir.rglob('*') 
            if d.is_dir() and not any(pat in str(d) for pat in self.exclude_patterns)
        ]
        
        total_dirs = len(all_dirs)
        logger.info(f"Found {total_dirs} directories to analyze")
        
        # Compute hashes for each directory
        for idx, dir_path in enumerate(all_dirs, 1):
            if idx % 100 == 0:
                logger.info(f"Progress: {idx}/{total_dirs} directories processed")
                
            dir_hash = self.compute_dir_hash(dir_path)
            if dir_hash:
                self.dir_hashes[dir_hash].append(dir_path)
                
    def get_duplicate_groups(self) -> Dict[str, List[Path]]:
        """
        Return only the groups that have duplicates.
        """
        return {
            h: paths for h, paths in self.dir_hashes.items() 
            if len(paths) > 1
        }
        
    def merge_directories(self, source: Path, target: Path) -> bool:
        """
        Merge source directory into target directory.
        Returns True if successful.
        """
        try:
            # Create target if it doesn't exist
            target.mkdir(parents=True, exist_ok=True)
            
            # Copy all contents from source to target
            for item in source.rglob('*'):
                if any(pat in str(item) for pat in self.exclude_patterns):
                    continue
                    
                relative_path = item.relative_to(source)
                target_path = target / relative_path
                
                if item.is_file():
                    if not target_path.exists():
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, target_path)
                    else:
                        logger.info(f"File already exists: {target_path}")
                elif item.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
            
            # Remove source directory after successful merge
            shutil.rmtree(source)
            logger.info(f"Successfully merged {source} into {target}")
            return True
            
        except Exception as e:
            logger.error(f"Error merging {source} into {target}: {e}")
            return False
            
    def generate_report(self, duplicates: Dict[str, List[Path]]) -> str:
        """
        Generate a detailed report of duplicate directories.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.root_dir / f"duplicate_dirs_report_{timestamp}.json"
        
        report_data = {
            "timestamp": timestamp,
            "total_groups": len(duplicates),
            "total_duplicates": sum(len(paths) - 1 for paths in duplicates.values()),
            "duplicate_groups": {
                h[:8]: [str(p) for p in paths]
                for h, paths in duplicates.items()
            }
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        return str(report_file)

def main():
    # Get workspace root
    workspace_root = Path(os.getcwd())
    
    # Initialize merger
    merger = DuplicateDirectoryMerger(workspace_root)
    
    # Find duplicates
    merger.find_duplicates()
    duplicates = merger.get_duplicate_groups()
    
    if not duplicates:
        logger.info("No duplicate directories found.")
        return 0
        
    # Generate and save report
    report_path = merger.generate_report(duplicates)
    logger.info(f"Duplicate directory report saved to: {report_path}")
    
    # Print summary
    logger.info("\nDuplicate Directory Groups:")
    for hash_val, paths in duplicates.items():
        logger.info(f"\nGroup (hash: {hash_val[:8]}):")
        for path in paths:
            logger.info(f"  - {path}")
    
    # Ask for merge confirmation
    response = input("\nWould you like to merge these duplicate directories? (yes/no): ")
    if response.lower() != 'yes':
        logger.info("Merge operation cancelled.")
        return 0
    
    # Perform merges
    success_count = 0
    total_merges = sum(len(paths) - 1 for paths in duplicates.values())
    
    for paths in duplicates.values():
        # Use the shortest path as the target
        target = min(paths, key=lambda p: len(str(p)))
        sources = [p for p in paths if p != target]
        
        logger.info(f"\nMerging into target: {target}")
        for source in sources:
            if merger.merge_directories(source, target):
                success_count += 1
                
    logger.info(f"\nMerge operations completed: {success_count}/{total_merges} successful")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 