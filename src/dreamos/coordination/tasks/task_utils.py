import json
import logging
import math
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
from uuid import UUID, uuid4

# EDIT START: Import core utility
# from datetime import datetime, timezone
from dreamos.utils.common_utils import get_utc_iso_timestamp

# EDIT END
# Removed: from src.tools.dreamos_utils.base import load_json_file, save_json_file
# Use consolidated utils now:
from dreamos.utils.file_io import read_json_file, write_json_atomic

# {{ EDIT START: Import ProjectBoardManager }}
from ..comms.project_board import (  # Assuming relative path
    ProjectBoardError,
    ProjectBoardManager,
)

# {{ EDIT END }}

logger = logging.getLogger(__name__)  # Define logger at module level


# {{ EDIT START: Deprecate unsafe direct file access functions }}
def read_tasks(task_list_path: Union[str, Path]) -> Optional[List[Dict[str, Any]]]:
    """DEPRECATED: Read tasks list directly from JSON file. UNSAFE without locking. Use ProjectBoardManager."""
    logger.error(
        f"Direct use of task_utils.read_tasks({task_list_path}) is DEPRECATED and UNSAFE due to lack of locking. Use ProjectBoardManager methods."
    )
    return None  # Indicate failure/deprecation
    # tasks = read_json_file(task_list_path)
    # if tasks is None:
    #     logger.error(f"Failed to read or parse task file: {task_list_path}")
    #     return None
    # if not isinstance(tasks, list):
    #      logger.error(f"Task file {task_list_path} does not contain a list.")
    #      return None
    #
    # # Ensure essential fields exist with defaults
    # for t in tasks:
    #      if not isinstance(t, dict):
    #           logger.warning(f"Skipping non-dict item in task list: {t}")
    #           continue # Skip non-dictionary items
    #      t.setdefault('retry_count', 0)
    #      t.setdefault('repair_attempts', 0)
    #      t.setdefault('failure_count', 0) # Kept for potential compatibility
    #      t.setdefault('status', 'UNKNOWN') # Default status if missing
    #      t.setdefault('task_id', 'MISSING_ID') # Default ID if missing
    #
    # return tasks


def write_tasks(task_list_path: Union[str, Path], tasks: List[Dict[str, Any]]) -> bool:
    """DEPRECATED: Write tasks list atomically to JSON file. UNSAFE without locking. Use ProjectBoardManager."""
    logger.error(
        f"Direct use of task_utils.write_tasks({task_list_path}) is DEPRECATED and UNSAFE due to lack of locking. Use ProjectBoardManager methods."
    )
    return False  # Indicate failure/deprecation
    # try:
    #     write_json_atomic(task_list_path, tasks, indent=2)
    #     logger.debug(f"Successfully wrote {len(tasks)} tasks to {task_list_path}")
    #     return True
    # except Exception as e:
    #     logger.exception(f"Failed to write tasks to {task_list_path}: {e}")
    #     return False


# {{ EDIT END }}


def _calculate_task_score(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculates scoring metrics for a completed task."""
    # EDIT START: Use core utility
    # now_iso: str = datetime.now(timezone.utc).isoformat()
    now_iso: str = get_utc_iso_timestamp()
    # EDIT END
    scoring: Dict[str, Any] = {
        "outcome_quality": 0.5,  # Default assumption
        "time_efficiency": 0.5,  # Default assumption
        "escalation_penalty": 1.0,
        "total_score": 0.0,  # Calculated at the end
        "scored_at": now_iso,
        "details": "",
    }
    details_list: List[str] = []  # Build details list for cleaner joining

    # Outcome Quality
    result_status: Optional[str] = task_data.get("result_status")
    if result_status == "SUCCESS":
        scoring["outcome_quality"] = 1.0
        details_list.append("Result status: SUCCESS.")
    elif result_status in ["FAILURE", "VALIDATION_ERROR"]:
        scoring["outcome_quality"] = 0.0
        details_list.append(f"Result status: {result_status}.")
    else:
        # Keep default 0.5 quality if status is unknown
        details_list.append(
            f"Result status: {result_status or 'Unknown/Not Provided'}."
        )

    # Escalation Penalty
    retry_count: int = task_data.get("retry_count", 0)
    repair_attempts: int = task_data.get("repair_attempts", 0)
    total_attempts: int = retry_count + repair_attempts
    if total_attempts > 0:
        scoring["escalation_penalty"] = max(
            0.0, 1.0 / (1.0 + float(total_attempts))
        )  # Ensure non-negative
        details_list.append(f"{total_attempts} retries/repairs recorded.")
    else:
        details_list.append("No retries/repairs.")

    # Time Efficiency
    started_at_str: Optional[str] = task_data.get("started_at")
    completed_at_str: Optional[str] = task_data.get("completed_at")
    if isinstance(started_at_str, str) and isinstance(completed_at_str, str):
        try:
            # Attempt to parse standard ISO format (with or without Z)
            start_dt = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(completed_at_str.replace("Z", "+00:00"))
            # Ensure timestamps are timezone-aware (assume UTC if not specified)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)

            duration_sec: float = (end_dt - start_dt).total_seconds()
            if duration_sec < 0:
                logger.warning(
                    f"Task {task_data.get('task_id', 'UNKNOWN')} has negative duration ({duration_sec}s). Clamping to 0."
                )
                duration_sec = 0.0
            # Avoid log(0 or negative) issues
            # Adding small epsilon to duration for log calculation stability
            log_input = (duration_sec / 10.0) + 1e-9
            scoring["time_efficiency"] = max(0.0, 1.0 - math.log10(log_input) / 2.0)
            details_list.append(f"Duration: {duration_sec:.2f}s.")
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Could not parse task timestamps for scoring task {task_data.get('task_id', 'UNKNOWN')}: {started_at_str}, {completed_at_str}. Error: {e}"
            )
            # Keep default 0.5 efficiency on parse error
            details_list.append("Could not parse task timestamps.")
    else:
        # Keep default 0.5 efficiency if timestamps missing
        details_list.append("Missing start/end timestamps for duration calculation.")

    # Total Score
    quality: float = max(0.0, min(1.0, scoring["outcome_quality"]))
    efficiency: float = max(0.0, min(1.0, scoring["time_efficiency"]))
    penalty: float = max(0.0, min(1.0, scoring["escalation_penalty"]))
    scoring["total_score"] = (quality + efficiency + penalty) / 3.0

    scoring["details"] = " ".join(details_list)
    return scoring


def update_task_status(
    task_list_path: Union[str, Path], task_id: str, status: str, **kwargs: Any
) -> bool:
    """DEPRECATED - Use TaskNexus or ProjectBoardManager methods directly."""
    logger.error(
        "Direct use of task_utils.update_task_status is DEPRECATED and UNSAFE due to lack of locking. Use TaskNexus or ProjectBoardManager methods."
    )
    # Return False to indicate failure/deprecation
    return False
    # {{ EDIT START: Replace unsafe logic with placeholder/deprecation warning }}
    # """Update a task's status and optionally other fields like results, timestamps, and scores.
    #
    # Uses atomic write for safety BUT LACKS LOCKING - DEPRECATED.
    # """
    # # Note: Read-Modify-Write on shared file is fragile under concurrency.
    # logger.warning(f"Attempting UNSAFE update for task {task_id} in {task_list_path}. Use ProjectBoardManager.")
    #
    # tasks = read_tasks(task_list_path)
    # if tasks is None:
    #     return False
    #
    # updated = False
    # task_found = False
    # target_task_index: Optional[int] = None
    # for i, t in enumerate(tasks):
    #      if not isinstance(t, dict): continue
    #      if t.get('task_id') == task_id:
    #         task_found = True
    #         target_task_index = i
    #         logger.debug(f"Found task {task_id} at index {i}. Updating status to {status}.")
    #         break
    #
    # if not task_found or target_task_index is None:
    #     logger.warning(f"Task ID '{task_id}' not found in {task_list_path} for update.")
    #     return False
    #
    # try:
    #     target_task: Dict[str, Any] = tasks[target_task_index]
    #     original_status = target_task.get('status')
    #
    #     # Apply status update
    #     target_task['status'] = status
    #     updated = True # Assume update happens if task is found
    #
    #     # Update optional fields from kwargs
    #     allowed_updates = {'result_status', 'started_at', 'completed_at', 'result_data', 'error_message', 'progress', 'notes'} # Added notes
    #     fields_updated: List[str] = []
    #     for key, value in kwargs.items():
    #          if key in allowed_updates:
    #               if target_task.get(key) != value: # Only log if value changes
    #                    target_task[key] = value
    #                    fields_updated.append(key)
    #          else:
    #               logger.warning(f"Attempted to update non-allowed field '{key}' for task {task_id}")
    #     if fields_updated:
    #          logger.debug(f"Updated fields for task {task_id}: {fields_updated}")
    #
    #     # --- Status Transition Logic ---
    #     # Always add/update timestamp
    #     target_task['timestamp_updated'] = get_utc_iso_timestamp()
    #
    #     # Calculate score if task is COMPLETED
    #     if status == 'COMPLETED' and original_status != status:
    #         # Ensure completed_at is set
    #         if 'completed_at' not in target_task or target_task.get('completed_at') is None:
    #              completed_at_ts = kwargs.get('completed_at') or get_utc_iso_timestamp()
    #              target_task['completed_at'] = completed_at_ts
    #              if not kwargs.get('completed_at'):
    #                   logger.warning(f"Task {task_id} marked COMPLETED without explicit completed_at. Using current time: {completed_at_ts}")
    #
    #         # Ensure started_at exists for scoring
    #         if 'started_at' not in target_task or target_task.get('started_at') is None:
    #              logger.warning(f"Task {task_id} marked COMPLETED without started_at timestamp. Score calculation may be inaccurate.")
    #
    #         # Add scoring if not present or force update?
    #         target_task['scoring'] = _calculate_task_score(target_task)
    #
    # except Exception as e:
    #     logger.exception(f"Error processing updates for task {task_id}: {e}")
    #     return False # Indicate failure
    #
    # # Write back the entire updated list
    # if updated:
    #     if write_tasks(task_list_path, tasks):
    #         logger.info(f"Successfully updated task {task_id} status to {status} in {task_list_path}")
    #         return True
    #     else:
    #         logger.error(f"Failed to write updates for task {task_id} to {task_list_path}")
    #         return False
    # else:
    #     logger.debug(f"No updates applied for task {task_id} in {task_list_path}")
    #     return False # Or True if no update needed is considered success?
    # {{ EDIT END }}


# ... existing code ...
