import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from dreamos.core.agent_bus import AgentBus
from dreamos.core.bus_utils import EventType
from dreamos.supervisor_tools.command_supervisor import CommandSupervisor, SupervisorEvent, ApprovalStatus, request_command_execution

# Fixture to provide a mocked AgentBus instance
@pytest.fixture
def mock_agent_bus():
    bus = Mock(spec=AgentBus)
    bus.publish = AsyncMock()
    bus.subscribe = Mock()
    bus.unsubscribe = Mock()
    bus.is_subscriber = Mock(return_value=False) # Default to not subscribed initially
    return bus

# Fixture to provide a CommandSupervisor instance with a mocked bus
@pytest.fixture
def command_supervisor(mock_agent_bus):
    # Ensure Singleton pattern doesn't interfere with testing instances
    if CommandSupervisor._instance:
        CommandSupervisor._instance = None
        CommandSupervisor._initialized = False
    supervisor = CommandSupervisor(agent_bus=mock_agent_bus)
    # Manually call start to set up subscriptions if needed, or mock them
    # supervisor.start() # Might not be needed if we mock subscribe directly
    return supervisor

@pytest.mark.asyncio
async def test_command_supervisor_initialization(command_supervisor, mock_agent_bus):
    """Tests basic initialization and subscription setup."""
    assert command_supervisor.agent_bus == mock_agent_bus
    assert isinstance(command_supervisor.pending_approvals, dict)
    assert isinstance(command_supervisor.approval_status, dict)

    # Simulate the start process calling subscribe
    command_supervisor._run() # This will attempt subscriptions if not already done

    # Check if subscribe was called correctly within _run (assuming start calls _run)
    mock_agent_bus.subscribe.assert_any_call(EventType.COMMAND_EXECUTION_REQUEST, command_supervisor.handle_command_request)
    mock_agent_bus.subscribe.assert_any_call(EventType.COMMAND_APPROVAL_RESPONSE, command_supervisor.handle_approval_response)

@pytest.mark.asyncio
async def test_handle_command_request(command_supervisor, mock_agent_bus):
    """Tests if a command request correctly triggers an approval request."""
    test_command = "echo 'hello'"
    requester_id = "test_agent_1"
    correlation_id = "corr_123"

    request_event = SupervisorEvent(
        event_type=EventType.COMMAND_EXECUTION_REQUEST,
        sender_id=requester_id,
        payload={"command": test_command, "details": "Test execution"},
        correlation_id=correlation_id
    )

    await command_supervisor.handle_command_request(request_event)

    # Verify an approval request was published
    mock_agent_bus.publish.assert_called_once()
    published_event = mock_agent_bus.publish.call_args[0][0]

    assert published_event.event_type == EventType.COMMAND_APPROVAL_REQUEST
    assert published_event.sender_id == "CommandSupervisor"
    assert published_event.correlation_id == correlation_id
    assert "command_id" in published_event.payload
    assert published_event.payload["command"] == test_command
    assert published_event.payload["requesting_agent_id"] == requester_id

    # Verify internal state
    command_id = published_event.payload["command_id"]
    assert command_id in command_supervisor.pending_approvals
    assert command_supervisor.pending_approvals[command_id] == request_event
    assert command_id in command_supervisor.approval_status
    assert command_supervisor.approval_status[command_id] == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_handle_approval_response_approved(command_supervisor, mock_agent_bus):
    """Tests handling an 'approved' response and triggering execution."""
    test_command = "echo 'approved command'"
    requester_id = "test_agent_2"
    correlation_id = "corr_456"
    command_id = "cmd_abc"

    # Setup initial state (as if a request was handled)
    request_event = SupervisorEvent(
        event_type=EventType.COMMAND_EXECUTION_REQUEST,
        sender_id=requester_id,
        payload={"command": test_command},
        correlation_id=correlation_id
    )
    command_supervisor.pending_approvals[command_id] = request_event
    command_supervisor.approval_status[command_id] = ApprovalStatus.PENDING

    # Mock execute_command to prevent actual subprocess calls
    command_supervisor.execute_command = AsyncMock()

    approval_response_event = SupervisorEvent(
        event_type=EventType.COMMAND_APPROVAL_RESPONSE,
        sender_id="human_approver",
        payload={"command_id": command_id, "approved": True}
    )

    await command_supervisor.handle_approval_response(approval_response_event)

    # Verify state updated
    assert command_id not in command_supervisor.pending_approvals
    assert command_supervisor.approval_status[command_id] == ApprovalStatus.APPROVED

    # Verify execute_command was called (using asyncio.create_task internally)
    # We need to give asyncio a chance to schedule the task
    await asyncio.sleep(0.01)
    command_supervisor.execute_command.assert_called_once_with(command_id, request_event)

    # Verify no result event was published *yet* (execute_command handles that)
    mock_agent_bus.publish.assert_not_called() # execute_command mock doesn't publish

@pytest.mark.asyncio
async def test_handle_approval_response_rejected(command_supervisor, mock_agent_bus):
    """Tests handling a 'rejected' response and publishing rejection result."""
    test_command = "echo 'rejected command'"
    requester_id = "test_agent_3"
    correlation_id = "corr_789"
    command_id = "cmd_def"
    reason = "Security concern"

    # Setup initial state
    request_event = SupervisorEvent(
        event_type=EventType.COMMAND_EXECUTION_REQUEST,
        sender_id=requester_id,
        payload={"command": test_command},
        correlation_id=correlation_id
    )
    command_supervisor.pending_approvals[command_id] = request_event
    command_supervisor.approval_status[command_id] = ApprovalStatus.PENDING

    # Mock execute_command to ensure it's NOT called
    command_supervisor.execute_command = AsyncMock()

    rejection_response_event = SupervisorEvent(
        event_type=EventType.COMMAND_APPROVAL_RESPONSE,
        sender_id="human_approver",
        payload={"command_id": command_id, "approved": False, "reason": reason}
    )

    await command_supervisor.handle_approval_response(rejection_response_event)

    # Verify state updated
    assert command_id not in command_supervisor.pending_approvals
    # assert command_supervisor.approval_status[command_id] == ApprovalStatus.REJECTED # Status is deleted upon rejection handling in the code
    assert command_id not in command_supervisor.approval_status


    # Verify execute_command was NOT called
    command_supervisor.execute_command.assert_not_called()

    # Verify rejection result was published
    mock_agent_bus.publish.assert_called_once()
    published_event = mock_agent_bus.publish.call_args[0][0]

    assert published_event.event_type == EventType.COMMAND_EXECUTION_RESULT
    assert published_event.sender_id == "CommandSupervisor"
    assert published_event.correlation_id == correlation_id
    assert published_event.payload["command_id"] == command_id
    assert published_event.payload["command"] == test_command
    assert published_event.payload["status"] == "rejected"
    assert published_event.payload["reason"] == reason

# Example test for the helper function (optional, requires AgentBus setup)
# @pytest.mark.asyncio
# async def test_request_command_execution_helper(mock_agent_bus):
#     """Tests the helper function for requesting execution."""
#     agent_id = "helper_test_agent"
#     command = "ls -l"
#     details = "List files"
#     
#     # Replace the global AgentBus singleton instance with our mock for this test
#     original_instance = AgentBus._instance
#     AgentBus._instance = mock_agent_bus
#     
#     try:
#         correlation_id = await request_command_execution(agent_id, command, details)
# 
#         # Verify publish was called on the mock bus
#         mock_agent_bus.publish.assert_called_once()
#         published_event = mock_agent_bus.publish.call_args[0][0]
# 
#         assert published_event.event_type == EventType.COMMAND_EXECUTION_REQUEST
#         assert published_event.sender_id == agent_id
#         assert published_event.correlation_id == correlation_id # Ensure returned ID matches event
#         assert published_event.payload["command"] == command
#         assert published_event.payload["details"] == details
#     finally:
#         # Restore original AgentBus instance
#         AgentBus._instance = original_instance

# TODO: Add tests for execute_command covering success, failure, and exceptions
# These tests would likely require mocking asyncio.create_subprocess_shell
