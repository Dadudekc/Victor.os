"""Coordinate utility functions for Dream.OS GUI automation/calibration."""

import json
from pathlib import Path
from typing import Any, Dict


def load_coordinates(path: str | Path) -> Dict[str, Any]:
    """Load coordinates from a JSON file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Coordinate file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_coordinates(path: str | Path, coords: Dict[str, Any]) -> None:
    """Save coordinates to a JSON file."""
    path = Path(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(coords, f, indent=2)
