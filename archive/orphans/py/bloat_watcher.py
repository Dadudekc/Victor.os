#!/usr/bin/env python3
"""
Bloat Watcher - Monitors repository for large files and directories
that might need cleanup or optimization.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Constants
MAX_FILE_SIZE_MB = 10  # Files larger than this will be flagged
MAX_DIR_SIZE_MB = 100  # Directories larger than this will be flagged
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "vendor",
    "build",
    "dist",
    "htmlcov",
}
EXCLUDED_FILES = {
    "poetry.lock",
    "package-lock.json",
    "yarn.lock",
    ".coverage",
    "*.pyc",
    "*.pyo",
    "*.pyd",
}


def get_size(path: Path) -> int:
    """Get size of file or directory in bytes."""
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def should_exclude(path: Path) -> bool:
    """Check if path should be excluded from analysis."""
    if path.name in EXCLUDED_FILES:
        return True
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return True
    return False


def scan_directory(root: Path) -> Tuple[List[Dict], List[Dict]]:
    """Scan directory for large files and directories."""
    large_files = []
    large_dirs = []

    for path in root.rglob("*"):
        if should_exclude(path):
            continue

        size = get_size(path)
        size_mb = size / (1024 * 1024)

        if path.is_file() and size_mb > MAX_FILE_SIZE_MB:
            large_files.append(
                {
                    "path": str(path.relative_to(root)),
                    "size": size_mb,
                    "formatted_size": format_size(size),
                }
            )
        elif path.is_dir() and size_mb > MAX_DIR_SIZE_MB:
            large_dirs.append(
                {
                    "path": str(path.relative_to(root)),
                    "size": size_mb,
                    "formatted_size": format_size(size),
                }
            )

    return large_files, large_dirs


def generate_report(large_files: List[Dict], large_dirs: List[Dict]) -> str:
    """Generate a markdown report of findings."""
    report = ["# Bloat Watcher Report\n"]
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    if not large_files and not large_dirs:
        report.append("No large files or directories found. Repository is clean! 🎉")
        return "\n".join(report)

    if large_files:
        report.append("## Large Files\n")
        report.append("Files larger than 10MB:\n")
        for file in sorted(large_files, key=lambda x: x["size"], reverse=True):
            report.append(f"- {file['path']} ({file['formatted_size']})")

    if large_dirs:
        report.append("\n## Large Directories\n")
        report.append("Directories larger than 100MB:\n")
        for dir_ in sorted(large_dirs, key=lambda x: x["size"], reverse=True):
            report.append(f"- {dir_['path']} ({dir_['formatted_size']})")

    return "\n".join(report)


def main():
    """Main entry point."""
    root = Path.cwd()
    print(f"Scanning {root} for large files and directories...")

    large_files, large_dirs = scan_directory(root)
    report = generate_report(large_files, large_dirs)

    # Print report
    print("\n" + report)

    # Save report
    report_dir = root / "runtime" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "bloat_watcher_report.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nReport saved to: {report_path}")

    # Exit with error if issues found
    if large_files or large_dirs:
        sys.exit(1)


if __name__ == "__main__":
    main()
