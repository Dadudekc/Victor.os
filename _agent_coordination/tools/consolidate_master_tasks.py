#!/usr/bin/env python3
"""
Consolidate master task shards into one canonical list.
"""
import glob
from pathlib import Path
from _agent_coordination.tools.file_lock_manager import read_json, write_json
import json  # for json.dumps

def main():
    # Directory containing shard files
    task_dir = Path(__file__).parent.parent / 'tasks'
    pattern = str(task_dir / 'master_tasks_*.json')
    shard_files = sorted(glob.glob(pattern))

    all_tasks = []
    for file_path in shard_files:
        try:
            data = read_json(file_path) or []
            if isinstance(data, list):
                all_tasks.extend(data)
        except Exception as e:
            print(f"Skipping {file_path}: {e}")

    # Write consolidated tasks
    output_file = task_dir / 'master_task_list.json'
    write_json(output_file, all_tasks)
    print(f"Consolidated {len(all_tasks)} tasks into {output_file}")

if __name__ == '__main__':
    main() 