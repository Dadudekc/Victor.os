"""Performance logging utilities for agent functionality."""

import logging
from typing import Optional

from dreamos.core.coordination.message_patterns import TaskMessage
from ...monitoring.performance_logger import PerformanceLogger
from ...utils.common_utils import get_utc_iso_timestamp

logger = logging.getLogger(__name__)

def log_task_performance(
    task: TaskMessage,
    agent_id: str,
    perf_logger: PerformanceLogger
) -> None:
    """Logs task performance metrics using the provided PerformanceLogger.

    Args:
        task: The TaskMessage object containing task details and results.
        agent_id: The ID of the agent that processed the task.
        perf_logger: The PerformanceLogger instance to use for logging.
    """
    start_time_iso = task.created_at.isoformat() if task.created_at else None
    end_time_iso = (
        task.updated_at.isoformat() if task.updated_at else get_utc_iso_timestamp()
    )

    try:
        perf_logger.log_outcome(
            task_id=task.task_id,
            agent_id=agent_id,
            task_type=task.task_type,
            status=task.status.name,
            start_time=start_time_iso,
            end_time=end_time_iso,
            error_message=task.error,
            input_summary=str(task.input_data)[:500],
            output_summary=str(task.result)[:500],
        )
        logger.debug(f"Logged performance for task {task.task_id}")
    except Exception as e:
        logger.error(
            f"Performance logging failed for task {task.task_id}: {e}",
            exc_info=True
        ) 