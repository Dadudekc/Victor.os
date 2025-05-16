# Decorators (`src/dreamos/utils/decorators.py`)

## Overview

This module provides utility decorators to add common behaviors like retries to functions.

## Decorators

### `retry_on_exception`

```python
def retry_on_exception(
    max_attempts: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    delay: float = 1.0
) -> Callable[..., Any]:
```

*   **Purpose:** Automatically retries a **synchronous** function call if it raises one of the specified `exceptions`.
*   **Parameters:**
    *   `max_attempts`: Maximum number of times to try the function call (including the initial attempt).
    *   `exceptions`: A tuple of exception types to catch and trigger a retry.
    *   `delay`: Time in seconds to wait (`time.sleep`) before the next retry.
*   **Behavior:** Logs a warning on each failed attempt and retries after the delay. If `max_attempts` are reached, logs an error (with traceback) and re-raises the last caught exception.

### `async_retry_on_exception`

```python
def async_retry_on_exception(
    max_attempts: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    delay: float = 1.0
) -> Callable[..., Coroutine[Any, Any, Any]]:
```

*   **Purpose:** Automatically retries an **asynchronous** function (`async def`) call if it raises one of the specified `exceptions`.
*   **Parameters:** Same as `retry_on_exception`.
*   **Behavior:** Similar to `retry_on_exception`, but uses `asyncio.sleep` for non-blocking delays between retries. Logs warnings and errors similarly and re-raises the last exception on final failure.

## Usage Example

```python
from dreamos.utils.decorators import retry_on_exception, async_retry_on_exception
import asyncio

@retry_on_exception(max_attempts=3, exceptions=(IOError,), delay=0.5)
def read_flaky_sync_file(path):
    # ... code that might raise IOError ...
    pass

@async_retry_on_exception(max_attempts=2, exceptions=(TimeoutError,), delay=1.0)
async def call_flaky_async_api(url):
    # ... code that might raise TimeoutError ...
    pass
```

## Future Considerations

*   Implement exponential backoff for delays.
*   Allow passing a specific logger instance.
*   Optionally return a default value on final failure instead of re-raising. 