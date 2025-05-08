"""
Utility to find the project root directory.

Provides a robust way to determine the project's root directory by searching
upwards for a common marker file or directory (e.g., '.git').
"""
from pathlib import Path


def find_project_root(marker_name: str = ".git") -> Path:
    """
    Finds the project root by searching upwards for a marker file/directory.

    Args:
        marker_name: The name of the marker file or directory (e.g., ".git", "pyproject.toml").

    Returns:
        The Path object representing the project root.

    Raises:
        FileNotFoundError: If the project root marker cannot be found.
    """
    current_dir = Path(__file__).resolve().parent
    while True:
        if (current_dir / marker_name).exists():
            return current_dir
        if current_dir.parent == current_dir: # Reached the filesystem root
            raise FileNotFoundError(
                f"Project root marker '{marker_name}' not found starting from {__file__}."
            )
        current_dir = current_dir.parent


# Example of usage, typically this would be imported and called by other modules.
# PROJECT_ROOT = find_project_root()
