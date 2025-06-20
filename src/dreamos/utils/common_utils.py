"""
Common utilities for the Dream.OS system.
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
import json
import hashlib
import os
import logging


def get_utc_iso_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    timestamp = get_utc_iso_timestamp()
    hash_value = hashlib.md5(timestamp.encode()).hexdigest()[:8]
    return f"{prefix}{hash_value}" if prefix else hash_value


def safe_json_dumps(obj: Any, default: Optional[Any] = None) -> str:
    """Safely serialize object to JSON string."""
    try:
        return json.dumps(obj, default=default or str)
    except (TypeError, ValueError):
        return json.dumps({"error": "Could not serialize object"})


def safe_json_loads(json_str: str) -> Optional[Any]:
    """Safely deserialize JSON string."""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None


def ensure_directory(path: str) -> bool:
    """Ensure directory exists, create if it doesn't."""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError:
        return False


def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes."""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except OSError:
        return 0.0


def setup_logging(name: str, level: int = logging.INFO, 
                 log_file: Optional[str] = None) -> logging.Logger:
    """Setup a logger with console and optional file output."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any], 
                deep: bool = True) -> Dict[str, Any]:
    """Merge two dictionaries, with dict2 taking precedence."""
    if not deep:
        return {**dict1, **dict2}
    
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value, deep=True)
        else:
            result[key] = value
    
    return result


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> list:
    """Validate that required fields are present in data."""
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)
    return missing_fields


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage."""
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"
    
    return filename


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def retry_on_exception(func, max_retries: int = 3, delay: float = 1.0, 
                      exceptions: tuple = (Exception,)):
    """Decorator to retry function on exception."""
    import time
    
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < max_retries - 1:
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
        raise last_exception
    
    return wrapper 