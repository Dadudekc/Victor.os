"""
Autonomy Recovery Patch: Provides utilities to monitor agent state, detect staleness,
and manage recovery or escalation (e.g., reporting to a Captain agent).

Tracks active tasks and last action timestamps/step counts per agent using local files.

CRITICAL FIXME: The file I/O operations in this module were originally implemented
                using a problematic asyncio pattern (run_until_complete from within
                an async context). They are being refactored to use `await asyncio.to_thread`
                correctly, making the helper functions and their callers async.
"""

import asyncio
import json
import logging
import os

# import time # F401 Unused import
from datetime import datetime, timedelta, timezone

# Configuration
AGENT_STATUS_DIR = "runtime/agent_comms/agent_status"
ACTIVE_TASK_FILE = "active_task.json"
LAST_ACTION_FILE = "last_action.json"
STALE_THRESHOLD_SECONDS = 300  # 5 minutes
MAX_STEPS_WITHOUT_COMMIT = 10  # Example threshold
# FIXME: CAPTAIN_MAILBOX_ID and CAPTAIN_MAILBOX_PATH should be configurable, not hardcoded.
CAPTAIN_MAILBOX_ID = "Captain-Agent-5"  # Needs confirmation or dynamic lookup
CAPTAIN_MAILBOX_PATH = f"runtime/agent_comms/agent_mailboxes/{CAPTAIN_MAILBOX_ID}/inbox"

logger = logging.getLogger(__name__)  # Define logger at module level


class AgentStateError(Exception):
    """Custom exception for agent state issues."""

    pass


async def _get_agent_status_path(agent_id: str) -> str:
    """Constructs the path to the agent's status directory, creating it if necessary."""
    path = os.path.join(AGENT_STATUS_DIR, agent_id)
    await asyncio.to_thread(os.makedirs, path, exist_ok=True)
    return path


async def _read_json_file(file_path: str) -> dict | None:
    """Safely reads a JSON file asynchronously."""
    exists = await asyncio.to_thread(os.path.exists, file_path)
    if not exists:
        return None
    try:

        def sync_read():
            with open(file_path, "r") as f:
                return json.load(f)

        return await asyncio.to_thread(sync_read)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading {file_path}: {e}")
        return None


async def _write_json_file(file_path: str, data: dict):
    """Safely writes data to a JSON file asynchronously."""
    try:

        def sync_write():
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

        await asyncio.to_thread(sync_write)
    except IOError as e:
        logger.error(f"Error writing to {file_path}: {e}")
        raise AgentStateError(f"Failed to write agent state to {file_path}") from e


async def get_active_task(agent_id: str) -> dict | None:
    """Reads the active task information for the agent asynchronously."""
    status_path = await _get_agent_status_path(agent_id)
    task_file = os.path.join(status_path, ACTIVE_TASK_FILE)
    return await _read_json_file(task_file)


async def set_active_task(
    agent_id: str, task_id: str, task_details: dict | None = None
):
    """Sets the agent's currently active task asynchronously."""
    status_path = await _get_agent_status_path(agent_id)
    task_file = os.path.join(status_path, ACTIVE_TASK_FILE)
    data = {"task_id": task_id, "details": task_details or {}}
    await _write_json_file(task_file, data)
    await update_last_action(
        agent_id, reset_steps=True
    )  # Reset steps when a new task is set


async def clear_active_task(agent_id: str):
    """Clears the agent's active task asynchronously."""
    status_path = await _get_agent_status_path(agent_id)
    task_file = os.path.join(status_path, ACTIVE_TASK_FILE)
    exists = await asyncio.to_thread(os.path.exists, task_file)
    if exists:
        try:
            await asyncio.to_thread(os.remove, task_file)
        except OSError as e:
            logger.error(f"Error removing active task file {task_file}: {e}")
            # Decide if this should raise an error or just be logged


async def update_last_action(
    agent_id: str, increment_step: bool = True, reset_steps: bool = False
):
    """Updates the timestamp of the agent's last significant action and step count asynchronously."""
    status_path = await _get_agent_status_path(agent_id)
    action_file = os.path.join(status_path, LAST_ACTION_FILE)

    current_steps = 0
    if not reset_steps:
        last_action_data = await _read_json_file(action_file)
        if last_action_data:
            current_steps = last_action_data.get("steps_since_last_commit", 0)

    if increment_step and not reset_steps:
        current_steps += 1

    data = {
        "last_action_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "steps_since_last_commit": current_steps,
    }
    await _write_json_file(action_file, data)


async def _send_halt_report_to_captain(agent_id: str, reason: str):
    """Sends an urgent HALT report to the Captain's inbox asynchronously."""
    message_id = f"halt_report_{agent_id}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"  # noqa: E501
    # Read last action data asynchronously before constructing the message
    last_action_file_path = os.path.join(
        await _get_agent_status_path(agent_id), LAST_ACTION_FILE
    )
    last_action_content = await _read_json_file(last_action_file_path)
    message = {
        "message_id": message_id,
        "sender_agent_id": agent_id,
        "recipient_agent_id": CAPTAIN_MAILBOX_ID,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "subject": f"CRITICAL: Agent {agent_id} Auto-HALT Triggered",
        "type": "AGENT_HALT_REPORT",
        "body": {
            "reason": reason,
            "details": f"Agent {agent_id} failed staleness check and requires intervention.",  # noqa: E501
            "last_action_data": last_action_content,
        },
        "priority": "CRITICAL",
    }

    captain_inbox_path = os.path.join(CAPTAIN_MAILBOX_PATH, f"{message_id}.json")
    try:
        await _write_json_file(captain_inbox_path, message)
        logger.info(f"Agent {agent_id} sent HALT report to Captain: {reason}")
    except Exception as e:
        logger.critical(
            f"Agent {agent_id} failed to send HALT report to Captain! Reason: {e}"
        )


async def check_agent_staleness(agent_id: str) -> bool:
    """
    Checks if the agent is stale based on the last action time or step count asynchronously.
    Returns True if stale, False otherwise.
    """
    # TODO: Initial staleness for new agents needs clearer policy.
    #       Currently, first check creates a record and returns False (not stale).
    status_path = await _get_agent_status_path(agent_id)
    action_file = os.path.join(status_path, LAST_ACTION_FILE)
    last_action_data = await _read_json_file(action_file)

    if not last_action_data:
        await update_last_action(
            agent_id, increment_step=False
        )  # Create initial record
        return False

    # Check time staleness
    last_action_time_str = last_action_data.get("last_action_timestamp_utc")
    if last_action_time_str:
        try:
            last_action_time = datetime.fromisoformat(last_action_time_str)
            if datetime.now(timezone.utc) - last_action_time > timedelta(
                seconds=STALE_THRESHOLD_SECONDS
            ):
                return True  # Stale due to time
        except ValueError:
            logger.error(
                f"Error parsing timestamp for agent {agent_id}: {last_action_time_str}"
            )
            # Treat as potentially stale if timestamp is invalid? Needs policy.

    # Check step staleness
    steps = last_action_data.get("steps_since_last_commit", 0)
    if steps >= MAX_STEPS_WITHOUT_COMMIT:
        return True  # Stale due to too many steps without commit/reset

    return False


async def maintain_loop_integrity(
    agent_id: str, current_task_id: str | None
) -> str | None:
    """
    Core async function to be injected into the agent loop.
    1. Checks for staleness and escalates if needed.
    2. Checks if a persistent task exists.
    3. If persistent task exists and no current task, returns the persistent task_id.
    4. Updates the last action timestamp/step count.

    Returns:
        The task_id the agent should focus on, or None.
    Raises:
        AgentStateError: If a HALT condition occurs.
    """
    if await check_agent_staleness(agent_id):
        # Read last action data asynchronously for the reason message
        last_action_file_path = os.path.join(
            await _get_agent_status_path(agent_id), LAST_ACTION_FILE
        )
        last_action_content_for_reason = await _read_json_file(last_action_file_path)
        reason = f"Stale state detected (timeout or excessive steps). Last action data: {last_action_content_for_reason}"  # noqa: E501
        logger.error(f"HALTING Agent {agent_id}: {reason}")
        await _send_halt_report_to_captain(agent_id, reason)
        raise AgentStateError(reason)

    persistent_task_data = await get_active_task(agent_id)
    task_to_focus_on = current_task_id

    if not current_task_id and persistent_task_data:
        persistent_task_id = persistent_task_data.get("task_id")
        logger.info(
            f"Agent {agent_id} has no current task from loop, resuming persistent task: {persistent_task_id}"  # noqa: E501
        )
        task_to_focus_on = persistent_task_id

    await update_last_action(agent_id, increment_step=(task_to_focus_on is not None))

    return task_to_focus_on


# --- Helper functions potentially called by agent logic ---


async def mark_task_complete_and_clear(agent_id: str):
    """Helper to clear active task state upon completion, asynchronously."""
    logger.info(f"Agent {agent_id} marking task complete, clearing active task state.")
    await clear_active_task(agent_id)
    await update_last_action(agent_id, reset_steps=True)  # Reset steps on completion


async def record_progress_and_reset_steps(agent_id: str):
    """Helper to call when significant progress (commit, validation) is made, asynchronously."""
    logger.info(f"Agent {agent_id} recording progress, resetting step counter.")
    await update_last_action(agent_id, reset_steps=True)


# Example Usage (Illustrative - integrate into actual agent loop)
# agent_id = "Agent-7"
# current_task_from_loop = None # Example: agent just finished mailbox scan, no new task
# try:
#     task_id_to_work_on = await maintain_loop_integrity(agent_id, current_task_from_loop)
#     if task_id_to_work_on:
#         # Agent proceeds to execute or continue task_id_to_work_on
#         print(f"Agent {agent_id} should work on task: {task_id_to_work_on}")
#         # Simulate making progress
#         # record_progress_and_reset_steps(agent_id)
#         # Simulate completing task
#         # mark_task_complete_and_clear(agent_id)
#     else:
#          # Agent proceeds to check task queue or other idle actions
#          print(f"Agent {agent_id} has no active task, checking queue.")
#
# except AgentStateError as e:
#      print(f"Agent {agent_id} halted due to state error: {e}")
#      # Agent enters safe halt state or exits loop


# === START COMMENT OUT UNIMPLEMENTED/MISPLACED RECOVERY FUNCTIONS ===
# TODO: Refactor these recovery functions into a class or implement correctly.
# They currently use `self` incorrectly at the module level.
#
# def _check_core_systems(self):
#     """Basic checks for essential system components (e.g., PBM, AgentBus)."""
#     logging.info(f"Agent {self.agent_id}: Checking core system availability.")
#     # TODO: Implement actual checks (e.g., can we instantiate PBM?)
#     # Example placeholder:
#     try:
#         # from dreamos.core.tasks.pbm import ProjectBoardManager  # Hypothetical
#         # pbm = ProjectBoardManager()
#         # logging.info("PBM connection successful.")
#         pass
#     except Exception as e:
#         logging.warning(f"Core system check failed (PBM example): {e}", exc_info=True)
#         return False
#     return True
#
# def _verify_agent_loop_integrity(self):
#     """Checks if the agent's own loop logic seems intact."""
#     logging.info(f"Agent {self.agent_id}: Verifying agent loop integrity.")
#     # TODO: Implement checks (e.g., can agent read its own state? Is loop runnable?)
#     # Example placeholder:
#     if not hasattr(self, "run") or not callable(self.run):
#         logging.error("Agent loop method 'run' is missing or not callable.")
#         return False
#     return True
#
# def _attempt_task_board_resync(self):
#     """Tries to connect to PBM and get current task status."""
#     logging.info(f"Agent {self.agent_id}: Attempting Task Board resynchronization.")
#     # TODO: Implement PBM interaction
#     # Example placeholder:
#     try:
#         # pbm = ProjectBoardManager()
#         # status = pbm.get_agent_status(self.agent_id) # Hypothetical
#         # logging.info(f"Task board resync successful. Current status: {status}")
#         pass
#     except Exception as e:
#         logging.error(f"Task board resync failed: {e}", exc_info=True)
#         return False
#     return True
#
# def _evaluate_recovery_options(self):
#     """Based on checks, decide the best course of action."""
#     logging.info(f"Agent {self.agent_id}: Evaluating recovery options.")
#     if not self._check_core_systems():
#         logging.warning("Core systems unavailable. Attempting minimal recovery.")
#         # Option: Attempt to alert Captain/System Monitor via a very basic mechanism
#         self._send_distress_signal(
#             "Core systems check failed. Limited recovery options."
#         )
#         return "MINIMAL_RECOVERY"
#
#     if not self._verify_agent_loop_integrity():
#         logging.error("Agent loop integrity compromised. Cannot self-recover fully.")
#         self._send_distress_signal(
#             "Agent loop integrity check failed. Requires external intervention."
#         )
#         return "AWAIT_INTERVENTION"
#
#     if not self._attempt_task_board_resync():
#         logging.warning(
#             "Task board resync failed. Proceeding with cached state if possible."
#         )
#         # Option: Operate based on last known state, announce state uncertainty
#         return "RECOVER_WITH_CACHE"
#
#     logging.info("All checks passed. Attempting full loop restart.")
#     return "FULL_RESTART"
#
# def _execute_recovery_strategy(self, strategy: str):
#     """Perform actions based on the chosen recovery strategy."""
#     logging.info(f"Agent {self.agent_id}: Executing recovery strategy '{strategy}'...")
#
#     if strategy == "FULL_RESTART":
#         logging.info("Initiating full agent loop restart.")
#         # This might involve re-initializing state and calling self.run() or similar
#         # self.initialize_state()
#         # self.run() # Or trigger the main loop mechanism
#         pass
#
#     elif strategy == "RECOVER_WITH_CACHE":
#         logging.warning(
#             "Attempting to operate with potentially stale cached state. "
#             "Announcing uncertainty."
#         )
#         # self.announce_status("OPERATING_UNCERTAIN_STATE")
#         # self.run() # Start loop with cached state awareness
#         pass
#
#     elif strategy == "MINIMAL_RECOVERY":
#         logging.warning("Entering minimal recovery mode. Only distress signals active.")
#         # Loop trying to send distress signals?
#         # while not self.shutdown_requested:
#         #     self._send_distress_signal("Agent in minimal recovery mode.")
#         #     time.sleep(60)
#         pass
#
#     elif strategy == "AWAIT_INTERVENTION":
#         logging.error("Entering safe halt mode. Awaiting external intervention.")
#         # Stop all active processes, maybe send a final distress signal
#         self._send_distress_signal(
#             "Agent halting. Requires external intervention.", final=True
#         )
#         # self.halt_processing()
#         pass
#     else:
#         logging.error(f"Unknown recovery strategy: {strategy}. Halting.")
#         self._send_distress_signal(f"Unknown recovery strategy '{strategy}'. Halting.")
#         # self.halt_processing()
#
# def _send_distress_signal(self, message: str, final: bool = False):
#     """Sends an emergency message (e.g., to Captain, log, specific channel)."""
#     signal_id = str(uuid.uuid4())
#     log_prefix = "FINAL DISTRESS SIGNAL" if final else "DISTRESS SIGNAL"
#     full_message = (
#         f"{log_prefix} (Agent: {self.agent_id}, Signal ID: {signal_id}): {message}"
#     )
#     logging.critical(full_message)
#
#     # TODO: Implement actual sending mechanism (e.g., AgentBus event, direct message)
#     # Example:
#     try:
#         # bus = AgentBus()
#         # event = BaseEvent(
#         #     event_type=EventType.SYSTEM_AGENT_DISTRESS,
#         #     source_id=self.agent_id,
#         #     data={"message": full_message, "signal_id": signal_id, "final": final}
#         # )
#         # bus.dispatch_event(event)
#         pass
#     except Exception as e:
#         logging.error(
#             f"Failed to send distress signal via primary mechanism: {e}", exc_info=True
#         )
#         # Fallback? Direct log write? stderr?
# === END COMMENT OUT ===
