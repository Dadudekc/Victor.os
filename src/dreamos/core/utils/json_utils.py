"""JSON utilities for Dream.OS."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

def load_json(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Load JSON file with error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {e}")
        return None

def save_json(file_path: Union[str, Path], data: Dict[str, Any], indent: int = 2) -> bool:
    """Save JSON file with error handling."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON file {file_path}: {e}")
        return False

def merge_json_files(file_paths: List[Union[str, Path]]) -> Optional[Dict[str, Any]]:
    """Merge multiple JSON files into one dictionary."""
    result = {}
    for file_path in file_paths:
        data = load_json(file_path)
        if data:
            result.update(data)
    return result if result else None

def json_to_string(data: Any, indent: Optional[int] = None) -> Optional[str]:
    """Convert data to JSON string with error handling."""
    try:
        return json.dumps(data, indent=indent)
    except Exception as e:
        logger.error(f"Error converting data to JSON string: {e}")
        return None

def string_to_json(json_str: str) -> Optional[Dict[str, Any]]:
    """Convert JSON string to dictionary with error handling."""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON string: {e}")
        return None
    except Exception as e:
        logger.error(f"Error converting JSON string to dictionary: {e}")
        return None 