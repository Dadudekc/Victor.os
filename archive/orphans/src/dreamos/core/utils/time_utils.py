"""Time utilities for Dream.OS."""

from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Get current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)
