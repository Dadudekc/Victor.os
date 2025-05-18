#!/usr/bin/env python3
"""
clean_workspace.py - Dream.OS Workspace Cleanup Utility

Cleans temporary files, caches, and stale artifacts to maintain a clean project environment.
Logs space saved and timestamp for audit purposes.
"""

import os
import shutil
import json
from datetime import datetime
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Project root is the directory this script is run from
PROJECT_ROOT = Path.cwd()

# Directories to clean (standard cache directories)
CACHE_DIRS = [
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".dreamos_cache",
    "cookies",
    "htmlcov",
]

# Find all __pycache__ directories recursively
def find_pycache_dirs():
    pycache_dirs = []
    for root, dirs, _ in os.walk(PROJECT_ROOT):
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            pycache_dirs.append(pycache_path)
    return pycache_dirs

# Files to clean (large temporary outputs, reports, etc.)
TEMP_FILES = [
    "_dedup_scan_output.txt",
    "duplicate_report.json",
    "working_tasks_agent-*_claimed.json",
]

def get_size(path):
    """Get the size of a file or directory in bytes"""
    if os.path.isfile(path):
        return os.path.getsize(path)
    elif os.path.isdir(path):
        total_size = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):  # Skip if it's a symbolic link
                    total_size += os.path.getsize(fp)
        return total_size
    return 0

def format_bytes(size):
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def delete_path(path):
    """Delete a file or directory and return space saved"""
    try:
        size = get_size(path)
        if os.path.isfile(path):
            os.remove(path)
            logging.info(f"Deleted file: {path} ({format_bytes(size)})")
        elif os.path.isdir(path):
            shutil.rmtree(path)
            logging.info(f"Deleted directory: {path} ({format_bytes(size)})")
        return size
    except Exception as e:
        logging.error(f"Failed to delete {path}: {e}")
        return 0

def main():
    """Main cleanup function"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Starting workspace cleanup at {timestamp}")
    
    total_saved = 0
    cache_saved = 0
    files_saved = 0
    deleted_count = 0
    
    # Clean cache directories at the top level
    for cache_dir in CACHE_DIRS:
        path = PROJECT_ROOT / cache_dir
        if path.exists():
            size = delete_path(path)
            cache_saved += size
            deleted_count += 1
    
    # Clean all __pycache__ directories recursively
    for pycache_dir in find_pycache_dirs():
        size = delete_path(pycache_dir)
        cache_saved += size
        deleted_count += 1
    
    # Clean temporary files
    import glob
    for temp_file_pattern in TEMP_FILES:
        for path in glob.glob(str(PROJECT_ROOT / temp_file_pattern)):
            size = delete_path(path)
            files_saved += size
            deleted_count += 1
    
    # Calculate total saved
    total_saved = cache_saved + files_saved
    
    # Summary
    logging.info(f"Cleanup completed at {timestamp}")
    logging.info(f"Total items deleted: {deleted_count}")
    logging.info(f"Space saved from caches: {format_bytes(cache_saved)}")
    logging.info(f"Space saved from temporary files: {format_bytes(files_saved)}")
    logging.info(f"Total space saved: {format_bytes(total_saved)}")
    
    # Write report
    cleanup_report = {
        "timestamp": timestamp,
        "items_deleted": deleted_count,
        "space_saved": {
            "caches": format_bytes(cache_saved),
            "temp_files": format_bytes(files_saved),
            "total": format_bytes(total_saved)
        }
    }
    
    # Ensure reports directory exists
    reports_dir = PROJECT_ROOT / "runtime" / "reports"
    reports_dir.mkdir(exist_ok=True, parents=True)
    
    # Write cleanup report
    report_path = reports_dir / "cleanup_report.json"
    with open(report_path, 'w') as f:
        json.dump(cleanup_report, f, indent=2)
    
    logging.info(f"Cleanup report written to {report_path}")
    
    # Write to devlog
    try:
        devlog_dir = PROJECT_ROOT / "runtime" / "devlog"
        devlog_path = devlog_dir / "devlog.md"
        
        if devlog_dir.exists():
            with open(devlog_path, 'a') as f:
                f.write(f"\n### 🧹 [{datetime.now().strftime('%Y-%m-%d')}] Project Cleanup Completed\n")
                f.write(f"- Removed {deleted_count} cache directories and temporary files\n")
                f.write(f"- Freed {format_bytes(total_saved)} disk space\n")
                f.write(f"- `runtime/` directory preserved for agent continuity\n")
                f.write(f"- System ready for next episode deployment\n\n")
            logging.info(f"Cleanup logged to devlog at {devlog_path}")
    except Exception as e:
        logging.error(f"Failed to write to devlog: {e}")
    
    return total_saved

if __name__ == "__main__":
    main() 