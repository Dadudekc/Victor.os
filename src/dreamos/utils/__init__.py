"""Core Dream.OS utility functions."""

# NOTE: Temporarily commenting out all relative imports here as they are causing
#       cascading failures after recent refactoring.
#       A dedicated task should be created to clean up src/dreamos/utils/
#       and its __init__.py.

# Import specific utilities instead of wildcard imports to avoid F403 and fix F401

# from .dream_mode_utils import load_dream_modes, select_dream_mode # Example if used
from .common_utils import (  # load_json_file, # Removed - Does not exist in common_utils.py; save_json_file, # Removed - Assumed related and likely missing too; load_yaml_file, # Removed - Does not exist in common_utils.py; save_yaml_file, # Removed - Assumed related and likely missing too  # noqa: E501
    get_utc_iso_timestamp,
)

# from .coords import Coordinate, CoordinateManager, CoordsBaseModel # Import specific if needed  # noqa: E501
from .gui_utils import get_specific_coordinate  # F401 fix - keep if used, remove if not
from .project_root import find_project_root  # F401 fix - keep if used, remove if not

# from .protocol_compliance_utils import (  # ... import other needed functions ...
#     check_task_schema,
# )
from .schema_validator import validate_payload  # Import specific validator

# EDIT: Remove missing imports
# from .search import (  # Import specific search functions
#     fuzzy_find_file,
#     regex_search_files,
# )
from .search import run_ripgrep_search  # Import the existing function
from .text import sanitize_filename  # Import existing

# from .validation import is_valid_uuid  # REMOVED Import from deleted module

# Ensure all imported names are actually used in the codebase.
# If any `from .module import func` above results in F401 later, remove that line.

__all__ = [
    "get_utc_iso_timestamp",
    # "load_json_file", # Removed
    # "save_json_file", # Removed
    # "load_yaml_file", # Removed
    # "save_yaml_file", # Removed
    "get_specific_coordinate",  # Remove if unused
    # "check_task_schema",
    "find_project_root",  # Remove if unused
    "validate_payload",
    # EDIT: Remove missing entries, add existing
    # "fuzzy_find_file",
    # "regex_search_files",
    "run_ripgrep_search",
    "sanitize_filename",
    # "is_valid_uuid", # REMOVED reference
    # "validate_agent_id", # REMOVED non-existent reference
    # Add specific names from coords, dream_mode_utils etc. if they are used and imported  # noqa: E501
    # Example: "CoordinateManager", "select_dream_mode"
]
