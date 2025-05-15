"""Function utilities for Dream.OS."""

import functools
import inspect
import logging
import time
from typing import Any, Callable, Dict, Optional, Type, TypeVar, cast

logger = logging.getLogger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None,
) -> Callable[[F], F]:
    """Retry decorator with configurable parameters."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if logger:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {str(e)}"
                        )
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
            if last_exception:
                raise last_exception
        return cast(F, wrapper)
    return decorator

def log_execution(logger: Optional[logging.Logger] = None) -> Callable[[F], F]:
    """Log function execution decorator."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                if logger:
                    logger.info(
                        f"{func.__name__} completed in {time.time() - start_time:.2f}s"
                    )
                return result
            except Exception as e:
                if logger:
                    logger.error(f"{func.__name__} failed: {str(e)}")
                raise
        return cast(F, wrapper)
    return decorator

def validate_args(func: F) -> F:
    """Validate function arguments against type annotations."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        for param_name, value in bound_args.arguments.items():
            param = sig.parameters[param_name]
            if param.annotation != inspect.Parameter.empty:
                if not isinstance(value, param.annotation):
                    raise TypeError(
                        f"Argument {param_name} must be of type {param.annotation.__name__}"
                    )
        return func(*args, **kwargs)
    return cast(F, wrapper)

def memoize(func: F) -> F:
    """Memoize function results."""
    cache: Dict[Any, Any] = {}
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        key = str((args, frozenset(kwargs.items())))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]
    return cast(F, wrapper)

def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None,
) -> Callable[[F], F]:
    """Async retry decorator with configurable parameters."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            import asyncio
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if logger:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {str(e)}"
                        )
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay)
            if last_exception:
                raise last_exception
        return cast(F, wrapper)
    return decorator 