import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from dreamos.agents.utils.agent_utils import (
    AgentError,
    MessageHandlingError,
    TaskProcessingError,
    format_agent_report,
    handle_task_cancellation,
    log_task_performance,
    publish_error,
    publish_task_update,
    with_error_handling,
    with_performance_tracking,
)
from dreamos.coordination.agent_bus import AgentBus
from dreamos.core.coordination.message_patterns import (
    EventType,
    TaskMessage,
    TaskStatus,
)
from dreamos.core.utils.performance_logger import PerformanceLogger
from dreamos.utils.common_utils import get_utc_iso_timestamp

# --- Test format_agent_report (Synchronous) ---


def test_format_agent_report():
    """Test the synchronous agent report formatting function."""
    report = format_agent_report(
        agent_id="TestAgent001",
        task="process_data",
        status="COMPLETED",
        action="Wrote results to output.txt",
    )

    assert isinstance(report, str)
    assert "Agent: TestAgent001" in report
    assert "Task: process_data" in report
    assert "Status: COMPLETED" in report
    assert "Action: Wrote results to output.txt" in report
    # Check for timestamp presence (format may vary slightly)
    assert "Timestamp:" in report


# --- Tests for Async Functions and Decorators (Requires Mocking) ---


# Mock agent class for testing decorators that need 'self'
class MockAgent:
    def __init__(self, agent_id="test_agent", perf_logger=None, logger=None):
        self.agent_id = agent_id
        self.perf_logger = perf_logger or MagicMock(spec=PerformanceLogger)
        # Use MagicMock for logger to allow attribute access
        self.logger = logger or MagicMock()


# --- Test with_error_handling Decorator ---
@pytest.mark.asyncio
async def test_with_error_handling_success():
    """Test that the decorated function runs normally on success."""
    mock_agent = MockAgent()

    @with_error_handling()
    async def successful_func(self, arg1, kwarg1=None):
        return f"Success: {arg1} {kwarg1}"

    result = await successful_func(mock_agent, "hello", kwarg1="world")
    assert result == "Success: hello world"
    mock_agent.logger.error.assert_not_called()


@pytest.mark.asyncio
@patch("dreamos.agents.utils.agent_utils.log_event")  # Mock log_event
async def test_with_error_handling_exception(mock_log_event):
    """Test that exceptions are caught, logged, and re-raised."""
    mock_agent = MockAgent()
    original_exception = ValueError("Something went wrong")

    @with_error_handling(error_class=TaskProcessingError)
    async def failing_func(self, arg1):
        raise original_exception

    with pytest.raises(TaskProcessingError) as excinfo:
        await failing_func(mock_agent, "bad_arg")

    # Check that the correct exception type was raised
    assert "Something went wrong" in str(excinfo.value)
    # Check that the original exception is the cause
    assert excinfo.value.__cause__ is original_exception

    # Check logger was called
    mock_agent.logger.error.assert_called_once()
    log_args, log_kwargs = mock_agent.logger.error.call_args
    assert "Error in failing_func: Something went wrong" in log_args[0]
    assert log_kwargs.get("exc_info") is True

    # Check governance log_event was called
    mock_log_event.assert_called_once()
    event_type, agent_id, details = mock_log_event.call_args[0]
    assert event_type == "AGENT_UTIL_ERROR"
    assert agent_id == mock_agent.agent_id
    assert details["error"] == str(original_exception)
    assert "ValueError: Something went wrong" in details["traceback"]


# --- Test with_performance_tracking Decorator ---
@pytest.mark.asyncio
async def test_with_performance_tracking_success():
    """Test that performance tracking context manager is used."""
    mock_perf_logger = MagicMock(spec=PerformanceLogger)
    # Mock the context manager behavior
    mock_context = MagicMock()
    mock_perf_logger.track_operation.return_value = mock_context

    mock_agent = MockAgent(perf_logger=mock_perf_logger)

    @with_performance_tracking("test_operation")
    async def tracked_func(self, arg1):
        return f"Tracked: {arg1}"

    result = await tracked_func(mock_agent, "data")
    assert result == "Tracked: data"

    mock_perf_logger.track_operation.assert_called_once_with("test_operation")
    # Check that the context manager's __aenter__ and __aexit__ were called (MagicMock tracks this)
    mock_context.__aenter__.assert_called_once()
    mock_context.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_with_performance_tracking_no_logger():
    """Test that it handles cases where perf_logger is missing/invalid."""
    # Test with no perf_logger
    mock_agent_no_logger = MockAgent(perf_logger=None)
    # Test with invalid perf_logger
    mock_agent_bad_logger = MockAgent(perf_logger="not a logger")

    @with_performance_tracking("test_operation")
    async def tracked_func(self, arg1):
        # Access self to ensure it's passed correctly
        return f"Tracked: {self.agent_id} {arg1}"

    # Should run without error and without calling track_operation
    result_no = await tracked_func(mock_agent_no_logger, "data1")
    assert result_no == f"Tracked: {mock_agent_no_logger.agent_id} data1"

    result_bad = await tracked_func(mock_agent_bad_logger, "data2")
    assert result_bad == f"Tracked: {mock_agent_bad_logger.agent_id} data2"
    # We expect warnings to be logged by the decorator itself, but difficult to assert here without capturing logs


# --- Test publish_task_update ---
@pytest.mark.asyncio
async def test_publish_task_update_success():
    mock_bus = AsyncMock(spec=AgentBus)
    mock_task = Mock(spec=TaskMessage)
    mock_task.task_id = "task-123"
    mock_task.correlation_id = "corr-456"
    mock_task.status = TaskStatus.COMPLETED
    mock_task.to_dict.return_value = {"task_id": "task-123", "status": "COMPLETED"}

    await publish_task_update(mock_bus, mock_task, "agent-abc")

    mock_bus.publish.assert_called_once()
    topic, payload = mock_bus.publish.call_args[0]
    assert topic == "system.task.task-123.event.updated"
    assert payload["sender_id"] == "agent-abc"
    assert payload["correlation_id"] == "corr-456"
    assert payload["data"]["task_id"] == "task-123"


@pytest.mark.asyncio
async def test_publish_task_update_failure():
    """Test that publish errors are caught and logged."""
    mock_bus = AsyncMock(spec=AgentBus)
    mock_bus.publish.side_effect = ConnectionError("Bus down")
    mock_task = Mock(spec=TaskMessage)
    mock_task.task_id = "task-fail"
    mock_task.correlation_id = "corr-fail"
    mock_task.status = TaskStatus.FAILED
    mock_task.to_dict.return_value = {"task_id": "task-fail", "status": "FAILED"}

    # Use patch to capture logs from the util_logger
    with patch("dreamos.agents.utils.agent_utils.util_logger") as mock_logger:
        await publish_task_update(mock_bus, mock_task, "agent-err")

    mock_bus.publish.assert_called_once()
    mock_logger.error.assert_called_once()
    log_args, log_kwargs = mock_logger.error.call_args
    assert "Failed to publish task update for task-fail" in log_args[0]
    assert log_kwargs.get("exc_info") is True


# --- Test publish_error ---
@pytest.mark.asyncio
async def test_publish_error_no_correlation_id():
    """Test publishing a system error without a correlation ID."""
    mock_bus = AsyncMock(spec=AgentBus)
    agent_id = "ErrorAgent"
    error_msg = "Something bad happened"
    details = {"detail_key": "detail_value"}

    await publish_error(
        mock_bus, error_msg, agent_id, correlation_id=None, details=details
    )

    # Should publish only to the system error topic
    mock_bus.publish.assert_called_once()
    topic, payload = mock_bus.publish.call_args[0]

    assert topic == EventType.SYSTEM_ERROR.value
    assert payload["sender_id"] == agent_id
    assert payload["correlation_id"] is None
    assert payload["data"]["error"] == error_msg
    assert payload["data"]["source_agent"] == agent_id
    assert payload["data"]["detail_key"] == "detail_value"
    assert "traceback" in payload["data"]  # Check traceback is included


@pytest.mark.asyncio
async def test_publish_error_with_correlation_id():
    """Test publishing an error with a correlation ID (system + response topics)."""
    mock_bus = AsyncMock(spec=AgentBus)
    agent_id = "ResponseErrorAgent"
    error_msg = "Request failed"
    correlation_id = "req-789"

    await publish_error(mock_bus, error_msg, agent_id, correlation_id=correlation_id)

    # Should publish twice: system error topic and response error topic
    assert mock_bus.publish.call_count == 2

    # Call 1: System Error Topic
    call1_args, _ = mock_bus.publish.call_args_list[0]
    topic1, payload1 = call1_args
    assert topic1 == EventType.SYSTEM_ERROR.value
    assert payload1["correlation_id"] == correlation_id
    assert payload1["data"]["error"] == error_msg

    # Call 2: Response Error Topic
    call2_args, _ = mock_bus.publish.call_args_list[1]
    topic2, payload2 = call2_args
    assert topic2 == f"system.response.{correlation_id}.error"
    assert payload2["correlation_id"] == correlation_id
    assert payload2["data"]["error"] == error_msg

    # Payloads should be identical
    assert payload1 == payload2


@pytest.mark.asyncio
async def test_publish_error_bus_failure():
    """Test that errors during bus publish are logged."""
    mock_bus = AsyncMock(spec=AgentBus)
    mock_bus.publish.side_effect = ConnectionError("Cannot connect")

    with patch("dreamos.agents.utils.agent_utils.util_logger") as mock_logger:
        await publish_error(
            mock_bus, "Test failure", "agent-x", correlation_id="corr-x"
        )

    # Should attempt to publish twice, both fail and log
    assert mock_bus.publish.call_count == 2
    assert mock_logger.error.call_count == 2
    assert (
        "Failed to publish system error message"
        in mock_logger.error.call_args_list[0][0][0]
    )
    assert (
        "Failed to publish error response message"
        in mock_logger.error.call_args_list[1][0][0]
    )


# --- Test handle_task_cancellation ---
@pytest.mark.asyncio
async def test_handle_task_cancellation_active_task():
    """Test cancelling an active task."""
    mock_bus = AsyncMock(spec=AgentBus)
    mock_task_to_cancel = AsyncMock(spec=asyncio.Task)
    mock_task_to_cancel.done.return_value = False
    active_tasks = {"task-cancel-1": mock_task_to_cancel}
    agent_id = "CancellerAgent"
    correlation_id = "cancel-req-1"

    await handle_task_cancellation(
        "task-cancel-1", active_tasks, mock_bus, agent_id, correlation_id
    )

    mock_task_to_cancel.cancel.assert_called_once()
    # Check that a success response is published
    mock_bus.publish.assert_called_once()
    topic, payload = mock_bus.publish.call_args[0]
    assert topic == f"system.response.{correlation_id}.result"
    assert payload["sender_id"] == agent_id
    assert payload["data"]["status"] == "CANCELLED"
    assert payload["data"]["task_id"] == "task-cancel-1"


@pytest.mark.asyncio
async def test_handle_task_cancellation_task_not_found():
    """Test cancelling a task that isn't in the active list."""
    mock_bus = AsyncMock(spec=AgentBus)
    active_tasks = {}
    agent_id = "CancellerAgent"
    correlation_id = "cancel-req-2"

    await handle_task_cancellation(
        "task-cancel-2", active_tasks, mock_bus, agent_id, correlation_id
    )

    # Should publish an error response
    mock_bus.publish.assert_called_once()
    topic, payload = mock_bus.publish.call_args[0]
    assert topic == f"system.response.{correlation_id}.error"  # Error topic
    assert payload["data"]["error"] == "Task not found or already completed."
    assert payload["data"]["task_id"] == "task-cancel-2"


@pytest.mark.asyncio
async def test_handle_task_cancellation_task_already_done():
    """Test cancelling a task that is already done."""
    mock_bus = AsyncMock(spec=AgentBus)
    mock_task_done = AsyncMock(spec=asyncio.Task)
    mock_task_done.done.return_value = True  # Task is already done
    active_tasks = {"task-cancel-3": mock_task_done}
    agent_id = "CancellerAgent"
    correlation_id = "cancel-req-3"

    await handle_task_cancellation(
        "task-cancel-3", active_tasks, mock_bus, agent_id, correlation_id
    )

    mock_task_done.cancel.assert_not_called()
    # Should publish an error response
    mock_bus.publish.assert_called_once()
    topic, payload = mock_bus.publish.call_args[0]
    assert topic == f"system.response.{correlation_id}.error"  # Error topic
    assert payload["data"]["error"] == "Task not found or already completed."


# --- Test log_task_performance ---
@pytest.mark.asyncio  # Needs to be async if perf_logger methods become async
async def test_log_task_performance():
    """Test logging task performance data."""
    mock_perf_logger = MagicMock(spec=PerformanceLogger)
    mock_task = Mock(spec=TaskMessage)
    mock_task.task_id = "perf-task-1"
    mock_task.name = "Performance Test Task"
    mock_task.status = TaskStatus.COMPLETED
    agent_id = "PerfAgent"

    # Simulate some performance data
    mock_perf_logger.get_operation_summary.return_value = {
        "total_time": 1.23,
        "call_count": 5,
        "avg_time": 0.246,
    }

    log_task_performance(mock_task, agent_id, mock_perf_logger)

    mock_perf_logger.log_summary.assert_called_once()
    log_args, _ = mock_perf_logger.log_summary.call_args
    context = log_args[0]
    assert context["agent_id"] == agent_id
    assert context["task_id"] == "perf-task-1"
    assert context["task_name"] == "Performance Test Task"
    assert context["final_status"] == TaskStatus.COMPLETED.name
