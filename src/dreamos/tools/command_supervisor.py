import asyncio
import logging

# import threading # No longer needed
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from dreamos.core.coordination import agent_bus
from dreamos.core.coordination.event_types import EventType

# Setup basic logging - REMOVED basicConfig
# logging.basicConfig(
#     level=logging.INFO, format=\"%(asctime)s - %(name)s - %(levelname)s - %(message)s\"
# )
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


class CommandSupervisor:
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
    """  # noqa: E501

    _instance = None
    _initialized = False

    # FIXME: AgentBus ideally should be passed consistently, not fetched via AgentBus() default call.
    # This assumes AgentBus() reliably provides the correct singleton if None is passed.
    def __init__(self, agent_bus_instance: Optional[agent_bus.AgentBus] = None):
        """Initializes the CommandSupervisor singleton. Now fully async."""
        if self._initialized:
            return
        # self.agent_bus = agent_bus or AgentBus() # Ensure AgentBus is properly managed/injected
        if agent_bus_instance is None:
            logger.warning(
                "CommandSupervisor initialized without an explicit AgentBus. Attempting to get default."
            )
            self.agent_bus = (
                agent_bus.AgentBus()
            )  # This should provide the singleton instance
        else:
            self.agent_bus = agent_bus_instance

        self.pending_approvals: Dict[str, SupervisorEvent] = {}
        self.approval_status: Dict[str, ApprovalStatus] = {}
        self.lock = asyncio.Lock()  # Use asyncio.Lock
        # self._stop_event = threading.Event() # REMOVED
        # self.thread = threading.Thread(target=self._run, daemon=True) # REMOVED
        self._initialized = True
        self._is_listening = False  # Flag to track if listeners are active
        logger.info("CommandSupervisor initialized (async mode).")

    async def start_listeners(self):
        """Subscribes to necessary AgentBus events. Idempotent."""
        if self._is_listening:
            logger.debug("CommandSupervisor listeners already active.")
            return

        logger.info("CommandSupervisor starting listeners...")
        # Subscribe to relevant events
        # Check if already subscribed can be tricky with some bus implementations;
        # assuming bus handles duplicate subscriptions gracefully or provides query methods.
        # For simplicity, we just subscribe. If bus errors on dupes, add checks.
        await self.agent_bus.subscribe(
            EventType.COMMAND_EXECUTION_REQUEST, self.handle_command_request
        )
        await self.agent_bus.subscribe(
            EventType.COMMAND_APPROVAL_RESPONSE, self.handle_approval_response
        )
        self._is_listening = True
        logger.info("CommandSupervisor listeners started and subscribed to events.")

    async def stop_listeners(self):
        """Unsubscribes from AgentBus events gracefully. Idempotent."""
        if not self._is_listening:
            logger.debug("CommandSupervisor listeners already inactive.")
            return

        logger.info("CommandSupervisor stopping listeners...")
        try:
            await self.agent_bus.unsubscribe(
                EventType.COMMAND_EXECUTION_REQUEST, self.handle_command_request
            )
            await self.agent_bus.unsubscribe(
                EventType.COMMAND_APPROVAL_RESPONSE, self.handle_approval_response
            )
            self._is_listening = False
            logger.info("CommandSupervisor listeners stopped and unsubscribed.")
        except Exception as e:
            logger.error(
                f"Error unsubscribing CommandSupervisor listeners: {e}", exc_info=True
            )

    # _run method REMOVED as supervisor is now event-driven within asyncio loop

    async def handle_command_request(
        self, event: SupervisorEvent
    ):  # event type hint might need to match AgentBus's event type
        """Handles incoming `COMMAND_EXECUTION_REQUEST` events."""
        # TODO: Ensure SupervisorEvent matches the actual event type from AgentBus if it's more specific.
        logger.info(f"Received command request: {event.payload} from {event.sender_id}")
        command_id = str(uuid4())
        request_payload = event.payload
        request_payload["command_id"] = command_id

        async with self.lock:  # Use asyncio.Lock
            self.pending_approvals[command_id] = event
            self.approval_status[command_id] = ApprovalStatus.PENDING

        approval_request_payload = {
            "command_id": command_id,
            "command": request_payload.get("command"),
            "requesting_agent_id": event.sender_id,
            "details": request_payload.get("details", "No details provided."),
        }
        # Create and publish event. Ensure SupervisorEvent is compatible or adapt.
        approval_event_data = SupervisorEvent(
            event_type=EventType.COMMAND_APPROVAL_REQUEST,
            sender_id="CommandSupervisor",  # Should be a proper Agent ID if supervisor is an agent
            payload=approval_request_payload,
            correlation_id=event.correlation_id,
        )
        logger.info(
            f"Requesting approval for command ID {command_id}: {request_payload.get('command')}"  # noqa: E501
        )
        # Assuming agent_bus.publish is an async method
        await self.agent_bus.publish(approval_event_data)

    async def handle_approval_response(self, event: SupervisorEvent):  # event type hint
        """Handles incoming `COMMAND_APPROVAL_RESPONSE` events."""
        response_payload = event.payload
        command_id = response_payload.get("command_id")
        approved = response_payload.get("approved", False)
        original_request_event: Optional[SupervisorEvent] = None

        logger.info(
            f"Received approval response for command ID {command_id}: Approved={approved}"  # noqa: E501
        )

        async with self.lock:  # Use asyncio.Lock
            if command_id in self.pending_approvals:
                original_request_event = self.pending_approvals.pop(command_id)
                if approved:
                    self.approval_status[command_id] = ApprovalStatus.APPROVED
                else:
                    self.approval_status[command_id] = ApprovalStatus.REJECTED
            else:
                logger.warning(
                    f"Received approval response for unknown or already processed command ID: {command_id}"  # noqa: E501
                )
                return

        if original_request_event:
            if approved:
                logger.info(
                    f"Command {command_id} approved. Proceeding with execution."
                )
                asyncio.create_task(
                    self.execute_command(command_id, original_request_event)
                )
            else:
                logger.info(f"Command {command_id} rejected.")
                rejection_payload = {
                    "command_id": command_id,
                    "command": original_request_event.payload.get("command"),
                    "status": "rejected",
                    "reason": response_payload.get("reason", "Rejected by user."),
                    "output": None,
                    "error": None,
                }
                result_event_data = SupervisorEvent(
                    event_type=EventType.COMMAND_EXECUTION_RESULT,
                    sender_id="CommandSupervisor",
                    payload=rejection_payload,
                    correlation_id=original_request_event.correlation_id,
                )
                await self.agent_bus.publish(result_event_data)
                async with self.lock:  # Use asyncio.Lock
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

            exit_code = process.returncode
            output = stdout.decode("utf-8", errors="replace").strip()
            error_output = stderr.decode("utf-8", errors="replace").strip()

            if exit_code == 0:
                result_payload["status"] = "completed"
                result_payload["output"] = output
                logger.info(f"Command {command_id} completed successfully.")
            else:
                result_payload["status"] = "failed"
                result_payload["output"] = output
                result_payload["error"] = (
                    f"Exit Code {exit_code}: {error_output}"
                    if error_output
                    else f"Exit Code {exit_code}"
                )
                logger.error(
                    f"Command {command_id} failed with exit code {exit_code}. Error: {error_output or 'N/A'}"
                )

        except Exception as e:
            logger.exception(
                f"Command execution failed unexpectedly for ID {command_id}"
            )
            result_payload["status"] = "error"
            result_payload["error"] = f"Supervisor Error: {type(e).__name__}: {e}"
            # Optionally include traceback
            result_payload["traceback"] = traceback.format_exc()

        finally:
            result_event_data = SupervisorEvent(
                event_type=EventType.COMMAND_EXECUTION_RESULT,
                sender_id="CommandSupervisor",
                payload=result_payload,
                correlation_id=correlation_id,
            )
            await self.agent_bus.publish(result_event_data)
            async with self.lock:  # Use asyncio.Lock
                if command_id in self.approval_status:
                    del self.approval_status[command_id]


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
    bus = agent_bus.AgentBus()  # Get the singleton instance
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
