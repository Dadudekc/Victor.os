"""
Common, generic utilities for the Dream.OS project.
Includes retry logic and potentially other cross-cutting concerns.
"""

import logging
import time
import asyncio # Import asyncio
from functools import wraps
from typing import Any, Callable, Optional, TypeVar
from .logging_utils import get_logger # Use relative import assuming it's in the same package

# Configure logging for this utility module
logger = get_logger(__name__)

# Type variables for generic functions
ReturnType = TypeVar('ReturnType')

# Kept retry_on_exception as a generic utility
def retry_on_exception(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Retry decorator for functions that may fail temporarily.
    Handles both synchronous and asynchronous functions.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function that implements retry logic
    """
    def decorator(func: Callable[..., ReturnType]) -> Callable[..., ReturnType]:
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> ReturnType:
                current_delay = delay
                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs) # Await the async function
                    except exceptions as e:
                        if attempt == max_attempts - 1:
                            logger.error(
                                f"Async function {func.__name__} failed after {max_attempts} attempts. Final error: {e}",
                                exc_info=True
                            )
                            raise
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for async {func.__name__}: {e}. Retrying in {current_delay:.2f}s..."
                        )
                        await asyncio.sleep(current_delay) # Use async sleep
                        current_delay *= backoff
                # This line should not be reached
                raise RuntimeError(f"Async retry logic failed unexpectedly after {max_attempts} attempts for {func.__name__}")
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> ReturnType:
                current_delay = delay
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs) # Call the sync function
                    except exceptions as e:
                        if attempt == max_attempts - 1:
                            logger.error(
                                f"Sync function {func.__name__} failed after {max_attempts} attempts. Final error: {e}",
                                exc_info=True
                            )
                            raise
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for sync {func.__name__}: {e}. Retrying in {current_delay:.2f}s..."
                        )
                        time.sleep(current_delay) # Use sync sleep
                        current_delay *= backoff
                # This line should not be reached
                raise RuntimeError(f"Sync retry logic failed unexpectedly after {max_attempts} attempts for {func.__name__}")
            return sync_wrapper
    return decorator

# Removed log_event (duplicate of utils.logging_utils.log_event)
# Removed wait_and_find_element (duplicate of utils.selenium_utils.wait_for_element)
# Removed wait_and_click (duplicate of utils.selenium_utils.safe_click)
# Removed wait_and_send_keys (duplicate of utils.selenium_utils.safe_send_keys)
# Removed is_element_present (similar logic possible via wait_for_element) 
