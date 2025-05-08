#!/usr/bin/env python
import subprocess
import os
import argparse

# Placeholder for a more comprehensive migration script
# This initial version focuses on moving _archive/scripts to archive/archived_scripts
# Extended to also handle _archive/tests to archive/archived_tests

ARCHIVE_MAPPINGS = {
    "_archive/scripts": "archive/archived_scripts",
    "_archive/tests": "archive/archived_tests",
}

def move_content_for_mapping(source_base, dest_base, dry_run=True):
    """Moves contents of a source_base to a dest_base using git mv."""
    if not os.path.exists(source_base):
        print(f"Source directory {source_base} not found. Skipping.")
        return False

    if not os.path.exists(os.path.dirname(dest_base)):
        if dry_run:
            print(f"DRY-RUN: Would create parent directory {os.path.dirname(dest_base)}")
        else:
            print(f"Creating parent directory {os.path.dirname(dest_base)}")
            os.makedirs(os.path.dirname(dest_base), exist_ok=True)

    if not os.path.exists(dest_base):
        if dry_run:
            print(f"DRY-RUN: Would create directory {dest_base}")
        else:
            print(f"Creating directory {dest_base}")
            os.makedirs(dest_base, exist_ok=True)
    
    all_successful = True
    for item_name in os.listdir(source_base):
        source_item_path = os.path.join(source_base, item_name)
        dest_item_path = os.path.join(dest_base, item_name)
        
        git_mv_command = ["git", "mv", source_item_path, dest_item_path]
        
        if dry_run:
            print(f"DRY-RUN: Would execute: {' '.join(git_mv_command)}")
        else:
            print(f"Executing: {' '.join(git_mv_command)}")
            try:
                subprocess.run(git_mv_command, check=True, capture_output=True, text=True)
                print(f"Successfully moved {source_item_path} to {dest_item_path}")
            except subprocess.CalledProcessError as e:
                print(f"Error moving {source_item_path}: {e}")
                print(f"Stdout: {e.stdout}")
                print(f"Stderr: {e.stderr}")
                all_successful = False
    return all_successful

# Remove old function specific to scripts
# def move_archived_scripts(dry_run=True): ...

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Move archived content using git mv.")
    parser.add_argument("--execute", action="store_true", help="Actually execute the git mv commands. Defaults to dry-run.")
    args = parser.parse_args()

    print("Starting migration script for _archive content...")
    overall_success = True
    for source_dir, dest_dir in ARCHIVE_MAPPINGS.items():
        print(f"\nProcessing mapping: {source_dir} -> {dest_dir}")
        if not move_content_for_mapping(source_dir, dest_dir, dry_run=not args.execute):
            overall_success = False
            print(f"Errors occurred processing {source_dir}. Review logs.")
    
    if overall_success and not args.execute:
        print("\nDRY-RUN successful for all mappings. No actual changes made.")
    elif overall_success and args.execute:
        print("\nSuccessfully processed all mappings and executed moves.")
        # Add logic here to delete the top-level _archive dir if all content moved and no errors
        # For example, after confirming all sub-moves were good:
        # if os.path.exists("_archive") and not os.listdir("_archive"):
        #     print("Attempting to remove empty _archive directory...")
        # else if os.path.exists("_archive"):
        #     print("_archive directory still contains items, not removing.")

    print("Migration script for _archive content finished.") 