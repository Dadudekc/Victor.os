# Dream.OS Logging - Developer Notes

## 1. Overview

<!-- LEGACY PATH: _agent_coordination/core/utils/logging.py -->
The Dream.OS logging system, managed by `LogManager` (verify location, likely under `src/dreamos/core/utils/`), provides a centralized and structured way to record events across the application. It aims for:

*   **Consistency:** Standardized format and retrieval.
*   **Observability:** Dual output to console (human-readable) and file (structured JSON Lines).
*   **Maintainability:** Log rotation and component tagging.

## 2. Configuration

Logging is configured during application startup, likely by a setup function called from the main entry point (e.g., `src/dreamos/main.py` or `cli.py`). This involves setting up handlers and formatters.

*(Verify exact configuration mechanism, potentially in `src/dreamos/config.py` or setup code)*

Key configuration aspects (Verify defaults):

*   **Log Directory:** Set to `logs/` relative to the workspace root.
*   **Console Handler:**
    *   Level: `INFO` by default.
    *   Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s` (Verify format)
*   **File Handler (`logs/agent.log`):**
    *   Level: `DEBUG` by default.
    *   Format: JSON Lines (see below).
    *   Rotation: 10MB file size limit, 5 backup files kept (Verify settings).

## 3. Retrieving a Logger

Use the standard Python `logging.getLogger()` function. It's recommended to configure the root logger or use a helper function if provided (verify existence and location, e.g., `src/dreamos/core/utils/logger.py`).

```python
import logging

# Best practice: Use __name__ for the logger name
logger = logging.getLogger(__name__)

# If using a custom setup with component tagging:
# logger = get_logger(__name__, component="MyComponent") # Verify function/method

# Example usage
logger.info("Initialization complete.")
logger.debug("Detailed state: %s", complex_object)
try:
    # ... some operation ...
    raise ValueError("Something went wrong")
except ValueError as e:
    logger.error("Failed to process task %s: %s", task_id, e, exc_info=True) # Include exception traceback
```

*   **`name`:** Typically `__name__` of the module using the logger. Appears in console/file logs.
*   **`component`:** *(Verify if still used)* A string identifier added to structured logs.

## 4. Structured Log Format (`agent.log`)

Log entries in `logs/agent.log` are JSON objects, one per line (JSON Lines format). *(Verify if format is still JSON Lines and confirm fields)*

**Example JSON Entry (Current structure needs verification):**

```json
{
  "timestamp": "2023-10-27T10:30:15.123456",
  "level": "INFO",
  "component": "MyComponent", 
  "message": "Initialization complete.",
  "logger": "src.dreamos.module.submodule",
  "extra": {} 
}
```

**Example Error Entry (Current structure needs verification):**

```json
{
  "timestamp": "2023-10-27T10:35:02.987654",
  "level": "ERROR",
  "component": "AnotherComponent",
  "message": "Failed to process task 123: Something went wrong",
  "logger": "src.dreamos.other_module",
  "file": "src/dreamos/other_module.py", 
  "line": 50,
  "function": "process_task",
  "exception": {
    "type": "ValueError",
    "message": "Something went wrong",
    "traceback": "Traceback (most recent call last):\n..."
  }
}
```

**Fields (Verify current fields):**

*   `timestamp`: ISO 8601 format timestamp.
*   `level`: Log level name.
*   `component`: *(Verify)* Component name if used.
*   `message`: The formatted log message.
*   `logger`: The name of the logger.
*   `file`, `line`, `function`: Included for `ERROR` level and above.
*   `exception`: Included if `exc_info=True` was passed.
*   `extra`: Additional context passed via `extra={...}`.

## 5. Log Rotation & Management

*   Log rotation is likely handled by `logging.handlers.RotatingFileHandler` (Verify).
*   Configuration (max size, backup count) is set during initial setup (Verify location and current values).

---
*Ensure logging is configured early in the application lifecycle.* 