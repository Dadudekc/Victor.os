"""Logging utilities for DreamOS."""

import logging
import traceback
from typing import Any, Dict

logger = logging.getLogger(__name__)


def log_handler_exception(handler: Any, event_data: Dict[str, Any], exception: Exception):
    """Logs exceptions occurring within event handlers.

    Args:
        handler: The handler function/method where the exception occurred.
        event_data: The data associated with the event being handled.
        exception: The exception object that was caught.
    """
    try:
        # Attempt to get a meaningful name for the handler
        handler_name = getattr(handler, '__qualname__', getattr(handler, '__name__', str(handler)))
    except Exception:
        handler_name = "unknown_handler"

    # Format the traceback
    exc_traceback = traceback.format_exc()

    # Log the error with context
    # Consider adding more event context if available (e.g., event type, source)
    logger.error(
        f"Exception caught in handler '{handler_name}' while processing event.\n"
        f"Handler: {handler}\n"
        f"Event Data Keys: {list(event_data.keys())}\n"
        f"Exception Type: {type(exception).__name__}\n"
        f"Exception Args: {exception.args}\n"
        f"Traceback:\n{exc_traceback}"
    )
    # NOTE: This function now requires the 'exception' object to be passed.
    # Integration point: Call this function within except blocks in event dispatch logic.
