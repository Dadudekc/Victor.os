# src/dreamos/utils/decorators.py
import asyncio
import functools
import logging
import time
from typing import Any, Callable, Coroutine, Tuple, Type

logger = logging.getLogger(__name__)


def retry_on_exception(
    max_attempts: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    delay: float = 1.0,
):
    """Decorator to retry a **synchronous** function if specific exceptions occur."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempts = 0
            last_exception = None
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    attempts += 1
                    if attempts >= max_attempts:
                        logger.error(
                            f"Sync function {func.__qualname__} failed after {max_attempts} attempts due to {type(e).__name__}.",
                            exc_info=True,
                        )
                        raise
                    logger.warning(
                        f"Attempt {attempts}/{max_attempts} failed for {func.__qualname__} due to {type(e).__name__}: {e}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
            if last_exception:
                raise last_exception
            return None

        return wrapper

    return decorator


def async_retry_on_exception(
    max_attempts: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    delay: float = 1.0,
):
    """Decorator to retry an **asynchronous** function if specific exceptions occur."""

    def decorator(
        func: Callable[..., Coroutine[Any, Any, Any]],
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempts = 0
            last_exception = None
            while attempts < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    attempts += 1
                    if attempts >= max_attempts:
                        logger.error(
                            f"Async function {func.__qualname__} failed after {max_attempts} attempts due to {type(e).__name__}.",
                            exc_info=True,
                        )
                        raise
                    logger.warning(
                        f"Attempt {attempts}/{max_attempts} failed for {func.__qualname__} due to {type(e).__name__}: {e}. Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
            if last_exception:
                raise last_exception
            return None

        return wrapper

    return decorator
