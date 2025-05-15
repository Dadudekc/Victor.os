"""List utilities for Dream.OS."""

from typing import Any, Callable, List, Optional, TypeVar, Union

T = TypeVar('T')

def chunk_list(lst: List[T], chunk_size: int) -> List[List[T]]:
    """Split list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def find_first(lst: List[T], predicate: Callable[[T], bool]) -> Optional[T]:
    """Find first element in list that matches predicate."""
    for item in lst:
        if predicate(item):
            return item
    return None

def remove_duplicates(lst: List[T]) -> List[T]:
    """Remove duplicate elements from list while preserving order."""
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

def flatten_list(lst: List[Any]) -> List[Any]:
    """Flatten nested list."""
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result

def filter_none(lst: List[Optional[T]]) -> List[T]:
    """Filter out None values from list."""
    return [item for item in lst if item is not None] 