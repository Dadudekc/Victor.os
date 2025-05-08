#!/usr/bin/env python
import subprocess
import os
import argparse

# Script to handle sandbox consolidation: dev_sandbox -> sandbox

SANDBOX_MAPPINGS = {
    "dev_sandbox/agent_file_manager_stub.py": "sandbox/legacy_stubs_and_utils/agent_file_manager_stub.py",
    # Add other specific file or directory mappings from dev_sandbox if they exist
}

# If dev_sandbox itself contains subdirectories that need to be moved as a whole:
# E.g., "dev_sandbox/some_tool": "sandbox/some_tool_new_location"

def ensure_target_dir_exists(filepath, dry_run=True):
    """Ensures the target directory for a file exists."""
    target_dir = os.path.dirname(filepath)
    if not os.path.exists(target_dir):
        if dry_run:
            print(f"DRY-RUN: Would create directory {target_dir}")
        else:
            print(f"Creating directory {target_dir}")
            os.makedirs(target_dir)

def move_sandbox_item(source_item, dest_item, dry_run=True):
    """Moves a single sandbox item (file or directory) using git mv."""
    if not os.path.exists(source_item):
        print(f"Source {source_item} not found. Skipping.")
        return False

    ensure_target_dir_exists(dest_item, dry_run)
    
    git_mv_command = ["git", "mv", source_item, dest_item]
    
    if dry_run:
        print(f"DRY-RUN: Would execute: {' '.join(git_mv_command)}")
        return True # Assume success for dry run for this item
    else:
        print(f"Executing: {' '.join(git_mv_command)}")
        try:
            subprocess.run(git_mv_command, check=True, capture_output=True, text=True)
            print(f"Successfully moved {source_item} to {dest_item}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error moving {source_item}: {e}")
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Move sandbox content using git mv.")
    parser.add_argument("--execute", action="store_true", help="Actually execute the git mv commands. Defaults to dry-run.")
    args = parser.parse_args()

    print("Starting migration script for dev_sandbox content...")
    overall_success = True
    items_moved_count = 0

    for source, dest in SANDBOX_MAPPINGS.items():
        print(f"\nProcessing mapping: {source} -> {dest}")
        if move_sandbox_item(source, dest, dry_run=not args.execute):
            items_moved_count += 1
        else:
            overall_success = False
            print(f"Errors occurred processing {source}. Review logs.")

    # After specific mapped items, check if dev_sandbox still exists and has other content
    if os.path.exists("dev_sandbox") and not args.execute:
        remaining_items = os.listdir("dev_sandbox")
        # Filter out items that were supposed to be moved if the script was comprehensive for all dev_sandbox items
        # For simplicity, we'll just check if it's empty assuming mappings cover all intentional moves.
        # A more robust script would check if remaining_items are only those that failed or were not in SANDBOX_MAPPINGS.
        if not remaining_items and items_moved_count > 0 and overall_success:
             print("DRY-RUN: `dev_sandbox` would be empty and could be deleted.")
        elif remaining_items:
            print(f"DRY-RUN: `dev_sandbox` still contains items: {remaining_items}. Manual review needed before deleting dev_sandbox.")

    elif os.path.exists("dev_sandbox") and args.execute and overall_success and items_moved_count > 0:
        # Logic to attempt to remove dev_sandbox if it's now empty
        try:
            if not os.listdir("dev_sandbox"):
                print("All known items moved from dev_sandbox and it appears empty.")
                # Potentially `git rm -r dev_sandbox` or `os.rmdir` if not git tracked or git rm failed
                print("Manual deletion of `dev_sandbox` directory recommended after verification.")
            else:
                print(f"`dev_sandbox` still contains items: {os.listdir('dev_sandbox')}. Not removing.")
        except OSError as e:
            print(f"Error trying to list or remove dev_sandbox: {e}")

    if overall_success and not args.execute:
        print("\nDRY-RUN successful for all sandbox mappings. No actual changes made.")
    elif overall_success and args.execute:
        print("\nSuccessfully processed all mapped sandbox items.")

    print("Migration script for dev_sandbox content finished.") 