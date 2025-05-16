"""Error utilities for Dream.OS."""

import logging
import traceback
from typing import Optional, Tuple, Type

logger = logging.getLogger(__name__)


def handle_error(
    error: Exception,
    error_type: Optional[Type[Exception]] = None,
    error_message: Optional[str] = None,
) -> Tuple[bool, str]:
    """Handle error and return status and message."""
    if error_type and not isinstance(error, error_type):
        logger.error(f"Unexpected error type: {type(error)}")
        return False, f"Unexpected error: {str(error)}"

    if error_message:
        logger.error(f"{error_message}: {str(error)}")
        return False, f"{error_message}: {str(error)}"

    logger.error(f"Error: {str(error)}")
    return False, str(error)


def get_error_details(error: Exception) -> str:
    """Get detailed error information."""
    return f"{type(error).__name__}: {str(error)}\n{traceback.format_exc()}"
