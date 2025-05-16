"""Validation utilities for Dream.OS."""

import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def validate_json_file(file_path: Path) -> Tuple[bool, Optional[str]]:
    """Validate JSON file."""
    try:
        if not file_path.exists():
            return False, f"File not found: {file_path}"
        with file_path.open("r", encoding="utf-8") as f:
            json.load(f)
        return True, None
    except json.JSONDecodeError as e:
        return False, f"Error decoding JSON from {file_path}: {e}"
    except Exception as e:
        return False, f"Error validating file {file_path}: {e}"


def validate_required_files(required_files: List[Path]) -> Tuple[bool, List[str]]:
    """Validate required files exist."""
    missing_files = []
    for file_path in required_files:
        if not file_path.exists():
            missing_files.append(str(file_path))
    return len(missing_files) == 0, missing_files


def validate_required_dirs(required_dirs: List[Path]) -> Tuple[bool, List[str]]:
    """Validate required directories exist."""
    missing_dirs = []
    for dir_path in required_dirs:
        if not dir_path.exists():
            missing_dirs.append(str(dir_path))
    return len(missing_dirs) == 0, missing_dirs
