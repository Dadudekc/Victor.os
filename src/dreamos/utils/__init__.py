"""Core Dream.OS utility functions."""

# NOTE: Temporarily commenting out all relative imports here as they are causing
#       cascading failures after recent refactoring.
#       A dedicated task should be created to clean up src/dreamos/utils/
#       and its __init__.py.
# REFACTOR Agent-7: Apply model failed to remove commented lines below (load/save json/yaml). Remove manually.  # noqa: E501

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
from .schema_validator import validate_schema  # Import specific validator
from .search import (  # Import specific search functions
    fuzzy_find_file,
    regex_search_files,
)
from .text import (  # ... import other needed functions ...
    extract_code_block,
    generate_uuid,
)
from .validation import is_valid_uuid  # Import specific validation

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
    "validate_schema",
    "fuzzy_find_file",
    "regex_search_files",
    "extract_code_block",
    "generate_uuid",
    "is_valid_uuid",
    "validate_agent_id",
    # Add specific names from coords, dream_mode_utils etc. if they are used and imported  # noqa: E501
    # Example: "CoordinateManager", "select_dream_mode"
]
