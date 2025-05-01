import asyncio
import logging
import sys  # For publish_agent_error test
import traceback  # For publish_agent_error test
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Queue
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from dreamos.coordination.agent_bus import AgentBus, BaseEvent, EventType
from dreamos.core.coordination.base_agent import (
    BaseAgent,
    MessageHandlingError,
    TaskMessage,
    TaskPriority,
    TaskProcessingError,
    TaskStatus,
)
from dreamos.core.coordination.event_payloads import (
    ErrorEventPayload,
    TaskCompletionPayload,
    TaskEventPayload,
    TaskFailurePayload,
    TaskProgressPayload,
)
from dreamos.core.coordination.message_patterns import TaskUpdate  # Import TaskUpdate


# --- Concrete Subclass for Testing ---
class ConcreteAgent(BaseAgent):
    async def _on_start(self):
        self.logger.info("ConcreteAgent _on_start called")
        await asyncio.sleep(0)  # Yield control

    async def _on_stop(self):
        self.logger.info("ConcreteAgent _on_stop called")
        await asyncio.sleep(0)

    # Example command handler
    async def handle_example_command(self, task: TaskMessage) -> dict:
        self.logger.info(f"Handling example command for task {task.task_id}")
        await asyncio.sleep(0.01)
        return {"result": "success"}


# --- Fixtures ---


@pytest.fixture
def mock_agent_bus() -> MagicMock:
    bus = MagicMock()
    bus.subscribe = AsyncMock(return_value="sub123")  # Mock subscribe as async
    bus.unsubscribe = AsyncMock()
    bus.dispatch_event = AsyncMock()
    return bus


@pytest.fixture
def test_agent(mock_agent_bus: MagicMock, tmp_path: Path) -> ConcreteAgent:
    """Provides an instance of the concrete agent for testing."""
    agent_id = "test_agent_001"
    # Disable performance logger for most tests unless specifically testing it
    with patch("dreamos.core.coordination.base_agent.PerformanceLogger", MagicMock()):
        agent = ConcreteAgent(
            agent_id=agent_id,
            agent_bus=mock_agent_bus,
            task_list_path=tmp_path / "tasks.json",
        )
        agent.register_command_handler("EXAMPLE_COMMAND", agent.handle_example_command)
        return agent


# --- Test Cases ---


def test_base_agent_init(
    test_agent: ConcreteAgent, mock_agent_bus: MagicMock, tmp_path: Path
):
    """Test basic initialization of the BaseAgent."""
    assert test_agent.agent_id == "test_agent_001"
    assert test_agent.agent_bus == mock_agent_bus
    assert test_agent.task_list_path == tmp_path / "tasks.json"
    assert isinstance(test_agent.logger, logging.Logger)
    assert test_agent._running is False
    assert "EXAMPLE_COMMAND" in test_agent._command_handlers


@pytest.mark.asyncio
async def test_base_agent_start(test_agent: ConcreteAgent, mock_agent_bus: MagicMock):
    """Test the start sequence, including task processor startup."""
    created_task = None

    # Helper to capture the task created by asyncio.create_task
    def capture_task(coro):
        nonlocal created_task
        task = asyncio.create_task(coro)
        created_task = task
        return task

    with (
        patch.object(test_agent, "_on_start", new_callable=AsyncMock) as mock_on_start,
        patch("asyncio.create_task", side_effect=capture_task) as mock_create_task,
    ):

        await test_agent.start()

        assert test_agent._running is True
        mock_agent_bus.subscribe.assert_awaited_once()
        # Check topic subscription
        subscribe_call_args = mock_agent_bus.subscribe.await_args
        assert (
            subscribe_call_args[0][0]
            == f"dreamos.agent.{test_agent.agent_id}.task.command"
        )
        assert subscribe_call_args[0][1] == test_agent._handle_command

        mock_create_task.assert_called_once()  # Task processor started
        assert created_task is not None  # Ensure task was captured
        # Optional: Add cleanup for the captured task if it doesn't get cancelled in stop
        # if not created_task.done(): created_task.cancel()

        mock_on_start.assert_awaited_once()  # Agent-specific start called


@pytest.mark.asyncio
async def test_base_agent_stop(test_agent: ConcreteAgent, mock_agent_bus: MagicMock):
    """Test the stop sequence."""
    # Simulate agent started state
    test_agent._running = True
    test_agent._subscription_id = "sub123"
    # Create a mock task object to represent the running task processor
    mock_task_processor = MagicMock(spec=asyncio.Task)
    mock_task_processor.cancel = MagicMock()
    test_agent._task_processor_task = mock_task_processor  # Assign the mock task

    with patch.object(test_agent, "_on_stop", new_callable=AsyncMock) as mock_on_stop:
        await test_agent.stop()

        assert test_agent._running is False
        # Check if the task processor's cancel method was called
        mock_task_processor.cancel.assert_called_once()

        # Verify unsubscribe was called with the correct topic and handler
        mock_agent_bus.unsubscribe.assert_awaited_once_with(
            test_agent._command_topic, test_agent._command_handler_ref
        )
        mock_on_stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_base_agent_register_command_handler(test_agent: ConcreteAgent):
    """Test registering a command handler."""

    async def dummy_handler(task):
        pass

    test_agent.register_command_handler("DUMMY_CMD", dummy_handler)
    assert "DUMMY_CMD" in test_agent._command_handlers
    assert test_agent._command_handlers["DUMMY_CMD"] == dummy_handler


@pytest.mark.asyncio
async def test_base_agent_publish_event_helpers(
    test_agent: ConcreteAgent, mock_agent_bus: MagicMock
):
    """Test the various publish_task_* helper methods."""
    mock_task_dict = {"task_id": "t-pub", "task_type": "TEST", "params": {}}
    # Use TaskMessage's validation/defaults
    mock_task = TaskMessage(
        task_id="t-pub",
        task_type="TEST",
        params={},
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING,
    )
    correlation_id = mock_task.correlation_id  # Should be generated by TaskMessage

    # Test TASK_ACCEPTED
    await test_agent.publish_task_accepted(mock_task)
    mock_agent_bus.dispatch_event.assert_awaited_with(
        BaseEvent(
            EventType.TASK_ACCEPTED,
            test_agent.agent_id,
            mock_task.to_dict(),
            correlation_id,
        )
    )

    # Test TASK_STARTED
    await test_agent.publish_task_started(mock_task)
    mock_agent_bus.dispatch_event.assert_awaited_with(
        BaseEvent(
            EventType.TASK_STARTED,
            test_agent.agent_id,
            mock_task.to_dict(),
            correlation_id,
        )
    )

    # Test TASK_PROGRESS
    progress_details = "Halfway there"
    await test_agent.publish_task_progress(mock_task, 0.5, progress_details)
    expected_progress_data = mock_task.to_dict()
    expected_progress_data["progress"] = 0.5
    expected_progress_data["progress_details"] = progress_details
    mock_agent_bus.dispatch_event.assert_awaited_with(
        BaseEvent(
            EventType.TASK_PROGRESS,
            test_agent.agent_id,
            expected_progress_data,
            correlation_id,
        )
    )

    # Test TASK_COMPLETED
    result_data = {"output": "done"}
    await test_agent.publish_task_completed(mock_task, result_data)
    expected_completed_data = mock_task.to_dict()
    expected_completed_data["result"] = result_data
    mock_agent_bus.dispatch_event.assert_awaited_with(
        BaseEvent(
            EventType.TASK_COMPLETED,
            test_agent.agent_id,
            expected_completed_data,
            correlation_id,
        )
    )

    # Test TASK_FAILED
    error_message = "It broke"
    await test_agent.publish_task_failed(mock_task, error_message, is_final=True)
    expected_failed_data = mock_task.to_dict()
    expected_failed_data["error"] = error_message
    expected_failed_data["is_final"] = True
    mock_agent_bus.dispatch_event.assert_awaited_with(
        BaseEvent(
            EventType.TASK_FAILED,
            test_agent.agent_id,
            expected_failed_data,
            correlation_id,
        )
    )

    # Test AGENT_ERROR
    error_details = {"code": 500}
    await test_agent.publish_agent_error("Core meltdown", error_details, correlation_id)
    expected_error_data = ErrorEventPayload(
        error_message="Core meltdown",
        details=error_details,
        agent_id=test_agent.agent_id,
    ).to_dict()
    mock_agent_bus.dispatch_event.assert_awaited_with(
        BaseEvent(
            EventType.AGENT_ERROR,
            test_agent.agent_id,
            expected_error_data,
            correlation_id,
        )
    )


# --- Tests for Internal Methods ---


@pytest.mark.asyncio
async def test_handle_command_valid(
    test_agent: ConcreteAgent, mock_agent_bus: MagicMock
):
    """Test _handle_command with a valid task message."""
    task_data = {
        "task_id": "cmd-task-001",
        "task_type": "EXAMPLE_COMMAND",
        "params": {"param1": "value1"},
        "priority": "HIGH",  # Test string enum conversion
        "status": "PENDING",  # Should be ignored and set by handler
        "correlation_id": "corr-123",
    }
    event = BaseEvent(
        EventType.TASK_COMMAND, "sender_agent", task_data, task_data["correlation_id"]
    )

    with (
        patch.object(
            test_agent, "publish_task_accepted", new_callable=AsyncMock
        ) as mock_publish,
        patch.object(
            test_agent._task_queue, "put", new_callable=AsyncMock
        ) as mock_queue_put,
    ):
        await test_agent._handle_command(event)

        mock_publish.assert_awaited_once()
        # Check that the published task has the correct initial status and priority
        published_task: TaskMessage = mock_publish.await_args[0][0]
        assert isinstance(published_task, TaskMessage)
        assert published_task.task_id == "cmd-task-001"
        assert published_task.task_type == "EXAMPLE_COMMAND"
        assert published_task.params == {"param1": "value1"}
        assert published_task.priority == TaskPriority.HIGH
        assert published_task.status == TaskStatus.ACCEPTED  # Status is set by handler
        assert published_task.correlation_id == "corr-123"

        mock_queue_put.assert_awaited_once()
        # Check that the correct task tuple was put into the queue
        queued_item = mock_queue_put.await_args[0][0]
        assert len(queued_item) == 2
        assert (
            queued_item[0] == TaskPriority.HIGH.value
        )  # Priority value is used for sorting
        assert queued_item[1] == published_task  # The validated TaskMessage object


@pytest.mark.asyncio
async def test_handle_command_invalid_data(
    test_agent: ConcreteAgent, mock_agent_bus: MagicMock
):
    """Test _handle_command with invalid task data (missing required fields)."""
    invalid_task_data = {
        "task_type": "EXAMPLE_COMMAND",  # Missing task_id
        "params": {},
    }
    correlation_id = "corr-456"
    event = BaseEvent(
        EventType.TASK_COMMAND, "sender_agent", invalid_task_data, correlation_id
    )

    with (
        patch.object(
            test_agent, "publish_agent_error", new_callable=AsyncMock
        ) as mock_publish_error,
        patch.object(
            test_agent._task_queue, "put", new_callable=AsyncMock
        ) as mock_queue_put,
    ):
        await test_agent._handle_command(event)

        mock_publish_error.assert_awaited_once()
        # Check the error details
        error_args = mock_publish_error.await_args[0]
        assert "Invalid task message format" in error_args[0]
        assert isinstance(
            error_args[1]["validation_error"], str
        )  # Pydantic error details
        assert error_args[2] == correlation_id

        mock_queue_put.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_command_unknown_type(
    test_agent: ConcreteAgent, mock_agent_bus: MagicMock
):
    """Test _handle_command with an unknown task type."""
    task_data = {
        "task_id": "cmd-task-002",
        "task_type": "UNKNOWN_COMMAND",
        "params": {},
    }
    correlation_id = "corr-789"
    event = BaseEvent(EventType.TASK_COMMAND, "sender_agent", task_data, correlation_id)

    with (
        patch.object(
            test_agent, "publish_task_failed", new_callable=AsyncMock
        ) as mock_publish_failed,
        patch.object(
            test_agent._task_queue, "put", new_callable=AsyncMock
        ) as mock_queue_put,
    ):
        await test_agent._handle_command(event)

        mock_publish_failed.assert_awaited_once()
        failed_task: TaskMessage = mock_publish_failed.await_args[0][0]
        error_msg: str = mock_publish_failed.await_args[0][1]
        is_final: bool = mock_publish_failed.await_args[0][2]

        assert failed_task.task_id == "cmd-task-002"
        assert failed_task.status == TaskStatus.FAILED  # Should be marked failed
        assert "No handler registered" in error_msg
        assert is_final is True

        mock_queue_put.assert_not_awaited()


# TODO: Add tests for _process_task_queue, _process_single_task

# --- Test BaseAgent Stop Unsubscribe ---


@pytest.mark.asyncio
async def test_base_agent_stop_unsubscribes(mock_agent_bus, tmp_path):
    """Verify specifically that BaseAgent.stop calls agent_bus.unsubscribe."""

    # Create a minimal agent instance for this specific test
    # Use ConcreteAgent or patch BaseAgent if needed
    class MinimalAgent(BaseAgent):
        async def _on_start(self):
            pass

        async def _on_stop(self):
            pass

    agent = MinimalAgent(
        agent_id="stop_test_agent",
        agent_bus=mock_agent_bus,
        task_list_path=tmp_path / "tasks.json",
    )

    # Simulate the state after start() has run
    agent._running = True
    command_topic = f"agent.{agent.agent_id}.task.command"
    command_handler = agent._handle_command  # Get the actual handler reference
    agent._command_topic = command_topic
    agent._command_handler_ref = command_handler
    # Mock the task processor task object as it's needed in stop()
    agent._task_processor_task = AsyncMock(spec=asyncio.Task)
    agent._task_processor_task.cancel = MagicMock()

    # Call stop
    await agent.stop()

    # Assert unsubscribe was called correctly
    mock_agent_bus.unsubscribe.assert_awaited_once_with(command_topic, command_handler)


@pytest.mark.asyncio
async def test_publish_agent_error(test_agent, mock_agent_bus):
    """Test publishing an agent error specifically."""
    error_msg = "Specific agent error"
    details = {"info": "extra"}
    correlation_id = "corr-id-agent-err"
    task_id = "t-agent-err"

    # Get traceback information
    try:
        raise ValueError(error_msg)
    except ValueError:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb_str = "\n".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )

    await test_agent.publish_agent_error(
        error_msg,
        details=details,
        correlation_id=correlation_id,
        task_id=task_id,
        exception_type=exc_type.__name__,
        traceback=tb_str,
    )

    # EDIT: Use ErrorEventPayload structure
    expected_payload = ErrorEventPayload(
        error_message=error_msg,
        agent_id=test_agent.agent_id,
        task_id=task_id,
        exception_type=exc_type.__name__,
        traceback=tb_str,
        details=details,
    )

    mock_agent_bus.dispatch_event.assert_awaited_once_with(
        BaseEvent(
            event_type=EventType.AGENT_ERROR,
            source_id=test_agent.agent_id,
            data=expected_payload.to_dict(),  # Assuming ErrorEventPayload needs to_dict()
            correlation_id=correlation_id,
        )
    )


# Helper function to create tasks for testing
def create_sample_task(
    task_id="test-task-123",
    command_type="TEST_CMD",
    params=None,
    status=TaskStatus.ACCEPTED,
):
    return TaskMessage(
        task_id=task_id,
        task_type=command_type,
        command_type=command_type,  # Ensure command_type is set too
        params=params or {},
        status=status,
        priority=TaskPriority.MEDIUM,
    )


# Fixture to provide a BaseAgent instance with mocked dependencies
@pytest.fixture
def mock_agent(mock_agent_bus, tmp_path):
    agent_id = "mock_agent_001"
    with (
        patch("dreamos.core.coordination.base_agent.PerformanceLogger", MagicMock()),
        patch(
            "dreamos.core.coordination.base_agent.persist_task_update",
            new_callable=AsyncMock,
        ) as mock_persist,
        patch.object(BaseAgent, "publish_task_accepted", new_callable=AsyncMock),
        patch.object(BaseAgent, "publish_task_started", new_callable=AsyncMock),
        patch.object(BaseAgent, "publish_task_completed", new_callable=AsyncMock),
        patch.object(BaseAgent, "publish_task_failed", new_callable=AsyncMock),
        patch.object(BaseAgent, "publish_validation_failed", new_callable=AsyncMock),
        patch.object(BaseAgent, "publish_agent_error", new_callable=AsyncMock),
    ):
        # Need a concrete class to instantiate
        class MockConcreteAgent(BaseAgent):
            async def _on_start(self):
                pass

            async def _on_stop(self):
                pass

            # Need a default handler for tests
            async def handle_default_test_command(self, task: TaskMessage) -> dict:
                return {"result": "mock success", "summary": "Mock handler ran"}

        agent = MockConcreteAgent(
            agent_id=agent_id,
            agent_bus=mock_agent_bus,
            task_list_path=tmp_path / "tasks.json",
        )
        agent.register_command_handler(
            "test_command", agent.handle_default_test_command
        )
        agent.persist_task_update = mock_persist  # Attach mock for easy access in tests
        yield agent  # Yield the agent for use in tests


# --- Tests for _validate_task_completion ---


@pytest.mark.asyncio
async def test_validate_task_completion_success_with_summary(mock_agent):
    """Verify base validation passes with a valid result dict including summary."""
    task = create_sample_task()
    result = {"output": "data", "summary": "All good"}

    passed, details = await mock_agent._validate_task_completion(task, result)

    assert passed is True
    assert "Basic validation checks passed" in details
    mock_agent.publish_validation_failed.assert_not_called()


@pytest.mark.asyncio
async def test_validate_task_completion_success_without_summary(mock_agent):
    """Verify base validation passes (with warning) if result lacks summary."""
    task = create_sample_task()
    result = {"output": "data only"}  # No summary

    passed, details = await mock_agent._validate_task_completion(task, result)

    assert passed is True  # Currently only warns, doesn't fail
    assert "Handler result lacks a 'summary' key" in details
    mock_agent.publish_validation_failed.assert_not_called()


@pytest.mark.asyncio
async def test_validate_task_completion_fail_empty_result(mock_agent):
    """Verify base validation fails if the result dict is empty."""
    task = create_sample_task()
    result = {}  # Empty result

    passed, details = await mock_agent._validate_task_completion(task, result)

    assert passed is False
    assert "Handler result dictionary is missing, None, or empty" in details
    mock_agent.publish_validation_failed.assert_awaited_once()
    # Check the details passed to the publish call
    call_args = mock_agent.publish_validation_failed.await_args[0]
    assert task == call_args[0]
    assert "Handler result dictionary is missing, None, or empty" in call_args[1]


@pytest.mark.asyncio
async def test_validate_task_completion_fail_none_result(mock_agent):
    """Verify base validation fails if the result is None."""
    task = create_sample_task()
    result = None  # None result

    passed, details = await mock_agent._validate_task_completion(task, result)

    assert passed is False
    assert "Handler result dictionary is missing, None, or empty" in details
    mock_agent.publish_validation_failed.assert_awaited_once()
    # Check the details passed to the publish call
    call_args = mock_agent.publish_validation_failed.await_args[0]
    assert task == call_args[0]
    assert "Handler result dictionary is missing, None, or empty" in call_args[1]


# --- Existing tests for _process_single_task (might need adjustment if mocks change) ---


@pytest.mark.asyncio
async def test_process_single_task_success_with_validation_pass(mock_agent):
    """Verify task processing completes and persists COMPLETED status when validation passes."""
    task = create_sample_task(command_type="test_command")
    handler_result = {"output": "success", "summary": "Handler success summary"}
    mock_handler = AsyncMock(return_value=handler_result)
    mock_agent.register_command_handler("test_command", mock_handler)

    # Mock validation to return True
    mock_agent._validate_task_completion = AsyncMock(
        return_value=(True, "Validation passed")
    )

    # Mock persistence function (assuming it's globally available or mocked via patch)
    with patch(
        "dreamos.core.coordination.base_agent.persist_task_update",
        new_callable=AsyncMock,
    ) as mock_persist:
        await mock_agent._process_single_task(task, None)

    # Assertions
    mock_handler.assert_awaited_once_with(task)
    mock_agent._validate_task_completion.assert_awaited_once_with(task, handler_result)
    mock_agent.publish_task_completed.assert_awaited_once_with(
        task, result=handler_result
    )

    # Check persistence calls: WORKING then COMPLETED
    expected_persist_calls = [
        call(task.task_id, TaskStatus.WORKING),
        call(
            task.task_id, TaskStatus.COMPLETED, result_summary="Handler success summary"
        ),
    ]
    mock_persist.assert_has_awaits(
        expected_persist_calls, any_order=False
    )  # Ensure order

    # Ensure validation failure paths weren't called
    mock_agent.publish_validation_failed.assert_not_called()  # Assuming this helper exists and is called by _validate... or base agent


@pytest.mark.asyncio
async def test_process_single_task_success_with_validation_fail(mock_agent):
    """Verify task processing persists VALIDATION_FAILED status when validation fails."""
    task = create_sample_task(command_type="test_command")
    handler_result = {
        "output": "some data",
        "summary": "Handler ran",
    }  # Handler still completes
    validation_details = "Output format incorrect."
    mock_handler = AsyncMock(return_value=handler_result)
    mock_agent.register_command_handler("test_command", mock_handler)

    # Mock validation to return False
    mock_agent._validate_task_completion = AsyncMock(
        return_value=(False, validation_details)
    )

    # Mock persistence function
    with patch(
        "dreamos.core.coordination.base_agent.persist_task_update",
        new_callable=AsyncMock,
    ) as mock_persist:
        await mock_agent._process_single_task(task, None)

    # Assertions
    mock_handler.assert_awaited_once_with(task)
    mock_agent._validate_task_completion.assert_awaited_once_with(task, handler_result)

    # Check persistence calls: WORKING then VALIDATION_FAILED
    expected_persist_calls = [
        call(task.task_id, TaskStatus.WORKING),
        call(task.task_id, TaskStatus.VALIDATION_FAILED, details=validation_details),
    ]
    mock_persist.assert_has_awaits(expected_persist_calls, any_order=False)

    # Ensure completion path wasn't called
    mock_agent.publish_task_completed.assert_not_called()
    # Optionally check if a specific validation failure event was published if applicable
    # mock_agent.publish_validation_failed.assert_awaited_once_with(task, validation_details) # If called directly by _process_single_task
