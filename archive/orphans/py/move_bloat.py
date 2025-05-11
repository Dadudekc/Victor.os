#!/usr/bin/env python3
"""
Move Bloat Directory: Identifies and moves the largest directory to vendor/ or archive/.
"""

import os
import shutil
from pathlib import Path


def get_dir_size(path):
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            try:
                total += (Path(root) / f).stat().st_size
            except Exception:
                continue
    return total


def find_top_bloat_dir():
    # Directories to exclude from consideration
    exclude = {".git", "venv", "env", "node_modules", "archive", "vendor"}

    # Get all directories and their sizes
    dir_sizes = []
    for root, dirs, files in os.walk("."):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude]

        # Skip if current directory is in exclude list
        if any(x in Path(root).parts for x in exclude):
            continue

        size = get_dir_size(root)
        if size > 0:  # Only include non-empty directories
            dir_sizes.append((Path(root), size))

    # Sort by size descending
    dir_sizes.sort(key=lambda x: x[1], reverse=True)

    return dir_sizes[0] if dir_sizes else None


def move_bloat_dir():
    # Find the largest directory
    result = find_top_bloat_dir()
    if not result:
        print("No bloat directories found.")
        return

    source_dir, size_mb = result
    size_mb = size_mb / (1024 * 1024)  # Convert to MB

    # Determine target location (vendor/ for code, archive/ for data)
    if any(
        f.suffix in {".py", ".js", ".ts", ".java", ".cpp", ".h"}
        for f in source_dir.rglob("*")
    ):
        target_dir = Path("vendor") / source_dir.name
    else:
        target_dir = Path("archive") / source_dir.name

    # Create target directory
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Move the directory
        shutil.move(str(source_dir), str(target_dir))
        print(f"[MOVED] {source_dir} ({size_mb:.1f}MB) -> {target_dir}")
    except Exception as e:
        print(f"[ERROR] Failed to move {source_dir}: {e}")


if __name__ == "__main__":
    move_bloat_dir()
