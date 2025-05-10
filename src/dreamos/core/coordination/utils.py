"""Coordination Utilities"""
import asyncio
import logging
import traceback
from functools import wraps
from typing import Any, Callable, Dict, Optional

# Imports needed by decorators (verify paths)
# from dreamos.core.memory.governance_memory_engine import log_event # COMMENTED OUT
from ...monitoring.performance_logger import PerformanceLogger
# Attempt to import error classes from agents.utils - might cause cycle?
# If so, these errors might need to move to core.errors
# REMOVED try/except block and fallback definitions
# try:
#    from dreamos.agents.utils.agent_utils import AgentError, TaskProcessingError, MessageHandlingError
# except ImportError:
#    # Fallback if agents.utils cannot be imported (e.g. during core init)
#    # Define minimal versions here? Or raise config error?
#    class AgentError(Exception): pass
#    class TaskProcessingError(AgentError): pass
#    class MessageHandlingError(AgentError): pass
#    logging.getLogger(__name__).warning("Could not import error classes from dreamos.agents.utils. Fallback definitions used.")

# ADDED import from core.errors
from ..errors import AgentError

util_logger = logging.getLogger("core.coordination.utils")


def with_error_handling(error_class: type = AgentError):
    """Decorator for functions that need standardized error handling and logging."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Identify self/agent_id if method is called on an agent instance
            agent_id = "unknown_agent"
            if args and hasattr(args[0], "agent_id"):
                agent_id = args[0].agent_id
            elif "self" in kwargs and hasattr(kwargs["self"], "agent_id"):
                agent_id = kwargs["self"].agent_id

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Log the error using standard logger if available on self, otherwise use util_logger
                logger_instance = getattr(
                    args[0] if args else None, "logger", util_logger
                )

                error_msg = f"test" # Simplified f-string for diagnosis
                logger_instance.error(error_msg, exc_info=True)

                # Log governance event - COMMENTED OUT
                # error_details = {
                #     "error": str(e),
                #     "traceback": traceback.format_exc(),
                #     "function": func.__name__,
                #     "args": str(args[1:]) if args else "()",  # Don't log self
                #     "kwargs": str(kwargs),
                # }
                # try:
                #     # Assuming log_event is globally available or passed via context
                #     log_event("AGENT_UTIL_ERROR", agent_id, error_details)
                # except Exception as log_e:
                #     logger_instance.error(
                #         f"Failed to log governance event for agent error: {log_e}"
                #     )

                # Re-raise the specified error class
                raise error_class(error_msg) from e

        return wrapper

    return decorator


def with_performance_tracking(operation_name: str):
    """Decorator for tracking operation performance. Assumes 'self' is the first arg and has 'perf_logger'."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Ensure self has perf_logger attribute
            if not hasattr(self, "perf_logger") or not isinstance(
                self.perf_logger, PerformanceLogger
            ):
                util_logger.warning(
                    f"Performance tracking skipped for {operation_name}: 'perf_logger' not found or invalid on {self}."
                )
                return await func(self, *args, **kwargs)

            # Use the performance logger from the instance
            with self.perf_logger.track_operation(operation_name):
                return await func(self, *args, **kwargs)

        return wrapper

    return decorator

# Add __all__ if needed
__all__ = ["with_error_handling", "with_performance_tracking"] 