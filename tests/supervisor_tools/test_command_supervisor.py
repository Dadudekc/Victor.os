import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dreamos.core.agent_bus import AgentBus
from dreamos.core.bus_utils import EventType
from dreamos.supervisor_tools.command_supervisor import (
    ApprovalStatus,
    CommandSupervisor,
    SupervisorEvent,
    request_command_execution,
)


# Fixture to provide a mocked AgentBus instance
@pytest.fixture
def mock_agent_bus():
    bus = Mock(spec=AgentBus)
    bus.publish = AsyncMock()
    bus.subscribe = Mock()
    bus.unsubscribe = Mock()
    bus.is_subscriber = Mock(return_value=False)  # Default to not subscribed initially
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
    command_supervisor._run()  # This will attempt subscriptions if not already done

    # Check if subscribe was called correctly within _run (assuming start calls _run)
    mock_agent_bus.subscribe.assert_any_call(
        EventType.COMMAND_EXECUTION_REQUEST, command_supervisor.handle_command_request
    )
    mock_agent_bus.subscribe.assert_any_call(
        EventType.COMMAND_APPROVAL_RESPONSE, command_supervisor.handle_approval_response
    )


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
        correlation_id=correlation_id,
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
        correlation_id=correlation_id,
    )
    command_supervisor.pending_approvals[command_id] = request_event
    command_supervisor.approval_status[command_id] = ApprovalStatus.PENDING

    # Mock execute_command to prevent actual subprocess calls
    command_supervisor.execute_command = AsyncMock()

    approval_response_event = SupervisorEvent(
        event_type=EventType.COMMAND_APPROVAL_RESPONSE,
        sender_id="human_approver",
        payload={"command_id": command_id, "approved": True},
    )

    await command_supervisor.handle_approval_response(approval_response_event)

    # Verify state updated
    assert command_id not in command_supervisor.pending_approvals
    assert command_supervisor.approval_status[command_id] == ApprovalStatus.APPROVED

    # Verify execute_command was called (using asyncio.create_task internally)
    # We need to give asyncio a chance to schedule the task
    await asyncio.sleep(0.01)
    command_supervisor.execute_command.assert_called_once_with(
        command_id, request_event
    )

    # Verify no result event was published *yet* (execute_command handles that)
    mock_agent_bus.publish.assert_not_called()  # execute_command mock doesn't publish


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
        correlation_id=correlation_id,
    )
    command_supervisor.pending_approvals[command_id] = request_event
    command_supervisor.approval_status[command_id] = ApprovalStatus.PENDING

    # Mock execute_command to ensure it's NOT called
    command_supervisor.execute_command = AsyncMock()

    rejection_response_event = SupervisorEvent(
        event_type=EventType.COMMAND_APPROVAL_RESPONSE,
        sender_id="human_approver",
        payload={"command_id": command_id, "approved": False, "reason": reason},
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

# --- Tests for execute_command ---


# Helper to create a mock process for asyncio.create_subprocess_shell
def create_mock_process(returncode=0, stdout=b"Success output", stderr=b""):
    process = AsyncMock(spec=asyncio.subprocess.Process)
    process.returncode = returncode
    # Mock communicate to return stdout and stderr
    process.communicate = AsyncMock(return_value=(stdout, stderr))
    return process


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_shell")
async def test_execute_command_success(
    mock_create_subprocess, command_supervisor, mock_agent_bus
):
    """Test successful command execution and result publishing."""
    command_id = "cmd_exec_succ"
    test_command = "echo success"
    requester_id = "agent_succ"
    correlation_id = "corr_succ"
    stdout_val = b"Command ran okay"

    request_event = SupervisorEvent(
        event_type=EventType.COMMAND_EXECUTION_REQUEST,
        sender_id=requester_id,
        payload={"command": test_command},
        correlation_id=correlation_id,
    )
    command_supervisor.approval_status[command_id] = (
        ApprovalStatus.APPROVED
    )  # Set state

    # Configure mock process
    mock_process = create_mock_process(returncode=0, stdout=stdout_val)
    mock_create_subprocess.return_value = mock_process

    await command_supervisor.execute_command(command_id, request_event)

    # Verify subprocess call
    mock_create_subprocess.assert_called_once_with(
        test_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    mock_process.communicate.assert_called_once()

    # Verify result published
    mock_agent_bus.publish.assert_called_once()
    published_event = mock_agent_bus.publish.call_args[0][0]

    assert published_event.event_type == EventType.COMMAND_EXECUTION_RESULT
    assert published_event.correlation_id == correlation_id
    assert published_event.payload["command_id"] == command_id
    assert published_event.payload["command"] == test_command
    assert published_event.payload["status"] == "success"
    assert published_event.payload["output"] == stdout_val.decode()
    assert published_event.payload["error"] is None

    # Verify cleanup
    assert command_id not in command_supervisor.approval_status


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_shell")
async def test_execute_command_failure_returncode(
    mock_create_subprocess, command_supervisor, mock_agent_bus
):
    """Test failed command execution (non-zero return code) and result publishing."""
    command_id = "cmd_exec_fail_ret"
    test_command = "exit 1"
    requester_id = "agent_fail_ret"
    correlation_id = "corr_fail_ret"
    stderr_val = b"Something went wrong"

    request_event = SupervisorEvent(
        event_type=EventType.COMMAND_EXECUTION_REQUEST,
        sender_id=requester_id,
        payload={"command": test_command},
        correlation_id=correlation_id,
    )
    command_supervisor.approval_status[command_id] = ApprovalStatus.APPROVED

    # Configure mock process
    mock_process = create_mock_process(returncode=1, stdout=b"", stderr=stderr_val)
    mock_create_subprocess.return_value = mock_process

    await command_supervisor.execute_command(command_id, request_event)

    # Verify subprocess call
    mock_create_subprocess.assert_called_once_with(
        test_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    mock_process.communicate.assert_called_once()

    # Verify result published
    mock_agent_bus.publish.assert_called_once()
    published_event = mock_agent_bus.publish.call_args[0][0]

    assert published_event.event_type == EventType.COMMAND_EXECUTION_RESULT
    assert published_event.correlation_id == correlation_id
    assert published_event.payload["command_id"] == command_id
    assert published_event.payload["status"] == "error"
    assert published_event.payload["output"] == ""
    assert (
        f"Command failed with exit code 1: {stderr_val.decode()[:1000]}"
        in published_event.payload["error"]
    )  # Check truncated error

    # Verify cleanup
    assert command_id not in command_supervisor.approval_status


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_shell", side_effect=OSError("Command not found"))
async def test_execute_command_exception(
    mock_create_subprocess, command_supervisor, mock_agent_bus
):
    """Test exception during command execution and result publishing."""
    command_id = "cmd_exec_fail_exc"
    test_command = "nonexistent_command"
    requester_id = "agent_fail_exc"
    correlation_id = "corr_fail_exc"

    request_event = SupervisorEvent(
        event_type=EventType.COMMAND_EXECUTION_REQUEST,
        sender_id=requester_id,
        payload={"command": test_command},
        correlation_id=correlation_id,
    )
    command_supervisor.approval_status[command_id] = ApprovalStatus.APPROVED

    await command_supervisor.execute_command(command_id, request_event)

    # Verify subprocess call attempted
    mock_create_subprocess.assert_called_once_with(
        test_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    # Verify result published
    mock_agent_bus.publish.assert_called_once()
    published_event = mock_agent_bus.publish.call_args[0][0]

    assert published_event.event_type == EventType.COMMAND_EXECUTION_RESULT
    assert published_event.correlation_id == correlation_id
    assert published_event.payload["command_id"] == command_id
    assert published_event.payload["status"] == "error"
    assert published_event.payload["output"] is None
    assert (
        "Command execution failed: OSError: Command not found"
        in published_event.payload["error"]
    )
    assert "Traceback (most recent call last):" in published_event.payload["error"]

    # Verify cleanup
    assert command_id not in command_supervisor.approval_status


# --- Integration Tests for execute_command (using real subprocess) ---

# Note: These tests interact with the actual shell. Ensure commands are safe.


@pytest.mark.asyncio
async def test_execute_command_real_success(command_supervisor, mock_agent_bus):
    """Test successful execution of a real simple command."""
    command_id = "cmd_real_succ"
    test_command = "echo hello integration test"
    requester_id = "agent_real_succ"
    correlation_id = "corr_real_succ"

    request_event = SupervisorEvent(
        event_type=EventType.COMMAND_EXECUTION_REQUEST,
        sender_id=requester_id,
        payload={"command": test_command},
        correlation_id=correlation_id,
    )
    command_supervisor.approval_status[command_id] = (
        ApprovalStatus.APPROVED
    )  # Simulate approval

    # We are NOT mocking asyncio.create_subprocess_shell here
    await command_supervisor.execute_command(command_id, request_event)

    # Verify result published
    mock_agent_bus.publish.assert_called_once()
    published_event = mock_agent_bus.publish.call_args[0][0]

    assert published_event.event_type == EventType.COMMAND_EXECUTION_RESULT
    assert published_event.correlation_id == correlation_id
    assert published_event.payload["command_id"] == command_id
    assert published_event.payload["command"] == test_command
    assert published_event.payload["status"] == "success"
    # Need to account for potential trailing newline from echo
    assert published_event.payload["output"].strip() == "hello integration test"
    assert published_event.payload["error"] is None


@pytest.mark.asyncio
async def test_execute_command_real_failure_exit_code(
    command_supervisor, mock_agent_bus
):
    """Test execution of a real command failing with a non-zero exit code."""
    command_id = "cmd_real_fail_exit"
    # Use a command guaranteed to fail and produce stderr (adjust for cross-platform if needed)
    # 'exit 1' might not produce stderr, let's use ls on a non-existent file
    test_command = "ls /nonexistent_path_aksjdhflaksjdhf"
    requester_id = "agent_real_fail"
    correlation_id = "corr_real_fail"

    request_event = SupervisorEvent(
        event_type=EventType.COMMAND_EXECUTION_REQUEST,
        sender_id=requester_id,
        payload={"command": test_command},
        correlation_id=correlation_id,
    )
    command_supervisor.approval_status[command_id] = (
        ApprovalStatus.APPROVED
    )  # Simulate approval

    await command_supervisor.execute_command(command_id, request_event)

    # Verify result published
    mock_agent_bus.publish.assert_called_once()
    published_event = mock_agent_bus.publish.call_args[0][0]

    assert published_event.event_type == EventType.COMMAND_EXECUTION_RESULT
    assert published_event.correlation_id == correlation_id
    assert published_event.payload["command_id"] == command_id
    assert published_event.payload["command"] == test_command
    assert published_event.payload["status"] == "error"
    assert published_event.payload["output"] == ""  # ls shouldn't produce stdout here
    assert "Command failed with exit code" in published_event.payload["error"]
    assert (
        "No such file or directory" in published_event.payload["error"]
    )  # Check stderr content


@pytest.mark.asyncio
async def test_execute_command_real_stderr_only(command_supervisor, mock_agent_bus):
    """Test execution of a real command writing only to stderr."""
    command_id = "cmd_real_stderr"
    # Python command to write to stderr
    test_command = "python -c \"import sys; sys.stderr.write('this is stderr output'); sys.exit(0')\""  # Note nested quotes
    requester_id = "agent_real_stderr"
    correlation_id = "corr_real_stderr"

    request_event = SupervisorEvent(
        event_type=EventType.COMMAND_EXECUTION_REQUEST,
        sender_id=requester_id,
        payload={"command": test_command},
        correlation_id=correlation_id,
    )
    command_supervisor.approval_status[command_id] = (
        ApprovalStatus.APPROVED
    )  # Simulate approval

    await command_supervisor.execute_command(command_id, request_event)

    # Verify result published
    mock_agent_bus.publish.assert_called_once()
    published_event = mock_agent_bus.publish.call_args[0][0]

    assert published_event.event_type == EventType.COMMAND_EXECUTION_RESULT
    assert published_event.correlation_id == correlation_id
    assert published_event.payload["command_id"] == command_id
    assert published_event.payload["command"] == test_command
    # Command exits 0, so status is success despite stderr
    assert published_event.payload["status"] == "success"
    assert published_event.payload["output"] == ""
    # NOTE: Current implementation includes stderr in the 'error' field ONLY on non-zero exit.
    # This test verifies stderr isn't *lost*, but it doesn't appear in the success payload.
    # Depending on desired behavior, this might indicate a needed change in command_supervisor.
    assert published_event.payload["error"] is None


@pytest.mark.asyncio
async def test_execute_command_real_no_timeout(command_supervisor, mock_agent_bus):
    """Test that a slightly longer (but reasonable) command completes without timeout."""
    # NOTE: This test confirms completion, but doesn't test actual timeout handling,
    # as the current implementation lacks an explicit timeout on communicate().
    command_id = "cmd_real_sleep"
    test_command = "sleep 1"  # Simple 1-second wait (adjust if needed)
    requester_id = "agent_real_sleep"
    correlation_id = "corr_real_sleep"

    request_event = SupervisorEvent(
        event_type=EventType.COMMAND_EXECUTION_REQUEST,
        sender_id=requester_id,
        payload={"command": test_command},
        correlation_id=correlation_id,
    )
    command_supervisor.approval_status[command_id] = (
        ApprovalStatus.APPROVED
    )  # Simulate approval

    start_time = asyncio.get_event_loop().time()
    await command_supervisor.execute_command(command_id, request_event)
    end_time = asyncio.get_event_loop().time()

    # Verify result published
    mock_agent_bus.publish.assert_called_once()
    published_event = mock_agent_bus.publish.call_args[0][0]

    assert published_event.event_type == EventType.COMMAND_EXECUTION_RESULT
    assert published_event.payload["status"] == "success"
    assert published_event.payload["output"] == ""
    assert published_event.payload["error"] is None
    assert (end_time - start_time) >= 1.0  # Check that it actually waited


@pytest.mark.asyncio
async def test_execute_command_real_complex_args(command_supervisor, mock_agent_bus):
    """Test execution with arguments requiring shell quoting."""
    command_id = "cmd_real_quotes"
    # Command with spaces and nested quotes
    test_command = (
        "echo 'Argument 1' \"Argument with \\\"inner quotes\\\"\" 'Argument 3'"
    )
    expected_output = 'Argument 1 "Argument with \\"inner quotes\\"" Argument 3'
    requester_id = "agent_real_quotes"
    correlation_id = "corr_real_quotes"

    request_event = SupervisorEvent(
        event_type=EventType.COMMAND_EXECUTION_REQUEST,
        sender_id=requester_id,
        payload={"command": test_command},
        correlation_id=correlation_id,
    )
    command_supervisor.approval_status[command_id] = (
        ApprovalStatus.APPROVED
    )  # Simulate approval

    await command_supervisor.execute_command(command_id, request_event)

    # Verify result published
    mock_agent_bus.publish.assert_called_once()
    published_event = mock_agent_bus.publish.call_args[0][0]

    assert published_event.event_type == EventType.COMMAND_EXECUTION_RESULT
    assert published_event.payload["status"] == "success"
    assert published_event.payload["output"].strip() == expected_output
    assert published_event.payload["error"] is None


# TODO: Add test for large output if necessary (might be slow/resource intensive)
# TODO: Add test for potential hangs if process writes excessively to stdout/stderr
#       without being read (communicate() should handle this, but good to verify under stress).
