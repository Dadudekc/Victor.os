from pathlib import Path

# EDIT START: Minimal viable project root finder for CLI compatibility


def find_project_root() -> Path:
    """Returns the project root based on current file location."""
    return Path(__file__).resolve().parent.parent.parent.parent


# EDIT END
