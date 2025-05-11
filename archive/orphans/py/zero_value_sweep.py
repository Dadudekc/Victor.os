#!/usr/bin/env python3
"""
Zero-Value File Sweep: Recursively deletes bloat files (pycache, logs, .bak, .DS_Store, pytest_cache, etc.)
"""

import os
from pathlib import Path

PATTERNS = [
    "__pycache__",
    ".DS_Store",
    ".log",
    ".bak",
    ".ipynb_checkpoints",
    ".pytest_cache",
]

ROOT = Path(".").resolve()


def should_delete(path: Path) -> bool:
    name = path.name
    if any(
        name == pat
        or name.endswith(pat)
        or (pat.startswith(".") and name.endswith(pat))
        for pat in PATTERNS
    ):
        return True
    return False


def sweep(root: Path):
    deleted = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Remove matching directories
        for d in list(dirnames):
            if should_delete(Path(d)):
                full = Path(dirpath) / d
                try:
                    for sub in full.rglob("*"):
                        if sub.is_file():
                            sub.unlink()
                    full.rmdir()
                    deleted.append(str(full))
                    dirnames.remove(d)
                except Exception as e:
                    print(f"[WARN] Could not delete dir {full}: {e}")
        # Remove matching files
        for f in filenames:
            file_path = Path(dirpath) / f
            if should_delete(file_path):
                try:
                    file_path.unlink()
                    deleted.append(str(file_path))
                except Exception as e:
                    print(f"[WARN] Could not delete file {file_path}: {e}")
    return deleted


if __name__ == "__main__":
    deleted = sweep(ROOT)
    print(f"Deleted {len(deleted)} zero-value files/dirs.")
    for path in deleted:
        print(f"[DEL] {path}")
