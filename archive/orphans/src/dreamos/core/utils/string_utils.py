"""String utilities for Dream.OS."""

import re
from typing import List, Optional


def normalize_string(text: str) -> str:
    """Normalize string by removing special characters and converting to lowercase."""
    return re.sub(r"[^a-zA-Z0-9]", "", text.lower())


def split_camel_case(text: str) -> List[str]:
    """Split camel case string into words."""
    return re.findall(r"[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z][a-z]|\d|\W|$))|[a-z]+", text)


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to max length with suffix."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def extract_between(text: str, start: str, end: str) -> Optional[str]:
    """Extract text between start and end markers."""
    try:
        start_idx = text.index(start) + len(start)
        end_idx = text.index(end, start_idx)
        return text[start_idx:end_idx]
    except ValueError:
        return None
