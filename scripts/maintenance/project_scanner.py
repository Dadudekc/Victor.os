#!/usr/bin/env python3
"""
Project Scanner - Analyzes repository structure, dependencies, and health metrics.
Generates a comprehensive report of the project's state.
"""

import ast
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Constants
REPORT_DIR = Path("runtime/reports")
SCAN_DIRS = {
    "src": "Source code",
    "tests": "Test files",
    "docs": "Documentation",
    "scripts": "Utility scripts",
    "runtime": "Runtime data",
    "vendor": "Vendor dependencies",
}


def get_file_stats(path: Path) -> Dict:
    """Get statistics for a file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            return {
                "size": path.stat().st_size,
                "lines": len(content.splitlines()),
                "non_empty_lines": len([l for l in content.splitlines() if l.strip()]),
                "imports": extract_imports(content) if path.suffix == ".py" else [],
            }
    except Exception as e:
        return {"error": str(e)}


def extract_imports(content: str) -> List[str]:
    """Extract import statements from Python code."""
    try:
        tree = ast.parse(content)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports
    except:
        return []


def scan_directory(dir_path: Path) -> Dict:
    """Scan a directory and collect statistics."""
    stats = {
        "file_count": 0,
        "total_lines": 0,
        "total_size": 0,
        "extensions": defaultdict(int),
        "imports": defaultdict(int),
        "files": [],
    }

    for path in dir_path.rglob("*"):
        if path.is_file() and not any(part.startswith(".") for part in path.parts):
            file_stats = get_file_stats(path)
            stats["file_count"] += 1
            stats["total_lines"] += file_stats.get("lines", 0)
            stats["total_size"] += file_stats.get("size", 0)
            stats["extensions"][path.suffix] += 1

            if "imports" in file_stats:
                for imp in file_stats["imports"]:
                    stats["imports"][imp] += 1

            stats["files"].append(
                {
                    "path": str(path.relative_to(dir_path)),
                    "size": file_stats.get("size", 0),
                    "lines": file_stats.get("lines", 0),
                }
            )

    return stats


def generate_report(scan_results: Dict) -> str:
    """Generate a markdown report from scan results."""
    report = ["# Project Scan Report\n"]
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Overall Statistics
    report.append("## Overall Statistics\n")
    total_files = sum(stats["file_count"] for stats in scan_results.values())
    total_lines = sum(stats["total_lines"] for stats in scan_results.values())
    total_size = sum(stats["total_size"] for stats in scan_results.values())

    report.append(f"- Total Files: {total_files}")
    report.append(f"- Total Lines: {total_lines:,}")
    report.append(f"- Total Size: {total_size / 1024 / 1024:.1f} MB\n")

    # Directory Statistics
    report.append("## Directory Statistics\n")
    for dir_name, description in SCAN_DIRS.items():
        if dir_name in scan_results:
            stats = scan_results[dir_name]
            report.append(f"\n### {description} ({dir_name}/)\n")
            report.append(f"- Files: {stats['file_count']}")
            report.append(f"- Lines: {stats['total_lines']:,}")
            report.append(f"- Size: {stats['total_size'] / 1024 / 1024:.1f} MB")

            if stats["extensions"]:
                report.append("\nFile Types:")
                for ext, count in sorted(stats["extensions"].items()):
                    report.append(f"- {ext}: {count}")

    # Import Analysis
    report.append("\n## Import Analysis\n")
    all_imports = defaultdict(int)
    for stats in scan_results.values():
        for imp, count in stats["imports"].items():
            all_imports[imp] += count

    if all_imports:
        report.append("Most used imports:")
        for imp, count in sorted(all_imports.items(), key=lambda x: x[1], reverse=True)[
            :20
        ]:
            report.append(f"- {imp}: {count} uses")

    # Large Files
    report.append("\n## Large Files (>100KB)\n")
    large_files = []
    for dir_name, stats in scan_results.items():
        for file in stats["files"]:
            if file["size"] > 100 * 1024:  # 100KB
                large_files.append((f"{dir_name}/{file['path']}", file["size"]))

    if large_files:
        for path, size in sorted(large_files, key=lambda x: x[1], reverse=True):
            report.append(f"- {path}: {size / 1024:.1f} KB")
    else:
        report.append("No large files found.")

    return "\n".join(report)


def main():
    """Main entry point."""
    root = Path.cwd()
    print(f"Scanning project at {root}...")

    scan_results = {}
    for dir_name in SCAN_DIRS:
        dir_path = root / dir_name
        if dir_path.exists():
            print(f"Scanning {dir_name}/...")
            scan_results[dir_name] = scan_directory(dir_path)

    report = generate_report(scan_results)

    # Print report
    print("\n" + report)

    # Save report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "project_scan_report.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nReport saved to: {report_path}")

    # Save raw data for potential future analysis
    data_path = REPORT_DIR / "project_scan_data.json"
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(scan_results, f, indent=2)

    print(f"Raw data saved to: {data_path}")


if __name__ == "__main__":
    main()
