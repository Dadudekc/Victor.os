# src/dreamos/utils/decorators.py
import functools
import logging
import time

logger = logging.getLogger(__name__)


def retry_on_exception(max_attempts=3, exceptions=(Exception,), delay=1):
    """Basic placeholder decorator for retry logic."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts due to {e}.",  # noqa: E501
                            exc_info=True,
                        )
                        raise
                    logger.warning(
                        f"Attempt {attempts}/{max_attempts} failed for {func.__name__} due to {e}. Retrying in {delay}s..."  # noqa: E501
                    )
                    time.sleep(delay)

        return wrapper

    return decorator
