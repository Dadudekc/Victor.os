#!/usr/bin/env python
import os
import re
import argparse

# Placeholder for a script to update Python import paths after reorganization.
# Focuses on the app.automation -> src.apps.automation_gui change.

PATTERNS_TO_REPLACE = {
    # Old import: from app.automation... or import app.automation...
    # The ([\.\s]) captures a dot (for submodules like app.automation.utils) or a whitespace/newline.
    # This captured group is then reinserted with \1 in the replacement string.
    re.compile(r"from\s+app\.automation([\.\s])"): r"from src.apps.automation_gui\1",
    re.compile(r"import\s+app\.automation([\.\s])"): r"import src.apps.automation_gui\1",
}

# Directories to search for Python files (can be expanded)
SEARCH_DIRECTORIES = [".", "src", "tests"] # Current dir, src, tests

def update_imports_in_file(filepath, dry_run=True):
    """Updates import statements in a single Python file."""
    changes_made = False
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for pattern, replacement in PATTERNS_TO_REPLACE.items():
            content, num_subs = pattern.subn(replacement, content)
            if num_subs > 0:
                changes_made = True
                print(f"  - Replaced {num_subs} occurrence(s) of pattern {pattern.pattern} in {filepath}")

        if changes_made and not dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  - Updated file: {filepath}")
        elif changes_made and dry_run:
            print(f"  - DRY-RUN: Would update file: {filepath}")
        
        return changes_made

    except Exception as e:
        print(f"Error processing file {filepath}: {e}")
        return False

def find_and_update_python_files(root_dirs, dry_run=True):
    """Finds all .py files in root_dirs and updates their imports."""
    print(f"Starting import update scan in: {root_dirs}")
    if dry_run:
        print("DRY-RUN mode enabled. No files will be changed.")
    
    files_processed_count = 0
    files_changed_count = 0

    for root_dir in root_dirs:
        for dirpath, _, filenames in os.walk(root_dir):
            # Skip .venv and other common virtual environment or cache dirs
            if ".venv" in dirpath or "__pycache__" in dirpath or ".git" in dirpath:
                continue
            for filename in filenames:
                if filename.endswith(".py"):
                    filepath = os.path.join(dirpath, filename)
                    files_processed_count += 1
                    if update_imports_in_file(filepath, dry_run=dry_run):
                        files_changed_count +=1
    
    print(f"Finished import update scan.")
    print(f"Files processed: {files_processed_count}")
    print(f"Files changed (or would change in dry-run): {files_changed_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update Python import paths after project reorganization.")
    parser.add_argument("--execute", action="store_true", help="Actually execute the file changes. Defaults to dry-run.")
    args = parser.parse_args()

    find_and_update_python_files(SEARCH_DIRECTORIES, dry_run=not args.execute) 