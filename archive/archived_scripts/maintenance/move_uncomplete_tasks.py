#!/usr/bin/env python3
"""
Archive uncompleted and proposal-based task files into a subfolder.
"""

import glob
import os
import shutil


def main():
    task_dir = os.path.join("_agent_coordination", "tasks")
    archive_dir = os.path.join(task_dir, "archive")
    os.makedirs(archive_dir, exist_ok=True)

    patterns = ["*gap_tasks.json", "*_proposal.json"]
    for pattern in patterns:
        for path in glob.glob(os.path.join(task_dir, pattern)):
            dest = os.path.join(archive_dir, os.path.basename(path))
            shutil.move(path, dest)
            print(f"Moved {path} to {dest}")


if __name__ == "__main__":
    main()
