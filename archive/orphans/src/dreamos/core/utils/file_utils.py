"""File utilities for Dream.OS."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def load_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load JSON file."""
    try:
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None
        with file_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        return None


def save_json_file(file_path: Path, data: Dict[str, Any]) -> bool:
    """Save JSON file."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving file {file_path}: {e}")
        return False
