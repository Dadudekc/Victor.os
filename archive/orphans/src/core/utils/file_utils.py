"""File management utilities for Dream.os."""

import json
from pathlib import Path
from typing import Any, Dict, Union  # Optional was not used after cleanup


class FileManager:
    """Manages file operations with error handling and validation."""

    def __init__(self, base_dir: Union[str, Path]):
        self.base_dir = Path(base_dir)
        if not self.base_dir.exists():
            self.base_dir.mkdir(parents=True)

    def read_json(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        full_path = self.base_dir / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path}")
        with open(full_path, "r") as f:
            return json.load(f)

    def write_json(self, file_path: Union[str, Path], data: Dict[str, Any]) -> None:
        full_path = self.base_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w") as f:
            json.dump(data, f, indent=2)

    def ensure_dir(self, dir_path: Union[str, Path]) -> Path:
        full_path = self.base_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        return full_path

    def list_files(self, dir_path: Union[str, Path], pattern: str = "*") -> list[Path]:
        full_path = self.base_dir / dir_path
        if not full_path.exists():
            return []
        return list(full_path.glob(pattern))

    def delete_file(self, file_path: Union[str, Path]) -> bool:
        full_path = self.base_dir / file_path
        if full_path.exists():
            full_path.unlink()
            return True
        return False
