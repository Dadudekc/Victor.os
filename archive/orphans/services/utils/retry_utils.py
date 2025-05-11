# src/dreamos/services/utils/retry_utils.py
# Placeholder for retry logic

import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def retry_selenium_action(
    max_attempts: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)
):
    """Decorator to retry a function call if it raises specified exceptions."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    logger.warning(
                        f"Attempt {attempts}/{max_attempts} failed for {func.__name__} due to {type(e).__name__}: {e}. Retrying in {delay}s..."
                    )
                    if attempts >= max_attempts:
                        logger.error(
                            f"Max retries ({max_attempts}) reached for {func.__name__}. Last error: {e}"
                        )
                        raise  # Re-raise the last exception
                    time.sleep(delay)
            # This part should not be reached if max_attempts > 0
            # but as a fallback, if max_attempts is 0 or negative, execute once.
            if max_attempts <= 0:
                return func(*args, **kwargs)
            return None  # Should be unreachable if max_attempts > 0

        return wrapper

    return decorator


# Ensure file ends with newline
