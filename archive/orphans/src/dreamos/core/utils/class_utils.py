"""Class utilities for Dream.OS."""

import inspect
from typing import Any, Dict, List, Optional, Type, TypeVar

T = TypeVar("T")


def get_class_methods(cls: Type[Any]) -> List[str]:
    """Get list of class method names."""
    return [name for name, _ in inspect.getmembers(cls, predicate=inspect.ismethod)]


def get_class_attributes(cls: Type[Any]) -> List[str]:
    """Get list of class attribute names."""
    return [
        name for name, _ in inspect.getmembers(cls, lambda x: not inspect.isroutine(x))
    ]


def get_method_signature(
    cls: Type[Any], method_name: str
) -> Optional[inspect.Signature]:
    """Get method signature."""
    try:
        method = getattr(cls, method_name)
        return inspect.signature(method)
    except (AttributeError, ValueError):
        return None


def get_class_hierarchy(cls: Type[Any]) -> List[Type[Any]]:
    """Get class inheritance hierarchy."""
    hierarchy = []
    current_cls = cls
    while current_cls is not object:
        hierarchy.append(current_cls)
        current_cls = current_cls.__base__
    return hierarchy


def get_class_annotations(cls: Type[Any]) -> Dict[str, Any]:
    """Get class type annotations."""
    return cls.__annotations__ if hasattr(cls, "__annotations__") else {}
