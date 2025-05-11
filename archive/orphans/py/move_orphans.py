#!/usr/bin/env python3
"""
Move Orphaned Files: Moves orphaned files to archive/orphans/ directory.
"""

import shutil
from pathlib import Path

from scan_for_orphans import find_orphans


def move_orphans():
    # Create archive/orphans directory if it doesn't exist
    archive_dir = Path("archive/orphans")
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Get list of orphaned files
    orphans = find_orphans()

    moved = []
    for orphan in orphans:
        try:
            # Create relative path structure in archive
            rel_path = orphan.relative_to(Path("."))
            target = archive_dir / rel_path

            # Create parent directories if needed
            target.parent.mkdir(parents=True, exist_ok=True)

            # Move the file
            shutil.move(str(orphan), str(target))
            moved.append(orphan)
            print(f"[MOVED] {orphan} -> {target}")
        except Exception as e:
            print(f"[ERROR] Failed to move {orphan}: {e}")

    return moved


if __name__ == "__main__":
    moved = move_orphans()
    print(f"\nMoved {len(moved)} orphaned files to archive/orphans/")
