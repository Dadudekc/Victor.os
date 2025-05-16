"""Common utility functions used throughout Dream.OS."""

from datetime import datetime
from typing import Optional


def get_utc_iso_timestamp() -> str:
    """Get current UTC timestamp in ISO format.

    Returns:
        str: ISO formatted timestamp
    """
    return datetime.utcnow().isoformat()


def validate_iso_timestamp(timestamp: str) -> bool:
    """Validate ISO timestamp format.

    Args:
        timestamp: ISO timestamp string to validate

    Returns:
        bool: True if valid ISO timestamp
    """
    try:
        datetime.fromisoformat(timestamp)
        return True
    except ValueError:
        return False


def parse_iso_timestamp(timestamp: str) -> Optional[datetime]:
    """Parse ISO timestamp string to datetime object.

    Args:
        timestamp: ISO timestamp string

    Returns:
        Optional[datetime]: Parsed datetime or None if invalid
    """
    try:
        return datetime.fromisoformat(timestamp)
    except ValueError:
        return None
