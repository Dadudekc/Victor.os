# Dream.OS Error Handling Standard

**Version:** 1.0
**Status:** ACTIVE
**Owner:** Agent4 / AgentGemini (Consolidated)
**Dependencies:** ORG-LOGGING-STD-001 (for logging format alignment)

## 1. Goals

- Promote consistent and predictable error handling across the Dream.OS codebase.
- Improve diagnosability of issues through clear error types and context.
- Enhance system robustness by standardizing retry logic and error propagation.

## 2. Core Principles

- **Fail Fast, Fail Explicitly:** Prefer raising specific exceptions over returning ambiguous error codes (`None`, `False`) from core functions or utilities, unless the function's documented contract explicitly defines non-exceptional failure modes (e.g., a search returning no results).
- **Be Specific (Catching):** Catch the most specific exception type possible. Avoid overly broad `except` clauses like `except Exception:` where feasible, and *never* use bare `except:`.
- **Provide Context:** Errors should include sufficient context for diagnosis. Utilize exception wrapping (`raise MyError(...) from original_exception`) to preserve the original cause.
- **Log Meaningfully:** When errors are caught and handled (or just before re-raising/wrapping), log them with sufficient context. Use `logging.exception()` for unexpected errors to capture tracebacks.
- **Don't Swallow Errors:** Avoid catching exceptions only to ignore them (`pass`) unless there is a very deliberate and documented reason (e.g., optional cleanup actions).
- **Distinguish Error Types:** Use custom exceptions (see hierarchy below) to differentiate between different categories of errors (e.g., configuration vs. I/O vs. validation).
- **Leverage Standard Logging:** Use the configured Python `logging` module consistently as defined in `docs/logging.md`.

## 3. Standard Exception Hierarchy (Proposal)

A base exception class should be defined to allow catching all application-specific errors. Component-specific errors should inherit from this base or relevant built-in types.

```python
# Located potentially in src/dreamos/core/errors.py

class DreamOSError(Exception):
    """Base class for all Dream.OS specific exceptions."""
    pass

class ConfigurationError(DreamOSError):
    """Errors related to configuration loading or validation."""
    pass

class ToolError(DreamOSError):
    """Errors related to external tool execution or interaction."""
    pass

class CommunicationError(DreamOSError):
    """Errors related to inter-agent communication (Mailbox, AgentBus)."""
    pass

class MemoryError(DreamOSError):
    """Errors related to memory component operations."""
    pass

# Example usage:
# raise ConfigurationError("Missing required setting 'API_KEY'")
# raise ToolError("Failed to execute 'git status'") from os.OSError
```

Component-specific exceptions already defined (e.g., `AdapterError`, `ValidationError`, `SummarizationError`) should ideally be reviewed to inherit from `DreamOSError` or a more specific subclass if appropriate.

## 4. Raising vs. Returning Errors

- **General Rule:** Functions performing an action that can fail unexpectedly should `raise` a specific exception (ideally inheriting from `DreamOSError` or a standard Python exception like `ValueError`, `TypeError`, `IOError`).
- **Exceptions to Raising:**
    - Functions explicitly designed to check existence or state (e.g., `is_valid()`, `task_exists()`) may return `bool`.
    - Functions explicitly designed to search/retrieve data may return `None` or an empty collection (`[]`, `{}`) if not finding data is a documented, non-erroneous outcome. Document this clearly.
- **Avoid:** Returning generic error codes or strings. Relying solely on logs to signal failure without raising an exception.

## 5. Exception Wrapping

- When catching an exception from a lower-level operation (library call, I/O, etc.) and raising a higher-level application error, **always** use the `raise NewException(...) from original_exception` syntax. This preserves the full context for debugging.

```python
# Example
try:
    # Low-level operation
    result = low_level_api.do_something()
except LowLevelError as e:
    logger.error("Low level operation failed during high level task.")
    raise HighLevelTaskError("Failed to complete high level task due to API failure") from e
```

## 6. Handling Exceptions (Catching & Logging)

- **Catch Specific Exceptions:** Replace generic `except Exception:` with more specific built-in exceptions (`ValueError`, `TypeError`, `IOError`, `FileNotFoundError`, `KeyError`, etc.) or custom application exceptions (e.g., `ConfigurationError`, `ToolError`) wherever possible.
    - **Example (Bad):**
      ```python
      try:
          # ... some operation ...
      except Exception:
          print("An error occurred") # Lacks detail, type, uses print
      ```
    - **Example (Good):**
      ```python
      import logging
      from .errors import ConfigurationError # Assuming custom errors defined
      logger = logging.getLogger(__name__)

      try:
          # ... some operation that might raise KeyError or FileNotFoundError ...
      except KeyError as e:
          # Log specific error, potentially wrap if needed
          logger.error(f"Configuration key missing: {e}")
          # raise ConfigurationError(f"Missing key: {e}") from e
      except FileNotFoundError as e:
           logger.error(f"Required file not found: {e.filename}")
           # raise MySpecificError(...) from e
      ```
- **Log Exceptions Properly:** When catching broad exceptions is necessary (e.g., interacting with external libraries, top-level handlers), **always** log the full exception information using `logging.exception()`.
    - **Example (Bad):**
      ```python
      try:
          # ... external call ...
      except Exception as e:
          logger.error(f"External call failed: {e}") # Traceback is lost
      ```
    - **Example (Good):**
      ```python
      try:
          # ... external call ...
      except Exception as e:
          # Logs ERROR level message and includes exception traceback automatically
          logger.exception("External call failed unexpectedly.")
          # Optionally re-raise wrapped exception
          # raise CommunicationError("External call failed") from e
      ```
- **Avoid Bare `except:`:** Never use `except:` without specifying an exception type. It catches *all* exceptions, including system-exiting ones like `SystemExit` or `KeyboardInterrupt`, making the program difficult to terminate cleanly.

## 7. Retry Logic

- For operations prone to transient failures (network requests, UI interactions), utilize the existing `src.dreamos.core.utils.core.RetryManager`.
- Configure `RetryManager` with appropriate `max_retries`, delays, and specific `retry_on_exceptions` tuple.
- Avoid implementing custom retry loops unless `RetryManager` is unsuitable for the specific use case (document rationale clearly).

## 8. Logging Errors (Standard Practice Recap)

- Use `logger.error(...)` for handled errors where operation might continue.
- Use `logger.exception(...)` for handled errors where traceback is important OR for unexpected errors caught in broad handlers.
- Follow format/destination standards defined in `docs/logging.md`.

## 9. TODO / Future Considerations

- Review existing custom exceptions (`AdapterError`, `LockDirectoryError`, `ValidationError`, etc.) for alignment with the proposed `DreamOSError` hierarchy. Create refactoring tasks if needed.
- Define standard logging format for exceptions (ORG-LOGGING-STD-001).
- Refactor specific code sections identified during initial analysis to align with these standards.
- Add examples for specific components (e.g., AgentBus error handling).

## 10. Identified Refactoring Candidates (Initial Pass)

The following areas were identified as potentially deviating from these guidelines and may warrant specific refactoring tasks:

- **`src/dreamos/utils/coords.py` (`get_coordinate`):** Currently returns `None` on generic `Exception`. Should raise specific errors (e.g., `ValueError`, custom `CoordinateAccessError(DreamOSError)`).
- **`src/dreamos/tools/discovery/archive_defunct_tests.py`:** Suppresses `OSError`/`Exception`/`IOError` by logging and incrementing counts instead of raising. Should raise an appropriate summary exception upon significant failures.
- **`src/dreamos/tools/dreamos_utils/check_agent_pulse.py`:** Returns errors as strings in a list instead of raising specific exceptions (e.g., `CommunicationError`).
- **Existing Custom Exceptions:** Need review to ensure inheritance from `DreamOSError` or appropriate subclasses:
    - `AdapterError` (`llm_bridge/bridge_adapters/base_adapter.py`)
    - `LockDirectoryError`, `LockAcquisitionError` (`core/utils/file_locking.py`)
    - `ValidationError` (`utils/validation.py`)
    - `ConfigError` (`config.py`)
    - `SummarizationError` (`memory/summarization_utils.py`)
    - `CompactionError` (`memory/compaction_utils.py`)
    - `ProjectBoardManagerError` (`core/comms/project_board.py`)
    - `CursorOrchestratorError` (`automation/cursor_orchestrator.py`)
