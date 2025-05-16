#!/usr/bin/env python3
"""
Direct Cleanup Script
--------------------
Performs direct cleanup operations without requiring analysis files:
1. Removes empty directories
2. Cleans up temporary files
3. Identifies and handles duplicate files
4. Consolidates orphaned files
"""

import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

# Setup logging
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = WORKSPACE_ROOT / "runtime" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
CLEANUP_LOG = LOG_DIR / "cleanup_log.json"

# File patterns to ignore
IGNORE_PATTERNS = {
    ".git", "__pycache__", ".pytest_cache", "node_modules",
    "venv", "env", ".venv", ".env", ".idea", ".vscode"
}

def load_cleanup_log() -> List[Dict]:
    """Load the existing cleanup log or create a new one."""
    if CLEANUP_LOG.exists():
        with open(CLEANUP_LOG, "r") as f:
            return json.load(f)
    return []

def save_cleanup_log(log_entries: List[Dict]):
    """Save entries to the cleanup log."""
    with open(CLEANUP_LOG, "w") as f:
        json.dump(log_entries, f, indent=2)

def log_action(action: str, path: str, reason: str):
    """Log a cleanup action."""
    log_entries = load_cleanup_log()
    log_entries.append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "path": str(path),
        "reason": reason
    })
    save_cleanup_log(log_entries)
    print(f"{action}: {path} - {reason}")

def should_ignore(path: Path) -> bool:
    """Check if a path should be ignored."""
    return any(ignore in path.parts for ignore in IGNORE_PATTERNS)

def get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def find_duplicate_files() -> Dict[str, List[Path]]:
    """Find duplicate files based on content hash."""
    hash_map: Dict[str, List[Path]] = {}
    
    for path in WORKSPACE_ROOT.rglob("*"):
        if not path.is_file() or should_ignore(path):
            continue
            
        try:
            file_hash = get_file_hash(path)
            if file_hash not in hash_map:
                hash_map[file_hash] = []
            hash_map[file_hash].append(path)
        except Exception as e:
            print(f"Error processing {path}: {e}")
            
    return {h: paths for h, paths in hash_map.items() if len(paths) > 1}

def remove_empty_dirs():
    """Remove empty directories."""
    for dirpath, dirnames, filenames in os.walk(WORKSPACE_ROOT, topdown=False):
        current_dir = Path(dirpath)
        
        if should_ignore(current_dir):
            continue
            
        if not os.listdir(dirpath):
            try:
                os.rmdir(dirpath)
                log_action("remove_dir", dirpath, "Empty directory")
            except Exception as e:
                print(f"Error removing directory {dirpath}: {e}")

def clean_temp_files():
    """Clean up temporary files."""
    temp_patterns = ["*.tmp", "*.temp", "*.pyc", "*.pyo", "*.pyd", "*.log", 
                    "*.bak", "*.swp", "*.swo", "*~"]
                    
    for pattern in temp_patterns:
        for path in WORKSPACE_ROOT.rglob(pattern):
            if should_ignore(path):
                continue
                
            try:
                path.unlink()
                log_action("remove_file", path, f"Temporary file ({pattern})")
            except Exception as e:
                print(f"Error removing temp file {path}: {e}")

def handle_duplicates():
    """Handle duplicate files."""
    duplicates = find_duplicate_files()
    
    for file_hash, paths in duplicates.items():
        # Sort by path length (shorter paths are likely more "canonical")
        paths.sort(key=lambda p: len(str(p)))
        
        # Keep the first one (shortest path)
        keeper = paths[0]
        
        # Move others to archive
        for dupe in paths[1:]:
            try:
                archive_path = WORKSPACE_ROOT / "archive" / "duplicates" / dupe.name
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dupe), str(archive_path))
                log_action("archive_duplicate", dupe, f"Duplicate of {keeper}")
            except Exception as e:
                print(f"Error handling duplicate {dupe}: {e}")

def analyze_orphaned_files():
    """Analyze orphaned files and generate a report."""
    orphans_dir = WORKSPACE_ROOT / "archive" / "orphans"
    if not orphans_dir.exists():
        print("No orphaned files directory found.")
        return
        
    # Initialize counters
    stats = {
        "total_files": 0,
        "by_extension": {},
        "by_category": {
            "python": 0,
            "javascript": 0,
            "typescript": 0,
            "config": 0,
            "data": 0,
            "docs": 0,
            "tests": 0,
            "other": 0
        },
        "empty_files": 0,
        "large_files": 0  # >1MB
    }
    
    # Analyze all files
    print("\nAnalyzing orphaned files...")
    for path in orphans_dir.rglob("*"):
        if not path.is_file():
            continue
            
        stats["total_files"] += 1
        
        # Count by extension
        ext = path.suffix
        stats["by_extension"][ext] = stats["by_extension"].get(ext, 0) + 1
        
        # Categorize files
        if ext in [".py"]:
            stats["by_category"]["python"] += 1
        elif ext in [".js", ".jsx"]:
            stats["by_category"]["javascript"] += 1
        elif ext in [".ts", ".tsx"]:
            stats["by_category"]["typescript"] += 1
        elif ext in [".json", ".yaml", ".yml", ".toml"]:
            stats["by_category"]["config"] += 1
        elif ext in [".csv", ".xlsx", ".db"]:
            stats["by_category"]["data"] += 1
        elif ext in [".md", ".rst", ".txt"]:
            stats["by_category"]["docs"] += 1
        elif any(path.name.endswith(test_ext) for test_ext in [".test.py", ".test.js", ".test.ts", ".spec.py", ".spec.js", ".spec.ts"]):
            stats["by_category"]["tests"] += 1
        else:
            stats["by_category"]["other"] += 1
            
        # Check file size
        size = path.stat().st_size
        if size == 0:
            stats["empty_files"] += 1
        elif size > 1_000_000:  # 1MB
            stats["large_files"] += 1
            
    # Print report
    print("\nOrphaned Files Analysis:")
    print(f"Total files: {stats['total_files']}")
    print("\nBy Category:")
    for category, count in stats["by_category"].items():
        print(f"  {category}: {count}")
    print("\nBy Extension:")
    for ext, count in sorted(stats["by_extension"].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {ext or 'no extension'}: {count}")
    print(f"\nEmpty files: {stats['empty_files']}")
    print(f"Large files (>1MB): {stats['large_files']}")
    
    return stats

def handle_orphaned_files():
    """Handle files in the archive/orphans directory."""
    orphans_dir = WORKSPACE_ROOT / "archive" / "orphans"
    if not orphans_dir.exists():
        return
        
    # Create consolidated directories by type
    consolidated = {
        "python": orphans_dir / "consolidated" / "python",
        "javascript": orphans_dir / "consolidated" / "javascript",
        "typescript": orphans_dir / "consolidated" / "typescript",
        "config": orphans_dir / "consolidated" / "config",
        "data": orphans_dir / "consolidated" / "data",
        "docs": orphans_dir / "consolidated" / "docs",
        "tests": orphans_dir / "consolidated" / "tests",
        "other": orphans_dir / "consolidated" / "other"
    }
    
    for dir_path in consolidated.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Map file extensions to consolidated directories
    ext_mapping = {
        ".py": consolidated["python"],
        ".js": consolidated["javascript"],
        ".ts": consolidated["typescript"],
        ".tsx": consolidated["typescript"],
        ".jsx": consolidated["javascript"],
        ".json": consolidated["config"],
        ".yaml": consolidated["config"],
        ".yml": consolidated["config"],
        ".toml": consolidated["config"],
        ".md": consolidated["docs"],
        ".rst": consolidated["docs"],
        ".txt": consolidated["docs"],
        ".csv": consolidated["data"],
        ".xlsx": consolidated["data"],
        ".db": consolidated["data"],
        ".test.py": consolidated["tests"],
        ".test.js": consolidated["tests"],
        ".test.ts": consolidated["tests"],
        ".spec.py": consolidated["tests"],
        ".spec.js": consolidated["tests"],
        ".spec.ts": consolidated["tests"]
    }
    
    # Process all files in orphans directory
    for path in orphans_dir.rglob("*"):
        if not path.is_file() or path.parent.name == "consolidated":
            continue
            
        # Determine target directory
        target_dir = None
        if path.suffix in ext_mapping:
            target_dir = ext_mapping[path.suffix]
        elif any(path.name.endswith(test_ext) for test_ext in [".test.py", ".test.js", ".test.ts", ".spec.py", ".spec.js", ".spec.ts"]):
            target_dir = consolidated["tests"]
        else:
            target_dir = consolidated["other"]
            
        try:
            # Create unique filename to avoid collisions
            target_path = target_dir / f"{path.stem}_{path.parent.name}{path.suffix}"
            counter = 1
            while target_path.exists():
                target_path = target_dir / f"{path.stem}_{path.parent.name}_{counter}{path.suffix}"
                counter += 1
                
            # Move the file
            shutil.move(str(path), str(target_path))
            log_action("consolidate_orphan", path, f"Moved to {target_path.relative_to(orphans_dir)}")
        except Exception as e:
            print(f"Error consolidating orphaned file {path}: {e}")

def main():
    """Main cleanup process."""
    print("Starting direct cleanup process...")
    
    # Create archive directory if it doesn't exist
    archive_dir = WORKSPACE_ROOT / "archive"
    archive_dir.mkdir(exist_ok=True)
    
    # Run cleanup operations
    print("\n1. Cleaning temporary files...")
    clean_temp_files()
    
    print("\n2. Handling duplicate files...")
    handle_duplicates()
    
    print("\n3. Removing empty directories...")
    remove_empty_dirs()
    
    print("\n4. Analyzing orphaned files...")
    stats = analyze_orphaned_files()
    
    if stats and stats["total_files"] > 0:
        print("\n5. Consolidating orphaned files...")
        handle_orphaned_files()
    
    print("\nCleanup complete. Check runtime/logs/cleanup_log.json for details.")

if __name__ == "__main__":
    main() 