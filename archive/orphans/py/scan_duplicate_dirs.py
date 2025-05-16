#!/usr/bin/env python3
"""
Scan for duplicate directories in the project.
Identifies directories that have similar content and structure.
"""

import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Directories to exclude from scanning
EXCLUDE_DIRS = {
    "__pycache__",
    "node_modules",
    ".git",
    "venv",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".vscode",
    ".idea",
}


def should_scan_dir(dir_path: str) -> bool:
    """Check if directory should be scanned."""
    return not any(exclude in dir_path for exclude in EXCLUDE_DIRS)


def get_dir_signature(dir_path: Path) -> str:
    """
    Generate a signature for a directory based on its structure and file sizes.
    More efficient than full content hashing.
    """
    if not dir_path.is_dir():
        return ""

    items = []
    try:
        # Get directory structure and file sizes
        for root, dirs, files in os.walk(dir_path, topdown=True):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if should_scan_dir(d)]

            # Sort for consistent ordering
            dirs.sort()
            files.sort()

            rel_root = Path(root).relative_to(dir_path)

            # Add directory structure
            items.extend(f"d:{rel_root}/{d}" for d in dirs)

            # Add file info (name and size only)
            for f in files:
                try:
                    fpath = Path(root) / f
                    size = fpath.stat().st_size
                    items.append(f"f:{rel_root}/{f}:{size}")
                except (OSError, PermissionError):
                    continue

    except (OSError, PermissionError):
        return ""

    # Create hash of directory signature
    return hashlib.md5("".join(items).encode()).hexdigest()


def find_duplicate_dirs(root_path: Path) -> Dict[str, List[Path]]:
    """
    Find directories that appear to be duplicates based on their signature.
    """
    dir_signatures = defaultdict(list)

    print("Scanning directories...")
    count = 0

    # Walk through all directories
    for root, dirs, _ in os.walk(root_path, topdown=True):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if should_scan_dir(d)]

        current_path = Path(root)

        # Get signature for current directory
        dir_sig = get_dir_signature(current_path)
        if dir_sig:
            dir_signatures[dir_sig].append(current_path)

        # Progress indicator
        count += 1
        if count % 100 == 0:
            print(f"Processed {count} directories...", end="\r")

    print("\nAnalyzing results...")

    # Filter out unique directories
    return {sig: paths for sig, paths in dir_signatures.items() if len(paths) > 1}


def generate_report(duplicates: Dict[str, List[Path]], output_file: Path) -> None:
    """Generate a JSON report of duplicate directories."""
    report = {
        "scan_time": datetime.now().isoformat(),
        "total_duplicate_groups": len(duplicates),
        "total_duplicate_dirs": sum(len(paths) - 1 for paths in duplicates.values()),
        "duplicate_groups": [
            {
                "signature": sig,
                "directories": [str(p) for p in paths],
                "dir_count": len(paths),
            }
            for sig, paths in duplicates.items()
        ],
    }

    with output_file.open("w") as f:
        json.dump(report, f, indent=2)


def main():
    # Use current working directory as root
    root_path = Path.cwd()
    output_file = root_path / "runtime" / "reports" / "duplicate_dirs_report.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"Starting duplicate directory scan in {root_path}")
    print(f"Excluding directories: {', '.join(EXCLUDE_DIRS)}")

    duplicates = find_duplicate_dirs(root_path)

    if not duplicates:
        print("\nNo duplicate directories found.")
        return

    # Generate report
    generate_report(duplicates, output_file)

    # Print summary
    total_groups = len(duplicates)
    total_dupes = sum(len(paths) - 1 for paths in duplicates.values())

    print(f"\nFound {total_groups} groups of duplicate directories")
    print(f"Total duplicate directories: {total_dupes}")

    for sig, paths in duplicates.items():
        print(f"\nDuplicate group (signature: {sig[:8]}) - {len(paths)} directories:")
        for path in paths:
            print(f"  - {path}")

    print(f"\nDetailed report saved to: {output_file}")


if __name__ == "__main__":
    main()
