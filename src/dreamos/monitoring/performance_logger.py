import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone  # Use timezone
from typing import Any, Dict, Optional  # Added for type hints
from pathlib import Path

# Updated import path
from ..core.config import AppConfig
from ..core.errors import ConfigurationError

# EDIT START: Load config to get path
# Define log path relative to potential runtime directory, avoid hardcoding 'memory' top-level  # noqa: E501
# TODO: Centralize log/runtime path configuration -> DONE
# LOG_DIR = os.path.join("runtime", "logs") # REMOVED
# LOG_PATH = os.path.join(LOG_DIR, "performance.jsonl") # REMOVED

# Load config once at module level
try:
    # Use the default loading mechanism
    _config = AppConfig.load()
    LOG_PATH = _config.paths.performance_log_path
except Exception as e:
    # EDIT: Catch ConfigurationError specifically if needed, otherwise general Exception
    # Use ConfigurationError directly if imported
    if isinstance(e, ConfigurationError):
        logging.error(f"Failed to load app config for PerformanceLogger: {e}")
    else:
        logging.error(f"Failed to load app config for PerformanceLogger (unexpected): {e}")
    # Fallback path if config load fails
    # REMOVED NameError causing line
    # raise appconfig_errors.exceptions.ConfigurationError(
    # Need a sensible fallback path
    LOG_PATH = Path("runtime/logs/performance.jsonl")
    logging.warning(f"Using fallback performance log path: {LOG_PATH}")

# Ensure log directory exists (handled by AppConfig._ensure_dirs_exist or fallback above)  # noqa: E501
# try: # REMOVED
#     os.makedirs(LOG_DIR, exist_ok=True) # REMOVED
# except OSError as e: # REMOVED
#     # Log error but allow continuation if possible # REMOVED
#     logging.basicConfig() # Ensure basicConfig is called if logger not set up # REMOVED  # noqa: E501
#     logging.error(f"Failed to create performance log directory {LOG_DIR}: {e}") # REMOVED  # noqa: E501
# EDIT END

# Logger specific to performance logging
perf_logger_instance = logging.getLogger("core.utils.performance")


class PerformanceLogger:
    """Logs performance metrics for agent operations and tasks."""

    def __init__(self):
        """Initializes the PerformanceLogger."""
        self.config = AppConfig.load()  # Load config to get path
        self.log_path = self.config.paths.performance_log_path

    @contextmanager
    def track_operation(self, operation_name: str):
        """Context manager to track the duration of an operation."""
        start_time = datetime.now(timezone.utc)
        perf_logger_instance.debug(
            f"Starting operation '{operation_name}' for agent {self.agent_id}..."
        )
        try:
            yield
        finally:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            perf_logger_instance.debug(
                f"Finished operation '{operation_name}' for agent {self.agent_id}. Duration: {duration:.3f}s"  # noqa: E501
            )
            # Optionally log operation summary here if needed, beyond just task outcomes
            self._log_entry(
                {
                    "event_type": "OPERATION_COMPLETED",
                    "agent_id": self.agent_id,
                    "operation_name": operation_name,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_sec": duration,
                }
            )

    def log_outcome(
        self,
        task_id: str,
        # agent_id: str, # Already stored in self.agent_id
        task_type: str,
        status: str,  # Expecting string (e.g., TaskStatus.name)
        start_time: Optional[str],  # Expecting ISO format string
        end_time: Optional[str],  # Expecting ISO format string
        error_message: Optional[str] = None,
        input_summary: Optional[str] = None,
        output_summary: Optional[str] = None,
    ):
        """Logs the outcome of a specific task."""
        duration_ms = None
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                end_dt = datetime.fromisoformat(end_time)
                duration_ms = int((end_dt - start_dt).total_seconds() * 1000)
            except ValueError:
                perf_logger_instance.warning(
                    f"Could not parse timestamps to calculate duration for task {task_id}"  # noqa: E501
                )

        entry = {
            "event_type": "TASK_OUTCOME",
            "task_id": task_id,
            "agent_id": self.agent_id,
            "task_type": task_type,
            "status": status.upper(),
            "start_time": start_time,
            "end_time": end_time,
            "duration_ms": duration_ms,
            "error_message": error_message,
            "input_summary": input_summary,
            "output_summary": output_summary,
        }
        self._log_entry(entry)

    def _log_entry(self, entry_dict: Dict[str, Any]):
        """Writes a structured entry to the performance log file."""
        entry_dict["log_timestamp"] = datetime.now(timezone.utc).isoformat()
        # EDIT START: Add logging before file open attempt
        log_file_path_str = str(self.log_path)  # Use consistent path for logging
        perf_logger_instance.debug(
            f"Attempting to write performance log entry to: {log_file_path_str}"
        )
        # EDIT END
        try:
            # Use 'a' mode for appending
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry_dict) + "\n")
            perf_logger_instance.debug(
                f"Logged performance entry: {entry_dict.get('event_type', 'N/A')} - {entry_dict.get('task_id') or entry_dict.get('operation_name')}"  # noqa: E501
            )
        except Exception as e:
            perf_logger_instance.error(
                f"Failed to write to performance log ({log_file_path_str}): {e}",
                exc_info=True,
            )  # EDIT: Use consistent path string
