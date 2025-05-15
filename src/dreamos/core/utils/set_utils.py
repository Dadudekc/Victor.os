"""Set utilities for Dream.OS."""

from typing import Any, Callable, List, Optional, Set, TypeVar

T = TypeVar('T')

def find_duplicates(items: List[T]) -> Set[T]:
    """Find duplicate items in a list."""
    seen = set()
    duplicates = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
    return duplicates

def filter_set(items: Set[T], predicate: Callable[[T], bool]) -> Set[T]:
    """Filter set using predicate."""
    return {item for item in items if predicate(item)}

def merge_sets(sets: List[Set[T]]) -> Set[T]:
    """Merge multiple sets."""
    result = set()
    for s in sets:
        result.update(s)
    return result

def find_common_elements(sets: List[Set[T]]) -> Set[T]:
    """Find common elements in multiple sets."""
    if not sets:
        return set()
    result = sets[0].copy()
    for s in sets[1:]:
        result.intersection_update(s)
    return result

def find_unique_elements(sets: List[Set[T]]) -> Set[T]:
    """Find elements that appear in only one set."""
    if not sets:
        return set()
    all_elements = merge_sets(sets)
    common_elements = find_common_elements(sets)
    return all_elements - common_elements 