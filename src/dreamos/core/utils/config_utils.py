"""Configuration utilities for Dream.OS."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

def load_config_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load configuration file."""
    try:
        if not file_path.exists():
            logger.warning(f"Config file not found: {file_path}")
            return None
        with file_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding config JSON from {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading config file {file_path}: {e}")
        return None

def save_config_file(file_path: Path, data: Dict[str, Any]) -> bool:
    """Save configuration file."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving config file {file_path}: {e}")
        return False

def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with optional default."""
    return os.environ.get(key, default) 