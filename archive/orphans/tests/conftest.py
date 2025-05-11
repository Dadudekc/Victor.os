# tests/conftest.py
import os
import sys

# Ensure project root is on sys.path so that core and other packages are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Also add 'src' directory to sys.path so that the 'dreamos' package under src is importable  # noqa: E501
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

# allowed_dirs specifies which test slices to collect; memory slice unlocked below
allowed_dirs = [
    "/tests/utils",
    "tests/utils",
    "/tests/monitoring",
    "tests/monitoring",
    "/tests/coordination/cursor",
    "tests/coordination/cursor",
    "/tests/core/coordination",
    "tests/core/coordination",
    "/tests/core/monitoring",
    "tests/core/monitoring",
    # '/tests/memory', 'tests/memory'  # memory slice entries commented out to unlock tests  # noqa: E501
]
