"""
Script to update legacy file path references in code to match the new project structure.

This script scans Python files for references to episode task files and other
task JSONs that were relocated during the project reorganization.

Usage:
    python update_episode_references.py
"""

import os
import re
from pathlib import Path
import argparse
import sys

# Default source directory to scan
DEFAULT_ROOT_DIR = "src"

# Directories to exclude from scanning
EXCLUDED_DIRS = [
    "archive", 
    ".git", 
    ".venv", 
    "__pycache__", 
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov"
]

# Path updates to perform:
PATH_UPDATES = [
    # Episode task files
    {
        "pattern": r'["\']episodes/(parsed_episode[^"\']+\.json)["\']',
        "replacement": r'"runtime/tasks/episodes/\1"',
        "description": "Episode parsed task files"
    },
    # Root task files
    {
        "pattern": r'["\'](?:\.\/)?future_tasks\.json["\']',
        "replacement": r'"runtime/tasks/future_tasks.json"',
        "description": "runtime/tasks/future_tasks.json"
    },
    {
        "pattern": r'["\'](?:\.\/)?working_tasks\.json["\']',
        "replacement": r'"runtime/tasks/working_tasks.json"',
        "description": "runtime/tasks/working_tasks.json"
    },
    {
        "pattern": r'["\'](?:\.\/)?sample_tasks\.json["\']',
        "replacement": r'"runtime/tasks/sample_tasks.json"',
        "description": "runtime/tasks/sample_tasks.json"
    },
    # Agent-specific working tasks
    {
        "pattern": r'["\'](?:\.\/)?working_tasks_agent-(\d+)_claimed\.json["\']',
        "replacement": r'"runtime/tasks/working/working_tasks_agent-\1_claimed.json"',
        "description": "Agent-specific working tasks"
    },
    # Episode YAML files in root
    {
        "pattern": r'["\'](?:\.\/)?dummy_episode\.yaml["\']',
        "replacement": r'"episodes/dummy_episode.yaml"',
        "description": "episodes/dummy_episode.yaml"
    },
    {
        "pattern": r'["\'](?:\.\/)?episode_(\d+)\.yaml["\']',
        "replacement": r'"episodes/episode_\1.yaml"',
        "description": "episode_N.yaml"
    }
]

def update_paths_in_file(filepath, dry_run=False):
    """Update all path references in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        print(f"⚠️  Skipping binary file: {filepath}")
        return 0

    total_changes = 0
    new_content = content

    for update in PATH_UPDATES:
        pattern = update["pattern"]
        replacement = update["replacement"]
        description = update["description"]
        
        new_content, count = re.subn(pattern, replacement, new_content)
        
        if count > 0:
            total_changes += count
            print(f"✅ Updated {count} reference(s) to {description} in {filepath}")
    
    if total_changes > 0 and not dry_run:
        # Only write the file if changes were made and we're not in dry-run mode
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
    return total_changes

def should_exclude(path):
    """Check if a path should be excluded from scanning."""
    path_parts = Path(path).parts
    
    for excluded_dir in EXCLUDED_DIRS:
        if excluded_dir in path_parts:
            return True
    
    return False

def scan_and_update(root, file_extensions, dry_run=False):
    """Scan all files with given extensions and update path references."""
    total_files_changed = 0
    total_references_updated = 0
    
    root_path = Path(root)
    
    for ext in file_extensions:
        for filepath in root_path.glob(f"**/*{ext}"):
            if filepath.is_file() and not should_exclude(filepath):
                changes = update_paths_in_file(filepath, dry_run)
                if changes > 0:
                    total_files_changed += 1
                    total_references_updated += changes
    
    return total_files_changed, total_references_updated

def main():
    parser = argparse.ArgumentParser(description="Update legacy file path references")
    parser.add_argument('--root', default=DEFAULT_ROOT_DIR, help='Root directory to scan')
    parser.add_argument('--extensions', default='.py,.md,.yaml,.yml,.json', 
                      help='Comma-separated list of file extensions to scan')
    parser.add_argument('--dry-run', action='store_true', 
                      help='Show changes without modifying files')
    parser.add_argument('--include-archive', action='store_true',
                      help='Include archive directories in scanning')
    args = parser.parse_args()
    
    print(f"🔍 Scanning for legacy path references in {args.root}...")
    
    # Determine if we're in dry run mode
    dry_run = args.dry_run
    
    if dry_run:
        print("⚠️  DRY RUN MODE: No files will be modified")
    
    extensions = args.extensions.split(',')
    
    # If --include-archive is set, don't exclude archive directories
    if args.include_archive:
        global EXCLUDED_DIRS
        EXCLUDED_DIRS = [d for d in EXCLUDED_DIRS if d != "archive"]
        print("📂 Including archive directories in scan")
    
    files_changed, refs_updated = scan_and_update(args.root, extensions, dry_run)
    
    print(f"\n🏁 Reference update complete!")
    print(f"📊 Stats: Updated {refs_updated} references across {files_changed} files")
    
    if dry_run:
        print("⚠️  This was a dry run. No files were modified.")
        print("   Run without --dry-run to apply changes.")
    else:
        print("\n✅ Files have been updated. Consider:")
        print("   1. Running tests to ensure no loaders broke")
        print("   2. Committing with:")
        print('      git add .')
        print('      git commit -m "refactor: update legacy path references to match new project structure"')

if __name__ == "__main__":
    main() 