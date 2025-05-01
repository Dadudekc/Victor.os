# src/dreamos/core/utils/autonomy_governor.py
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

# Type checking imports to avoid circular dependencies
if TYPE_CHECKING:
    from ..comms.mailbox_utils import MailboxUtils  # Assuming a utility class exists
    from ..config import AppConfig
    from ..coordination.project_board_manager import ProjectBoardManager

# Moved error import to top
from ..errors import DreamOSError

logger = logging.getLogger("AutonomyGovernor")

# REMOVED Global Paths - Use injected config
# WORKING_TASKS_PATH = PROJECT_ROOT / "runtime/agent_comms/project_boards/working_tasks.json"
# FUTURE_TASKS_PATH = PROJECT_ROOT / "runtime/agent_comms/project_boards/future_tasks.json"
# MAILBOX_BASE_DIR = PROJECT_ROOT / "runtime/agent_comms/agent_mailboxes"

# REMOVED Simplified Helper Functions - Use injected clients
# def _read_board_simple(...)
# def _check_mailbox_simple(...)

# --- Governor Logic ---


class AgentAutonomyGovernor:
    """Provides checks and guidance based on AUTONOMOUS_LOOP principles (v2.1 Inbox-Centric)."""

    # Dependency Injection
    def __init__(
        self,
        config: "AppConfig",
        pbm: "ProjectBoardManager",
        mailbox_utils: "MailboxUtils",
    ):
        """Initialize the governor with necessary dependencies."""
        self.config = config
        self.pbm = pbm
        self.mailbox_utils = mailbox_utils
        # TODO: Validate that injected dependencies are not None
        if not all([config, pbm, mailbox_utils]):
            # In a real system, might raise an error or handle missing dependencies
            logger.error("AutonomyGovernor initialized with missing dependencies!")

    def check_operational_status(self, agent_id: str) -> Tuple[str, Optional[str]]:
        """Checks agent status based on mailbox, central boards, and agent's own inbox (v2.1).

        Returns:
            Tuple[str, Optional[str]]: (Status String, Optional Task ID)
            Possible Status Strings:
                - MAILBOX_PENDING (External messages)
                - WORKING (Assigned central task)
                - WORKING_INBOX (Working on self-assigned inbox task)
                - IDLE_BLOCKED (Assigned central task is blocked)
                - IDLE_HAS_INBOX_TASK (No central task, but inbox task pending)
                - IDLE_CAN_CLAIM (No central/inbox task, but claimable tasks exist)
                - IDLE_TRUE_IDLE (No messages, no assigned/inbox/claimable tasks)
                - ERROR_CHECKING_STATUS
        """
        logger.debug(f"Governor checking status for Agent {agent_id}")

        try:
            # 1. Check Mailbox first (for external messages)
            # Uses injected mailbox_utils
            # Assuming check_mailbox returns True if messages exist
            if self.mailbox_utils.check_mailbox(agent_id):
                logger.info(f"Agent {agent_id} status: MAILBOX_PENDING")
                return "MAILBOX_PENDING", None

            # 2. Check Central Working Tasks for assigned tasks
            # Uses injected PBM
            working_tasks = self.pbm.get_all_tasks(board="working")
            assigned_task_id = None
            is_blocked = False
            for task in working_tasks:
                if task.get("assigned_agent") == agent_id:
                    assigned_task_id = task.get("task_id")
                    if task.get("status", "").upper() == "BLOCKED":
                        is_blocked = True
                    break  # Found first assigned task

            if assigned_task_id:
                if is_blocked:
                    logger.info(
                        f"Agent {agent_id} status: IDLE_BLOCKED on central task {assigned_task_id}"
                    )
                    return "IDLE_BLOCKED", assigned_task_id
                else:
                    logger.info(
                        f"Agent {agent_id} status: WORKING on central task {assigned_task_id}"
                    )
                    return "WORKING", assigned_task_id

            # 3. Check Agent's Own Inbox for Pending Tasks (v2.1)
            # Assuming mailbox_utils can list tasks or check for pending ones
            inbox_tasks = self.mailbox_utils.list_tasks_in_inbox(
                agent_id
            )  # Needs implementation
            pending_inbox_task_id = None
            for (
                task
            ) in (
                inbox_tasks
            ):  # Assuming list_tasks returns list of dicts/objects with task_id/status
                if task.get("status", "").upper() == "PENDING":
                    pending_inbox_task_id = task.get("task_id", "UNKNOWN_INBOX_TASK")
                    # Consider prioritizing based on task priority here if needed
                    break  # Found a pending task

            if pending_inbox_task_id:
                logger.info(
                    f"Agent {agent_id} status: IDLE_HAS_INBOX_TASK ({pending_inbox_task_id})"
                )
                return "IDLE_HAS_INBOX_TASK", pending_inbox_task_id

            # 4. Check Central Ready Queue for claimable work
            # Uses injected PBM
            ready_tasks = self.pbm.get_all_tasks(board="ready")  # Changed board name
            has_claimable = any(
                task.get("status", "").upper() == "PENDING"
                and not task.get("assigned_agent")
                for task in ready_tasks
            )  # Check ready_tasks

            if has_claimable:
                logger.info(
                    f"Agent {agent_id} status: IDLE_CAN_CLAIM (claimable central tasks exist)"
                )
                return "IDLE_CAN_CLAIM", None
            else:
                logger.info(
                    f"Agent {agent_id} status: IDLE_TRUE_IDLE (no pending tasks found)"
                )
                return "IDLE_TRUE_IDLE", None

        except Exception as e:
            logger.exception(f"Error checking status for Agent {agent_id}: {e}")
            return "ERROR_CHECKING_STATUS", None

    def get_next_action_suggestion(
        self, status: str, task_id: Optional[str] = None
    ) -> str:
        """Suggests the next action based on the operational status (v2.1)."""
        if status == "MAILBOX_PENDING":
            return "Process mailbox messages immediately."
        elif status == "WORKING":
            return f"Continue executing assigned central task {task_id}."
        elif (
            status == "WORKING_INBOX"
        ):  # Added status - Needs check_operational_status to return this
            return f"Continue executing self-assigned inbox task {task_id}."
        elif status == "IDLE_BLOCKED":
            return (
                f"Investigate blocker for assigned central task {task_id} or escalate."
            )
        elif status == "IDLE_HAS_INBOX_TASK":
            return f"Process pending task {task_id} from your inbox."
        elif status == "IDLE_CAN_CLAIM":
            return "Claim a task from the central ready queue board."
        elif status == "IDLE_TRUE_IDLE":
            return "Enter IDLE_MODE protocol: Contribute to Masterpiece (cleanup), assist others, or propose new tasks."
        elif status == "ERROR_CHECKING_STATUS":
            return "Status check failed. Investigate board/mailbox access."
        else:
            return "Unknown status. Re-evaluate operational state."

    # --- Placeholder Methods ---
    # TODO: Add py_compile and potentially pytest execution based on task metadata
    def validate_task_completion_checklist(
        self,
        task_id: str,
        completion_notes: str,
        modified_files: Optional[List[str]] = None,
    ) -> bool:
        """Performs basic self-validation: flake8 on modified Python files."""
        logger.debug(f"Performing validation check for task {task_id}")
        files_ok = True
        if modified_files:
            python_files = [f for f in modified_files if f.endswith(".py")]
            if python_files:
                try:
                    import subprocess

                    flake8_cmd = ["flake8"] + python_files
                    logger.debug(f"Running flake8 validation: {' '.join(flake8_cmd)}")
                    # Timeout included for safety
                    result = subprocess.run(
                        flake8_cmd,
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=30,
                    )
                    if result.returncode != 0:
                        logger.warning(
                            f"Flake8 validation failed for task {task_id}. Return code: {result.returncode}"
                        )
                        logger.warning(f"Flake8 stdout:\n{result.stdout}")
                        logger.warning(f"Flake8 stderr:\n{result.stderr}")
                        files_ok = False
                    else:
                        logger.info(f"Flake8 validation passed for task {task_id}.")
                except FileNotFoundError:
                    logger.error(
                        "Flake8 command not found. Cannot perform linting validation."
                    )
                    files_ok = False  # Treat as failure if tool missing
                except subprocess.TimeoutExpired:
                    logger.error(f"Flake8 validation timed out for task {task_id}.")
                    files_ok = False
                except Exception as e:
                    logger.exception(
                        f"Error running flake8 validation for task {task_id}: {e}"
                    )
                    files_ok = False
        else:
            logger.debug("No modified files provided, skipping file validation.")

        if files_ok:
            logger.info(f"Basic file validation passed for task {task_id}.")
            return True
        else:
            logger.warning(f"Basic file validation failed for task {task_id}.")
            return False

    # TODO: Consider dispatching compliance events to AgentBus
    def log_compliance_event(
        self, agent_id: str, event_type: str, details: Dict[str, Any]
    ):
        """Logs key autonomy loop events for compliance/monitoring."""
        try:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_id": agent_id,
                "event_type": event_type,  # e.g., TASK_COMPLETED_VALIDATED, IDLE_MODE_SCAN, BLOCKER_ESCALATED
                "details": details,
            }
            # Log clearly, avoid complex objects if just logging info
            logger.info(
                f"COMPLIANCE_EVENT::{agent_id}::{event_type}::{json.dumps(details)}"
            )
        except Exception as e:
            logger.error(f"Failed to log compliance event for {agent_id}: {e}")


# # --- Example Usage --- COMMENTED OUT
# # Needs updating to inject dependencies if uncommented
# if __name__ == '__main__':
#     pass # Cannot run standalone without dependencies
# # End of commented out block
