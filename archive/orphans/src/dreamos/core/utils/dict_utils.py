"""Dictionary utilities for Dream.OS."""

from typing import Any, Dict, List, Optional, TypeVar, Union

T = TypeVar("T")


def get_nested_value(
    data: Dict[str, Any], path: str, default: Optional[T] = None
) -> Union[Any, T]:
    """Get value from nested dictionary using dot notation path."""
    try:
        for key in path.split("."):
            data = data[key]
        return data
    except (KeyError, TypeError):
        return default


def set_nested_value(data: Dict[str, Any], path: str, value: Any) -> None:
    """Set value in nested dictionary using dot notation path."""
    keys = path.split(".")
    for key in keys[:-1]:
        if key not in data:
            data[key] = {}
        data = data[key]
    data[keys[-1]] = value


def merge_dicts(dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple dictionaries, later values override earlier ones."""
    result = {}
    for d in dicts:
        result.update(d)
    return result


def flatten_dict(data: Dict[str, Any], separator: str = ".") -> Dict[str, Any]:
    """Flatten nested dictionary using separator in keys."""
    result = {}

    def _flatten(d: Dict[str, Any], prefix: str = "") -> None:
        for key, value in d.items():
            new_key = f"{prefix}{separator}{key}" if prefix else key
            if isinstance(value, dict):
                _flatten(value, new_key)
            else:
                result[new_key] = value

    _flatten(data)
    return result


def filter_dict(data: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    """Filter dictionary to only include specified keys."""
    return {k: v for k, v in data.items() if k in keys}
