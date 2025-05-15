"""Tuple utilities for Dream.OS."""

from typing import Any, Callable, List, Optional, Tuple, TypeVar

T = TypeVar('T')

def find_first_matching(tuples: List[Tuple[Any, ...]], predicate: Callable[[Tuple[Any, ...]], bool]) -> Optional[Tuple[Any, ...]]:
    """Find first tuple that matches predicate."""
    for t in tuples:
        if predicate(t):
            return t
    return None

def filter_tuples(tuples: List[Tuple[Any, ...]], predicate: Callable[[Tuple[Any, ...]], bool]) -> List[Tuple[Any, ...]]:
    """Filter tuples using predicate."""
    return [t for t in tuples if predicate(t)]

def merge_tuples(tuples: List[Tuple[T, ...]]) -> Tuple[T, ...]:
    """Merge multiple tuples into one."""
    result = []
    for t in tuples:
        result.extend(t)
    return tuple(result)

def split_tuple(t: Tuple[Any, ...], index: int) -> Tuple[Tuple[Any, ...], Tuple[Any, ...]]:
    """Split tuple at index."""
    return t[:index], t[index:]

def remove_duplicates(t: Tuple[T, ...]) -> Tuple[T, ...]:
    """Remove duplicate elements from tuple while preserving order."""
    seen = set()
    result = []
    for item in t:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return tuple(result) 