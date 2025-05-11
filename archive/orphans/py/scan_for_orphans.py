#!/usr/bin/env python3
"""
Orphan File Scanner: Finds files never imported, referenced, or accessed in 60+ days.
"""

import ast
import sys
import time
from pathlib import Path

print("[DEBUG] Starting orphan file scan...")

ROOT = Path(".").resolve()
AGE_DAYS = 60
NOW = time.time()

# File types to check for orphans
CODE_EXTS = {".py", ".sh", ".ps1", ".bat"}
DATA_EXTS = {".json", ".yaml", ".yml", ".csv", ".txt"}


def find_orphans():
    print("[DEBUG] Finding all files...")
    # 1. Find all files
    all_files = [
        p
        for p in ROOT.rglob("*")
        if p.is_file()
        and not any(
            x in p.parts
            for x in [".git", "venv", "env", "node_modules", "archive", "vendor"]
        )
    ]
    print(f"[DEBUG] Found {len(all_files)} total files")

    print("[DEBUG] Finding Python imports...")
    # 2. Find all Python imports
    imported = set()
    for py in [p for p in all_files if p.suffix == ".py"]:
        try:
            with open(py, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for n in node.names:
                        imported.add(n.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported.add(node.module.split(".")[0])
        except Exception as e:
            print(f"[WARN] Failed to parse {py}: {e}")
            continue
    print(f"[DEBUG] Found {len(imported)} imported modules")

    print("[DEBUG] Finding CLI scripts...")
    # 3. Find all CLI/agent-registered scripts (simple heuristic)
    cli_scripts = set()
    for py in [p for p in all_files if p.suffix == ".py"]:
        try:
            with open(py, "r", encoding="utf-8") as f:
                src = f.read()
            if "argparse" in src or "click" in src or "if __name__" in src:
                cli_scripts.add(py.stem)
        except Exception as e:
            print(f"[WARN] Failed to read {py}: {e}")
            continue
    print(f"[DEBUG] Found {len(cli_scripts)} CLI scripts")

    print("[DEBUG] Finding old files...")
    # 4. Find files not accessed in AGE_DAYS
    old_files = [p for p in all_files if (NOW - p.stat().st_atime) > AGE_DAYS * 86400]
    print(f"[DEBUG] Found {len(old_files)} old files")

    print("[DEBUG] Identifying orphans...")
    # 5. Orphan logic
    orphans = []
    for f in all_files:
        if f.suffix in CODE_EXTS:
            # Not imported, not CLI, not referenced by name
            if f.stem not in imported and f.stem not in cli_scripts:
                orphans.append(f)
        elif f.suffix in DATA_EXTS:
            if f in old_files:
                orphans.append(f)

    print(f"[DEBUG] Found {len(orphans)} orphaned files")
    return orphans


if __name__ == "__main__":
    try:
        orphans = find_orphans()
        print(f"\nFound {len(orphans)} orphaned files:")
        for o in orphans:
            print(f"[ORPHAN] {o}")
    except Exception as e:
        print(f"[ERROR] Script failed: {e}", file=sys.stderr)
        sys.exit(1)
