"""Path utilities for Dream.OS."""

import os
from pathlib import Path
from typing import Optional

def find_project_root(marker: str = ".git") -> Optional[Path]:
    """Find project root by searching for a marker file/directory."""
    current_path = Path.cwd()
    while current_path != current_path.parent:
        if (current_path / marker).exists():
            return current_path
        current_path = current_path.parent
    return None

def ensure_dir_exists(path: Path) -> bool:
    """Ensure directory exists, creating it if necessary."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False

def get_relative_path(path: Path, base_path: Path) -> Path:
    """Get path relative to base path."""
    try:
        return path.relative_to(base_path)
    except ValueError:
        return path 