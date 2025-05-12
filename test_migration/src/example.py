"""Example module for testing."""


def bad_function(a, b):
    """Add two numbers."""
    return a + b


def unused_function():
    """Do nothing."""
    return None


if __name__ == "__main__":
    print(bad_function(1, 2))
