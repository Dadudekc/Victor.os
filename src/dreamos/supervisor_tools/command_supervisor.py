import asyncio
import json
import logging
import subprocess
import threading
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Union
from uuid import uuid4

from ..core.agent_bus import AgentBus
from ..core.bus_utils import EventType
from ..utils.log_exception import log_exception
from ..utils.singleton import Singleton

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class SupervisorEvent:
    """Represents an event structure specifically for the CommandSupervisor context."""

    event_type: EventType
    sender_id: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None


class ApprovalStatus(Enum):
    """Represents the possible states of a command approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CommandSupervisor(Singleton):
    """Singleton class to manage potentially risky command execution requests.

    This supervisor acts as a central gatekeeper for shell commands requested by
    various agents. It enforces a human-in-the-loop approval process before
    allowing any command execution, enhancing system safety.

    Workflow:
    1. An agent publishes a `COMMAND_EXECUTION_REQUEST` event via AgentBus.
    2. `CommandSupervisor` receives the request (`handle_command_request`).
    3. It assigns a unique ID and publishes a `COMMAND_APPROVAL_REQUEST` event.
    4. A separate component (e.g., a UI Agent, a manual reviewer) observes the
       approval request and publishes a `COMMAND_APPROVAL_RESPONSE` event.
    5. `CommandSupervisor` receives the response (`handle_approval_response`).
    6. If approved, it executes the command (`execute_command`) using asyncio
       subprocesses.
    7. If rejected or upon completion/error, it publishes a
       `COMMAND_EXECUTION_RESULT` event back to the original requesting agent.

    Attributes:
        agent_bus (AgentBus): The shared AgentBus instance for communication.
        pending_approvals (Dict[str, SupervisorEvent]): Stores requests awaiting approval.
        approval_status (Dict[str, ApprovalStatus]): Tracks the status of each request.
    """

    _instance = None
    _initialized = False

    def __init__(self, agent_bus: Optional[AgentBus] = None):
        """Initializes the CommandSupervisor singleton."""
        if self._initialized:
            return
        self.agent_bus = agent_bus or AgentBus()  # Get the singleton instance
        self.pending_approvals: Dict[str, SupervisorEvent] = {}
        self.approval_status: Dict[str, ApprovalStatus] = {}
        self.lock = threading.Lock()  # Protects shared state
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self._initialized = True
        logger.info("CommandSupervisor initialized.")

    def start(self):
        """Starts the CommandSupervisor's background thread for event handling."""
        if not self.thread.is_alive():
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            logger.info("CommandSupervisor started.")

    def stop(self):
        """Signals the CommandSupervisor's background thread to stop gracefully."""
        self._stop_event.set()
        if self.thread.is_alive():
            self.thread.join()
        logger.info("CommandSupervisor stopped.")

    def _run(self):
        """The main loop running in a background thread.

        Subscribes to necessary AgentBus events and waits for stop signal.
        """
        logger.info("CommandSupervisor thread running.")
        # Subscribe to relevant events if not already done by AgentBus initialization
        # This ensures the supervisor listens even if started after the bus is active.
        if not self.agent_bus.is_subscriber(
            self.handle_command_request, EventType.COMMAND_EXECUTION_REQUEST
        ):
            self.agent_bus.subscribe(
                EventType.COMMAND_EXECUTION_REQUEST, self.handle_command_request
            )
        if not self.agent_bus.is_subscriber(
            self.handle_approval_response, EventType.COMMAND_APPROVAL_RESPONSE
        ):
            self.agent_bus.subscribe(
                EventType.COMMAND_APPROVAL_RESPONSE, self.handle_approval_response
            )

        while not self._stop_event.is_set():
            # The supervisor primarily reacts to events, so the main loop can be simple.
            # We might add periodic checks or cleanup tasks here if needed.
            time.sleep(1)  # Prevent busy-waiting

        logger.info("CommandSupervisor thread stopped.")
        # Unsubscribe from events on stop
        self.agent_bus.unsubscribe(
            EventType.COMMAND_EXECUTION_REQUEST, self.handle_command_request
        )
        self.agent_bus.unsubscribe(
            EventType.COMMAND_APPROVAL_RESPONSE, self.handle_approval_response
        )

    async def handle_command_request(self, event: SupervisorEvent):
        """Handles incoming `COMMAND_EXECUTION_REQUEST` events.

        Assigns a command ID and forwards the request for human approval.
        """
        logger.info(f"Received command request: {event.payload} from {event.sender_id}")
        command_id = str(uuid4())
        request_payload = event.payload
        request_payload["command_id"] = command_id  # Add unique ID to the payload

        with self.lock:
            self.pending_approvals[command_id] = event
            self.approval_status[command_id] = ApprovalStatus.PENDING

        # Request human approval
        approval_request_payload = {
            "command_id": command_id,
            "command": request_payload.get("command"),
            "requesting_agent_id": event.sender_id,
            "details": request_payload.get("details", "No details provided."),
        }
        approval_event = SupervisorEvent(
            event_type=EventType.COMMAND_APPROVAL_REQUEST,
            sender_id="CommandSupervisor",
            payload=approval_request_payload,
            correlation_id=event.correlation_id,
        )
        logger.info(
            f"Requesting approval for command ID {command_id}: {request_payload.get('command')}"
        )
        await self.agent_bus.publish(approval_event)

    async def handle_approval_response(self, event: SupervisorEvent):
        """Handles incoming `COMMAND_APPROVAL_RESPONSE` events.

        Processes the approval/rejection and triggers command execution or
        notifies the requester accordingly.
        """
        response_payload = event.payload
        command_id = response_payload.get("command_id")
        approved = response_payload.get("approved", False)
        original_request_event = None

        logger.info(
            f"Received approval response for command ID {command_id}: Approved={approved}"
        )

        with self.lock:
            if command_id in self.pending_approvals:
                original_request_event = self.pending_approvals.pop(command_id)
                if approved:
                    self.approval_status[command_id] = ApprovalStatus.APPROVED
                else:
                    self.approval_status[command_id] = ApprovalStatus.REJECTED
            else:
                logger.warning(
                    f"Received approval response for unknown or already processed command ID: {command_id}"
                )
                return  # Ignore if command ID is not pending

        if original_request_event:
            if approved:
                logger.info(
                    f"Command {command_id} approved. Proceeding with execution."
                )
                # Use asyncio.create_task to run the execution concurrently
                asyncio.create_task(
                    self.execute_command(command_id, original_request_event)
                )
            else:
                logger.info(f"Command {command_id} rejected.")
                # Notify the original sender about the rejection
                rejection_payload = {
                    "command_id": command_id,
                    "command": original_request_event.payload.get("command"),
                    "status": "rejected",
                    "reason": response_payload.get("reason", "Rejected by user."),
                    "output": None,
                    "error": None,
                }
                result_event = SupervisorEvent(
                    event_type=EventType.COMMAND_EXECUTION_RESULT,
                    sender_id="CommandSupervisor",
                    payload=rejection_payload,
                    correlation_id=original_request_event.correlation_id,
                )
                await self.agent_bus.publish(result_event)
                # Clean up status tracking
                with self.lock:
                    if command_id in self.approval_status:
                        del self.approval_status[command_id]

    async def execute_command(self, command_id: str, request_event: SupervisorEvent):
        """Executes the command asynchronously after approval.

        Captures stdout/stderr and publishes the result via AgentBus.
        """
        command = request_event.payload.get("command")
        requester_id = request_event.sender_id
        correlation_id = request_event.correlation_id
        result_payload = {
            "command_id": command_id,
            "command": command,
            "status": "unknown",
            "output": None,
            "error": None,
        }

        try:
            logger.info(f"Executing command: {command} (ID: {command_id})")
            # Using asyncio.create_subprocess_shell for non-blocking execution.
            # Capture stdout and stderr.
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            stdout_str = stdout.decode("utf-8", errors="ignore") if stdout else ""
            stderr_str = stderr.decode("utf-8", errors="ignore") if stderr else ""

            if process.returncode == 0:
                result_payload["status"] = "success"
                result_payload["output"] = stdout_str
                logger.info(f"Command {command_id} executed successfully.")
            else:
                result_payload["status"] = "error"
                result_payload["error"] = (
                    f"Command failed with exit code {process.returncode}: {stderr_str}"
                )
                result_payload["output"] = stdout_str  # Include stdout even on error
                logger.error(f"Command {command_id} failed: {result_payload['error']}")

        except Exception as e:
            error_message = (
                f"Exception during command execution: {traceback.format_exc()}"
            )
            log_exception(e, logger, f"Command execution failed for ID {command_id}")
            result_payload["status"] = "error"
            result_payload["error"] = error_message

        finally:
            # Clean up status tracking
            with self.lock:
                if command_id in self.approval_status:
                    del self.approval_status[command_id]  # Remove entry once done

            # Send the result back to the original requester
            result_event = SupervisorEvent(
                event_type=EventType.COMMAND_EXECUTION_RESULT,
                sender_id="CommandSupervisor",
                payload=result_payload,
                correlation_id=correlation_id,
            )
            await self.agent_bus.publish(result_event)
            logger.info(
                f"Sent execution result for command ID {command_id} to {requester_id}"
            )


# Helper function for agents to request command execution
async def request_command_execution(
    agent_id: str, command: str, details: str = "", correlation_id: Optional[str] = None
):
    """Helper function for agents to publish a command execution request.

    Args:
        agent_id: The ID of the agent making the request.
        command: The shell command string to execute.
        details: Optional additional details about the command's purpose.
        correlation_id: Optional ID to correlate request and response events.

    Returns:
        The correlation ID used for the request.
    """
    bus = AgentBus()  # Get the singleton instance
    request_payload = {"command": command, "details": details}
    # Ensure a correlation ID exists
    _correlation_id = correlation_id or str(uuid4())
    event = SupervisorEvent(
        event_type=EventType.COMMAND_EXECUTION_REQUEST,
        sender_id=agent_id,
        payload=request_payload,
        correlation_id=_correlation_id,
    )
    logger.info(f"Agent {agent_id} requesting command execution: {command}")
    await bus.publish(event)
    return _correlation_id  # Return correlation ID for tracking
