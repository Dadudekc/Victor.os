#!/usr/bin/env python
import subprocess
import os
import argparse

# Script to handle application code consolidation: app/* and apps/* -> src/apps/*

APPLICATION_MAPPINGS = {
    # Source Path : Target Path in src/apps/
    "app/automation": "src/apps/automation_gui",
    "apps/sky_viewer": "src/apps/sky_viewer",
    "apps/browser": "src/apps/browser",
    # apps/examples is handled separately due to evaluation needed (src/examples or ai_docs/)
}

def ensure_target_app_dir_exists(target_app_path, dry_run=True):
    """Ensures the target application directory exists."""
    if not os.path.exists(target_app_path):
        if dry_run:
            print(f"DRY-RUN: Would create directory {target_app_path}")
        else:
            print(f"Creating directory {target_app_path}")
            os.makedirs(target_app_path)

def move_application_code(source_path, target_path, dry_run=True):
    """Moves contents of a source application directory to a target using git mv."""
    if not os.path.exists(source_path):
        print(f"Source directory {source_path} not found. Skipping.")
        return False

    ensure_target_app_dir_exists(target_path, dry_run)
    
    all_successful = True
    # Move all contents from source_path into target_path
    # git mv source_path/* target_path/ would require shell=True or globbing, better to iterate
    for item_name in os.listdir(source_path):
        source_item_path = os.path.join(source_path, item_name)
        # Construct destination to be *inside* the target_path directory
        dest_item_path = os.path.join(target_path, item_name) 
        
        git_mv_command = ["git", "mv", source_item_path, dest_item_path]
        
        if dry_run:
            print(f"DRY-RUN: Would execute: {' '.join(git_mv_command)}")
        else:
            print(f"Executing: {' '.join(git_mv_command)}")
            try:
                subprocess.run(git_mv_command, check=True, capture_output=True, text=True)
                print(f"Successfully moved {source_item_path} to {dest_item_path}")
            except subprocess.CalledProcessError as e:
                print(f"Error moving {source_item_path} to {dest_item_path}: {e}")
                print(f"Stdout: {e.stdout}")
                print(f"Stderr: {e.stderr}")
                all_successful = False
    return all_successful

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Move application content to src/apps/ using git mv.")
    parser.add_argument("--execute", action="store_true", help="Actually execute the git mv commands. Defaults to dry-run.")
    args = parser.parse_args()

    print("Starting migration script for application content...")
    overall_success = True

    # Ensure src/apps parent directory exists
    if not os.path.exists("src/apps"):
        if not args.execute:
            print("DRY-RUN: Would create directory src/apps")
        else:
            print("Creating directory src/apps")
            os.makedirs("src/apps")

    for source, dest_target_in_src_apps in APPLICATION_MAPPINGS.items():
        print(f"\nProcessing mapping: {source} -> {dest_target_in_src_apps}")
        if not move_application_code(source, dest_target_in_src_apps, dry_run=not args.execute):
            overall_success = False
            print(f"Errors occurred processing {source}. Review logs.")

    # After processing, check if original app/ and apps/ directories can be deleted
    # This requires them to be empty. The script currently moves their *contents*.
    # Agent 6 will need to manually verify and then use `git rm -r app` and `git rm -r apps` if empty.
    if not args.execute:
        print("\nDRY-RUN: Check if `app/` and `apps/` (excluding `apps/examples`) would be empty.")
        print("DRY-RUN: Manual deletion of `app/` and `apps/` directories would be needed after verification.")
    else:
        print("\nINFO: Manual deletion of `app/` and `apps/` directories (if empty) is recommended after verification.")

    if overall_success and not args.execute:
        print("\nDRY-RUN successful for all application mappings. No actual changes made.")
    elif overall_success and args.execute:
        print("\nSuccessfully processed all mapped application items.")

    print("Migration script for application content finished.") 