"""Enum utilities for Dream.OS."""

from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar

T = TypeVar("T", bound=Enum)


def enum_to_dict(enum_class: Type[T]) -> Dict[str, Any]:
    """Convert enum class to dictionary."""
    return {member.name: member.value for member in enum_class}


def dict_to_enum(data: Dict[str, Any], enum_class: Type[T]) -> Dict[str, T]:
    """Convert dictionary to enum members."""
    return {k: enum_class(v) for k, v in data.items()}


def get_enum_member(enum_class: Type[T], value: Any) -> Optional[T]:
    """Get enum member by value."""
    try:
        return enum_class(value)
    except ValueError:
        return None


def get_enum_member_by_name(enum_class: Type[T], name: str) -> Optional[T]:
    """Get enum member by name."""
    try:
        return enum_class[name]
    except KeyError:
        return None


def get_enum_values(enum_class: Type[T]) -> List[Any]:
    """Get list of enum values."""
    return [member.value for member in enum_class]
