import time
import asyncio
import logging
from typing import Any, Callable, Coroutine, Tuple, Type

logger = logging.getLogger(__name__)

def retry_on_exception(
    max_attempts: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    delay: float = 1.0
) -> Callable[..., Any]:
    """Automatically retries a synchronous function call if it raises specified exceptions."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed: {e}")
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
            logger.error(f"All {max_attempts} attempts failed. Raising last exception.", exc_info=True)
            raise last_exception
        return wrapper
    return decorator

def async_retry_on_exception(
    max_attempts: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    delay: float = 1.0
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Automatically retries an async function call if it raises specified exceptions."""
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(f"Async attempt {attempt + 1}/{max_attempts} failed: {e}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay)
            logger.error(f"All {max_attempts} async attempts failed. Raising last exception.", exc_info=True)
            raise last_exception
        return wrapper
    return decorator 