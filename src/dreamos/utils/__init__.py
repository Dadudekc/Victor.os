"""Core Dream.OS utility functions."""

# NOTE: Temporarily commenting out all relative imports here as they are causing
#       cascading failures after recent refactoring.
#       A dedicated task should be created to clean up src/dreamos/utils/
#       and its __init__.py.

# Import specific utilities instead of wildcard imports to avoid F403 and fix F401

# from .dream_mode_utils import load_dream_modes, select_dream_mode # Example if used
from .common_utils import (
    get_utc_iso_timestamp,
    load_json_file,
    save_json_file, # Assuming these are used
    load_yaml_file,
    save_yaml_file,
)
# from .coords import Coordinate, CoordinateManager, CoordsBaseModel # Import specific if needed
from .gui_utils import get_specific_coordinate # F401 fix - keep if used, remove if not
from .protocol_compliance_utils import (
    check_message_schema,
    check_task_schema,
    # ... import other needed functions ...
)
from .project_root import find_project_root # F401 fix - keep if used, remove if not
from .schema_validator import validate_schema # Import specific validator
from .search import fuzzy_find_file, regex_search_files # Import specific search functions
from .text import (
    extract_code_block,
    generate_uuid,
    # ... import other needed functions ...
)
from .validation import is_valid_uuid # Import specific validation

# Ensure all imported names are actually used in the codebase.
# If any `from .module import func` above results in F401 later, remove that line.

__all__ = [
    "get_utc_iso_timestamp",
    "load_json_file",
    "save_json_file",
    "load_yaml_file",
    "save_yaml_file",
    "get_specific_coordinate", # Remove if unused
    "check_message_schema",
    "check_task_schema",
    "find_project_root", # Remove if unused
    "validate_schema",
    "fuzzy_find_file",
    "regex_search_files",
    "extract_code_block",
    "generate_uuid",
    "is_valid_uuid",
    # Add specific names from coords, dream_mode_utils etc. if they are used and imported
    # Example: "CoordinateManager", "select_dream_mode"
]
