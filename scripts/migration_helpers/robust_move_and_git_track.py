#!/usr/bin/env python
import os
import shutil
import subprocess
import argparse
import json

# Script to robustly move files/directories and track with Git
# Uses shutil.copy, git add <new>, git rm <old>

PATH_MAPPING_FILE = "specs/verification/docs_path_mapping.json"

def run_git_command(git_args, dry_run=True, working_dir=None):
    command = ["git"] + git_args
    if dry_run:
        print(f"DRY-RUN: Would execute Git command: {' '.join(command)}")
        return True # Assume success for dry run
    else:
        print(f"Executing Git command: {' '.join(command)}")
        try:
            process = subprocess.run(command, check=True, capture_output=True, text=True, cwd=working_dir)
            print(f"Git command successful. Output:\n{process.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error executing Git command {' '.join(command)}: {e}")
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
            return False

def robust_move_item(source_path, dest_path, is_directory, dry_run=True):
    """Robustly moves an item (file or directory) and updates Git tracking."""
    print(f"Processing move: '{source_path}' -> '{dest_path}' (Directory: {is_directory})")

    if not os.path.exists(source_path):
        print(f"Warning: Source path '{source_path}' does not exist. Skipping.")
        return False # Or True if skipping is considered a non-failure for this item

    # Ensure destination parent directory exists
    dest_parent_dir = os.path.dirname(dest_path)
    if not os.path.exists(dest_parent_dir):
        if dry_run:
            print(f"DRY-RUN: Would create directory: {dest_parent_dir}")
        else:
            print(f"Creating directory: {dest_parent_dir}")
            os.makedirs(dest_parent_dir, exist_ok=True)

    # Perform copy
    if dry_run:
        print(f"DRY-RUN: Would copy '{source_path}' to '{dest_path}'")
    else:
        print(f"Copying '{source_path}' to '{dest_path}'...")
        try:
            if is_directory:
                if os.path.exists(dest_path):
                    print(f"Warning: Destination directory '{dest_path}' already exists. shutil.copytree might fail or merge.")
                    # For simplicity, if dest_path exists, assume it's from a partial run or intentional.
                    # A more robust script might delete it first or merge contents carefully.
                    # For now, let copytree handle it or error if it can't overwrite/merge as needed.
                shutil.copytree(source_path, dest_path, dirs_exist_ok=True) # dirs_exist_ok for Py3.8+
            else:
                shutil.copy2(source_path, dest_path)
            print("Copy successful.")
        except Exception as e:
            print(f"Error copying '{source_path}' to '{dest_path}': {e}")
            return False

    # Git operations
    if not run_git_command(["add", dest_path], dry_run=dry_run):
        print(f"Failed to git add '{dest_path}'. Aborting further git ops for this item.")
        # Potentially try to clean up copied files if add fails?
        return False
    
    git_rm_args = ["rm"]
    if is_directory:
        git_rm_args.append("-r")
    git_rm_args.append(source_path)
    
    if not run_git_command(git_rm_args, dry_run=dry_run):
        print(f"Failed to git rm '{source_path}'. The file was copied and added, but old path remains.")
        # This state requires manual intervention or more complex rollback logic.
        return False # Mark as failure for this item due to incomplete git operation

    print(f"Successfully processed and git tracked move for '{source_path}'")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Robustly move files/directories and update Git tracking.")
    parser.add_argument("--execute", action="store_true", help="Actually execute file operations and Git commands. Defaults to dry-run.")
    parser.add_argument("--mapping_file", default=PATH_MAPPING_FILE, help=f"Path to the JSON mapping file. Defaults to {PATH_MAPPING_FILE}")
    args = parser.parse_args()

    print(f"Starting robust move process. Dry run: {not args.execute}")

    path_mapping = {}
    try:
        with open(args.mapping_file, 'r') as f:
            path_mapping = json.load(f)
        print(f"Loaded path mapping from {args.mapping_file}")
        if not path_mapping:
            print(f"Warning: Mapping file {args.mapping_file} is empty.")
    except FileNotFoundError:
        print(f"Error: Mapping file {args.mapping_file} not found.")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {args.mapping_file}: {e}")
        exit(1)

    overall_success_count = 0
    failed_items = []

    # It's important to process specific file mappings before directory mappings
    # if a file within a directory has a different target than the directory's general content.
    # This simplified example iterates mapping as is. A real script would sort or group.
    # For `docs_path_mapping.json`, source paths ending with '/' are directories.
    for old_path, new_path in path_mapping.items():
        is_dir = old_path.endswith("/")
        # Normalize paths by removing trailing slash for os.path.exists checks on dirs if it causes issues
        # For shutil.copytree, source dir should not have trailing slash if dest exists usually.
        # For os.path.exists, trailing slash on dir is usually fine.
        normalized_old_path = old_path.rstrip("/")
        normalized_new_path = new_path.rstrip("/") # Assuming new_path for dir also implies dir

        # If the mapping was for a directory, copytree expects dest to be the new dir name
        # If old_path was "docs/foo/" and new_path was "ai_docs/bar/foo/"
        # then source for copytree is "docs/foo", dest is "ai_docs/bar/foo"
        # If old_path was "docs/file.md" and new_path was "ai_docs/file.md"
        # then source for copy2 is "docs/file.md", dest is "ai_docs/file.md"

        if robust_move_item(normalized_old_path, normalized_new_path, is_dir, dry_run=not args.execute):
            overall_success_count += 1
        else:
            failed_items.append(old_path)
            print(f"Failed to process '{old_path}'")
    
    print("\nRobust move process finished.")
    print(f"Successfully processed items: {overall_success_count}")
    if failed_items:
        print(f"Failed to process items: {len(failed_items)}")
        for item in failed_items:
            print(f"  - {item}")
    else:
        print("All items processed successfully (or skipped if source not found).") 