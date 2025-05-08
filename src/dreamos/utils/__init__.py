"""Core Dream.OS utility functions."""

# FIXME: This __init__.py is mid-refactor. A dedicated task (e.g., TASK-UTILS-REFACTOR-INIT)
#        is needed to clean up imports, ensure all utilities are correctly exposed via __all__,
#        and remove the temporary refactoring comments below once submodules are stable.

# NOTE: Temporarily commenting out all relative imports here as they are causing
#       cascading failures after recent refactoring.
#       A dedicated task should be created to clean up src/dreamos/utils/
#       and its __init__.py.

# Import specific utilities instead of wildcard imports to avoid F403 and fix F401

# from .dream_mode_utils import load_dream_modes, select_dream_mode # Example if used
from .common_utils import (
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


# Ensure all imported names are actually used in the codebase.
# If any `from .module import func` above results in F401 later, remove that line.

__all__ = [
    "get_utc_iso_timestamp",
    "get_specific_coordinate",  # Remove if unused
    # "check_task_schema",
    "find_project_root",  # Remove if unused
    "validate_payload",
    "run_ripgrep_search",
    "sanitize_filename",
    # Add specific names from coords, dream_mode_utils etc. if they are used and imported  # noqa: E501
    # Example: "CoordinateManager", "select_dream_mode"
]
