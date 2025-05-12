"""Tests for example module."""


def test_bad_function():
    """Test that bad_function adds numbers correctly."""
    from example import bad_function

    assert bad_function(1, 2) == 3


def test_unused_function():
    """Test that unused_function returns None."""
    from example import unused_function

    assert unused_function() is None


def test_main_block():
    """Test that main block produces correct output."""
    from example import bad_function

    assert bad_function(1, 2) == 3
