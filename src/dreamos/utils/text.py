"""Utilities for text processing and manipulation."""

import logging
import re

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str, max_length: int = 50) -> str:
    """Replaces potentially problematic filename characters with underscores.

    Also trims leading/trailing underscores/spaces and limits length.
    Args:
        filename: The original filename string.
        max_length: The maximum allowed length for the sanitized filename.

    Returns:
        A sanitized filename string safe for most filesystems.
    """
    if not filename:
        return "default_filename"

    # Remove or replace invalid characters (common across OS)
    # Allow alphanumeric, underscore, hyphen, dot
    sanitized = re.sub(r"[^\w\-\.]+", "_", filename)

    # Remove leading/trailing underscores and dots that might result
    sanitized = sanitized.strip("_.")

    # Replace multiple consecutive underscores/dots with a single one
    sanitized = re.sub(r"[_\.]+", "_", sanitized)

    # Ensure filename is not empty after sanitization
    if not sanitized:
        sanitized = "default_filename"

    # Limit length (take beginning part)
    sanitized = sanitized[:max_length]

    # Final trim just in case the slicing resulted in trailing dot/underscore
    sanitized = sanitized.strip("_.")

    # Ensure it's not empty AGAIN after final trim
    if not sanitized:
        sanitized = "default_filename"

    logger.debug(f"Sanitized filename: '{filename}' -> '{sanitized}'")
    return sanitized
