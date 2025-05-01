# src/dreamos/services/utils/retry_utils.py
# Placeholder for retry logic

import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def retry_selenium_action(
    max_attempts: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)
):
    """Placeholder decorator to satisfy imports. Does not actually retry."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # logger.debug(f"Placeholder retry decorator called for {func.__name__}. No retry logic active.")
            return func(*args, **kwargs)  # Execute the original function once

        return wrapper

    return decorator


# Ensure file ends with newline
