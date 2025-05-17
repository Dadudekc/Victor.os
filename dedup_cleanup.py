import yaml
import os
import shutil
from datetime import datetime

ACTION_PLAN_PATH = "deduplication_action_plan.yaml"
LOG_FILE_PATH = "runtime/reports/deduplication_log.md"

def execute_deduplication_plan():
    """Parses the YAML action plan and executes deletions and renames."""
    try:
        with open(ACTION_PLAN_PATH, 'r') as f:
            plan = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Action plan '{ACTION_PLAN_PATH}' not found.")
        return
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return

    if not plan or 'duplicate_clusters' not in plan:
        print("Error: Action plan is empty or malformed.")
        return

    log_entries = [f"# Deduplication Cleanup Log - {datetime.now().isoformat()}", "---"]
    files_deleted_count = 0
    files_renamed_count = 0
    operations_skipped_count = 0

    # Ensure logs/reports directory exists for the markdown log
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)

    for cluster in plan.get('duplicate_clusters', []):
        cluster_id = cluster.get('cluster_id', 'Unknown Cluster')
        log_entries.append(f"\n## Processing: {cluster_id}")
        
        for file_action in cluster.get('files', []):
            path = file_action.get('path')
            action = file_action.get('action')
            reason = file_action.get('reason', 'No reason provided')

            if not path:
                log_entries.append(f"  - SKIPPED: Missing path in action plan for cluster '{cluster_id}'.")
                operations_skipped_count += 1
                continue

            absolute_path = os.path.abspath(path) # Ensure path is absolute

            if action == 'delete':
                if os.path.exists(absolute_path):
                    try:
                        os.remove(absolute_path)
                        log_entries.append(f"  - DELETED: '{absolute_path}' (Reason: {reason})")
                        files_deleted_count += 1
                    except OSError as e:
                        log_entries.append(f"  - FAILED DELETE: '{absolute_path}'. Error: {e}")
                        operations_skipped_count += 1
                else:
                    log_entries.append(f"  - SKIPPED DELETE (Not found): '{absolute_path}'")
                    operations_skipped_count += 1
            
            elif action == 'rename':
                new_path = file_action.get('new_path')
                if not new_path:
                    log_entries.append(f"  - SKIPPED RENAME (Missing new_path): '{absolute_path}' in '{cluster_id}'.")
                    operations_skipped_count += 1
                    continue
                
                absolute_new_path = os.path.abspath(new_path)
                if os.path.exists(absolute_path):
                    try:
                        # Ensure parent directory of new_path exists
                        os.makedirs(os.path.dirname(absolute_new_path), exist_ok=True)
                        shutil.move(absolute_path, absolute_new_path)
                        log_entries.append(f"  - RENAMED: '{absolute_path}' to '{absolute_new_path}' (Reason: {reason})")
                        files_renamed_count += 1
                    except OSError as e:
                        log_entries.append(f"  - FAILED RENAME: '{absolute_path}' to '{absolute_new_path}'. Error: {e}")
                        operations_skipped_count += 1
                else:
                    log_entries.append(f"  - SKIPPED RENAME (Source not found): '{absolute_path}'")
                    operations_skipped_count += 1
            
            elif action == 'keep' or action == 'ignore':
                log_entries.append(f"  - INFO ({action.upper()}): '{absolute_path}' (Reason: {reason})")
            else:
                log_entries.append(f"  - WARNING (Unknown Action '{action}'): '{absolute_path}' for cluster '{cluster_id}'.")
                operations_skipped_count += 1

    # Update timestamp in the YAML plan file itself
    # This is a bit more complex as it involves reading, updating, and writing YAML carefully.
    # For now, we'll skip modifying the YAML directly in this script to keep it simpler.
    # The log file will have the execution timestamp.
    # If direct YAML update is needed, PyYAML's dump with a custom representer or manual string manipulation would be required.

    # Add summary to log
    log_entries.append("\n---")
    log_entries.append("## Execution Summary")
    log_entries.append(f"- Files Deleted: {files_deleted_count}")
    log_entries.append(f"- Files Renamed: {files_renamed_count}")
    log_entries.append(f"- Operations Skipped/Failed: {operations_skipped_count}")
    log_entries.append(f"\nFull log written to: {os.path.abspath(LOG_FILE_PATH)}")

    try:
        with open(LOG_FILE_PATH, 'w') as f:
            f.write("\n".join(log_entries))
        print(f"Cleanup actions processed. Log saved to: {os.path.abspath(LOG_FILE_PATH)}")
        print(f"Summary: {files_deleted_count} deleted, {files_renamed_count} renamed, {operations_skipped_count} skipped/failed.")
    except IOError as e:
        print(f"Error writing log file '{LOG_FILE_PATH}': {e}")
        print("Log entries (to console):")
        for entry in log_entries:
            print(entry)

if __name__ == "__main__":
    # Before running, ask for user confirmation
    confirm = input(f"This script will perform file deletions and renames based on '{ACTION_PLAN_PATH}'.\nAre you sure you want to proceed? (yes/no): ")
    if confirm.lower() == 'yes':
        print("Executing cleanup plan...")
        execute_deduplication_plan()
    else:
        print("Cleanup aborted by user.") 