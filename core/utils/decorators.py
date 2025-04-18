import time
import logging
from functools import wraps

MAX_ATTEMPTS = 3 # Default max attempts, can be overridden in decorator arguments

def retry_on_failure(max_attempts=MAX_ATTEMPTS, delay=2):
    """
    Decorator to retry a function on failure with exponential backoff.
    Logs warnings on failure and error after max attempts using standard logging.

    Args:
        max_attempts (int): Maximum number of attempts.
        delay (float): Base delay in seconds, multiplied by attempt number for backoff.
    """
    def decorator_retry(func):
        @wraps(func)
        def wrapper_retry(*args, **kwargs):
            logger = logging.getLogger(func.__module__ + '.' + func.__name__) # Get logger specific to the decorated function
            attempts = 0
            last_exception = None
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    last_exception = e
                    current_delay = delay * attempts
                    logger.warning(
                        f"Attempt {attempts}/{max_attempts} failed due to: {type(e).__name__} - {e}. "
                        f"Retrying in {current_delay:.2f} seconds..."
                    )
                    time.sleep(current_delay)
            
            error_msg = f"All {max_attempts} attempts failed. Last exception: {type(last_exception).__name__} - {last_exception}"
            logger.error(error_msg, exc_info=True) # Log with traceback
            # Re-raise the last exception to allow calling code to handle it if needed
            raise Exception(error_msg) from last_exception
        return wrapper_retry
    return decorator_retry 