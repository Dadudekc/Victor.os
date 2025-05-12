"""Tests for example module."""

import subprocess
import sys
from pathlib import Path


def test_bad_function():
    from example import bad_function

    assert bad_function(1, 2) == 3


def test_unused_function():
    from example import unused_function

    assert unused_function() is None


def test_main_block():
    from example import bad_function

    assert bad_function(1, 2) == 3


def test_main_execution():
    """Test that running the script directly produces the expected output."""
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "example.py")],
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "3"
    assert result.returncode == 0
