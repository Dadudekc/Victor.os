import asyncio
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

import pytest
from dreamos.coordination.agent_bus import BaseEvent, EventType
from dreamos.core.coordination.base_agent import (
    TaskMessage,
    TaskPriority,
    TaskStatus,
)

# Attempt to import ProjectBoardManager for spec, will pass if not available in this context
# but tests using it as a spec might require it in the actual test environment.
try:
    from dreamos.core.pbm.project_board_manager import ProjectBoardManager
except ImportError:
    ProjectBoardManager = MagicMock() # Fallback if not found, tests might need adjustment


# Fixtures like test_agent, mock_agent, mock_agent_bus, create_sample_task
# are automatically discovered from conftest.py


@pytest.mark.asyncio
async def test_base_agent_register_command_handler(test_agent): # test_agent is ConcreteAgent
    """Test registering a command handler."""

    async def dummy_handler(task):
        pass

    test_agent.register_command_handler("DUMMY_CMD", dummy_handler)
    assert "DUMMY_CMD" in test_agent._command_handlers
    assert test_agent._command_handlers["DUMMY_CMD"] == dummy_handler


# --- Tests for Internal Methods (_handle_command, _process_task_queue, etc.) ---

@pytest.mark.asyncio
async def test_handle_command_valid(test_agent, mock_agent_bus):
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
async def test_handle_command_invalid_data(test_agent, mock_agent_bus):
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
        ) as mock_queue_put, # Should not be called
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
async def test_handle_command_unknown_type(test_agent, mock_agent_bus):
    """Test _handle_command with an unknown task type."""
    task_data = {
        "task_id": "cmd-task-002",
        "task_type": "UNKNOWN_COMMAND",
        "params": {},
        "correlation_id": "corr-789", # Add correlation_id for consistency
    }
    event = BaseEvent(EventType.TASK_COMMAND, "sender_agent", task_data, task_data["correlation_id"])

    with (
        patch.object(
            test_agent, "publish_task_failed", new_callable=AsyncMock
        ) as mock_publish_failed,
        patch.object(
            test_agent._task_queue, "put", new_callable=AsyncMock
        ) as mock_queue_put, # Should not be called
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


# --- Tests for _validate_task_completion (using mock_agent fixture) ---

@pytest.mark.asyncio
async def test_validate_task_completion_success_with_summary(mock_agent, create_sample_task):
    """Verify base validation passes with a valid result dict including summary."""
    task = create_sample_task()
    result = {"output": "data", "summary": "All good"}

    # Assuming _validate_task_completion is part of mock_agent (BaseAgent)
    passed, details = await mock_agent._validate_task_completion(task, result, []) # Added required_keys

    assert passed is True
    assert "Basic validation checks passed" in details
    mock_agent.publish_validation_failed.assert_not_called()


@pytest.mark.asyncio
async def test_validate_task_completion_success_without_summary(mock_agent, create_sample_task):
    """Verify base validation passes (with warning) if result lacks summary."""
    task = create_sample_task()
    result = {"output": "data only"}  # No summary

    passed, details = await mock_agent._validate_task_completion(task, result, []) # Added required_keys

    assert passed is True  # Currently only warns, doesn't fail for summary
    assert "Handler result lacks a 'summary' key" in details
    mock_agent.publish_validation_failed.assert_not_called()


@pytest.mark.asyncio
async def test_validate_task_completion_fail_empty_result(mock_agent, create_sample_task):
    """Verify base validation fails if the result dict is empty."""
    task = create_sample_task()
    result = {}  # Empty result

    passed, details = await mock_agent._validate_task_completion(task, result, []) # Added required_keys

    assert passed is False
    assert "Handler result dictionary is missing, None, or empty" in details
    mock_agent.publish_validation_failed.assert_awaited_once()
    call_args = mock_agent.publish_validation_failed.await_args[0]
    assert task == call_args[0]
    assert "Handler result dictionary is missing, None, or empty" in call_args[1]


@pytest.mark.asyncio
async def test_validate_task_completion_fail_none_result(mock_agent, create_sample_task):
    """Verify base validation fails if the result is None."""
    task = create_sample_task()
    result = None  # None result

    passed, details = await mock_agent._validate_task_completion(task, result, []) # Added required_keys

    assert passed is False
    assert "Handler result dictionary is missing, None, or empty" in details
    mock_agent.publish_validation_failed.assert_awaited_once()
    call_args = mock_agent.publish_validation_failed.await_args[0]
    assert task == call_args[0]
    assert "Handler result dictionary is missing, None, or empty" in call_args[1]


# --- Tests for _process_single_task (using mock_agent for mocked persist/publish) ---

@pytest.mark.asyncio
async def test_process_single_task_success_with_validation_pass(mock_agent, create_sample_task):
    """Verify task processing completes and persists COMPLETED status when validation passes."""
    task = create_sample_task(command_type="test_command") # mock_agent has 'test_command' handler
    handler_result = {"output": "success", "summary": "Handler success summary"}
    mock_handler = AsyncMock(return_value=handler_result)
    # Override the default handler for this specific test if needed, or ensure mock_agent's default works
    mock_agent._command_handlers["test_command"] = mock_handler

    mock_agent._validate_task_completion = AsyncMock(
        return_value=(True, "Validation passed")
    )

    # mock_agent fixture already patches persist_task_update and publish_task_completed
    await mock_agent._process_single_task(task, task.correlation_id)

    mock_handler.assert_awaited_once_with(task)
    mock_agent._validate_task_completion.assert_awaited_once_with(task, handler_result, []) # Added required_keys
    mock_agent.publish_task_completed.assert_awaited_once_with(
        task, result=handler_result
    )

    expected_persist_calls = [
        call(task.task_id, TaskStatus.WORKING),
        call(
            task.task_id, TaskStatus.COMPLETED, result_summary="Handler success summary"
        ),
    ]
    # mock_agent.persist_task_update is the AsyncMock from the fixture patch
    mock_agent.persist_task_update.assert_has_awaits(expected_persist_calls, any_order=False)
    mock_agent.publish_validation_failed.assert_not_called()


@pytest.mark.asyncio
async def test_process_single_task_success_with_validation_fail(mock_agent, create_sample_task):
    """Verify task processing persists VALIDATION_FAILED status when validation fails."""
    task = create_sample_task(command_type="test_command")
    handler_result = {"output": "some data", "summary": "Handler ran"}
    validation_details = "Output format incorrect."
    mock_handler = AsyncMock(return_value=handler_result)
    mock_agent._command_handlers["test_command"] = mock_handler

    mock_agent._validate_task_completion = AsyncMock(
        return_value=(False, validation_details)
    )

    await mock_agent._process_single_task(task, task.correlation_id)

    mock_handler.assert_awaited_once_with(task)
    mock_agent._validate_task_completion.assert_awaited_once_with(task, handler_result, []) # Added required_keys

    expected_persist_calls = [
        call(task.task_id, TaskStatus.WORKING),
        call(task.task_id, TaskStatus.VALIDATION_FAILED, details=validation_details),
    ]
    mock_agent.persist_task_update.assert_has_awaits(expected_persist_calls, any_order=False)
    mock_agent.publish_task_completed.assert_not_called()
    # Check if publish_validation_failed (mocked in mock_agent) was called by _validate_task_completion
    # This depends on whether _validate_task_completion calls it directly or if _process_single_task does.
    # Based on original structure, _validate_task_completion calls it, which is already mocked.
    # If _process_single_task calls it based on validation result: mock_agent.publish_validation_failed.assert_awaited_once_with(task, validation_details)


# --- Tests for _process_task_queue (using test_agent as it's more complete) ---

@pytest.mark.asyncio
async def test_process_task_queue_processes_task(test_agent, mock_agent_bus, create_sample_task):
    """Test that _process_task_queue gets a task and calls _process_single_task."""
    test_agent._running = True # Simulate agent running
    sample_task = create_sample_task(command_type="EXAMPLE_COMMAND") # test_agent has this handler
    await test_agent._task_queue.put((test_agent._get_priority_value(sample_task.priority), sample_task))

    with patch.object(
        test_agent, "_process_single_task", new_callable=AsyncMock
    ) as mock_process_single:
        process_queue_task = asyncio.create_task(test_agent._process_task_queue())
        await asyncio.sleep(0.05) # Give time for one task processing cycle

        mock_process_single.assert_awaited_once()
        called_task = mock_process_single.await_args[0][0]
        assert called_task.task_id == sample_task.task_id

        test_agent._running = False # Stop the loop
        process_queue_task.cancel()
        try:
            await process_queue_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_process_task_queue_handles_skip_duplicate(test_agent, mock_agent_bus, create_sample_task):
    """Test that _process_task_queue skips duplicate active tasks."""
    test_agent._running = True
    sample_task = create_sample_task(task_id="task-q-dup", command_type="EXAMPLE_COMMAND")
    # Mark task as already active
    # Ensure the dummy active task can be awaited and cancelled gracefully
    dummy_active_task = asyncio.create_task(asyncio.sleep(0.1))
    test_agent._active_tasks[sample_task.task_id] = dummy_active_task

    await test_agent._task_queue.put((test_agent._get_priority_value(sample_task.priority), sample_task))

    with patch.object(
        test_agent, "_process_single_task", new_callable=AsyncMock
    ) as mock_process_single:
        process_queue_task = asyncio.create_task(test_agent._process_task_queue())
        await asyncio.sleep(0.05) # Allow queue processing

        mock_process_single.assert_not_awaited()
        assert test_agent._task_queue.empty() # Task should be consumed from queue

        # Cleanup
        test_agent._running = False
        if not dummy_active_task.done():
            dummy_active_task.cancel()
            try: await dummy_active_task
            except asyncio.CancelledError: pass
        if not process_queue_task.done():
            process_queue_task.cancel()
            try: await process_queue_task
            except asyncio.CancelledError: pass
        test_agent._active_tasks.pop(sample_task.task_id, None)


# --- More detailed _process_single_task tests using test_agent and ProjectBoardManager mock ---
# These were adapted from the original file, using test_agent fixture

@pytest.mark.asyncio
async def test_process_single_task_success(test_agent, mock_agent_bus, create_sample_task):
    """Test the happy path for _process_single_task using test_agent."""
    sample_task = create_sample_task(command_type="EXAMPLE_COMMAND") # Handler in ConcreteAgent
    correlation_id = sample_task.correlation_id

    # Mock PBM and validation for test_agent instance
    test_agent.pbm = AsyncMock(spec=ProjectBoardManager)
    mock_validate = AsyncMock(return_value=(True, "Validation passed."))
    test_agent._validate_task_completion = mock_validate

    # Patch the publish methods directly on the test_agent instance for this test
    with patch.object(test_agent, "publish_task_started", new_callable=AsyncMock) as mock_publish_started, \
         patch.object(test_agent, "publish_task_completed", new_callable=AsyncMock) as mock_publish_completed, \
         patch.object(test_agent, "publish_validation_failed", new_callable=AsyncMock) as mock_publish_validation_failed:

        await test_agent._process_single_task(sample_task, correlation_id)

        test_agent.pbm.update_working_task.assert_awaited_once_with(sample_task.task_id, {"status": TaskStatus.WORKING.value})
        test_agent.pbm.move_task_to_completed.assert_awaited_once()
        move_args = test_agent.pbm.move_task_to_completed.await_args[0]
        assert move_args[0] == sample_task.task_id
        assert move_args[1]["status"] == TaskStatus.COMPLETED.value
        # ConcreteAgent's EXAMPLE_COMMAND handler returns {"result": "success"}
        assert move_args[1]["result"] == {"result": "success"}

        mock_publish_started.assert_awaited_once_with(sample_task)
        mock_validate.assert_awaited_once_with(sample_task, {"result": "success"}, []) # Added required_keys
        mock_publish_completed.assert_awaited_once_with(sample_task, {"result": "success"})
        mock_publish_validation_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_single_task_no_handler(test_agent, mock_agent_bus, create_sample_task):
    """Test processing a task with no registered handler using test_agent."""
    sample_task = create_sample_task(command_type="UNKNOWN_COMMAND")
    correlation_id = sample_task.correlation_id
    test_agent.pbm = AsyncMock(spec=ProjectBoardManager)

    with (patch.object(test_agent, "publish_task_failed", new_callable=AsyncMock) as mock_publish_failed,
          patch.object(test_agent, "publish_task_started", new_callable=AsyncMock) as mock_publish_started):

        await test_agent._process_single_task(sample_task, correlation_id)

        test_agent.pbm.update_working_task.assert_awaited_once()
        update_args = test_agent.pbm.update_working_task.await_args[0]
        assert update_args[0] == sample_task.task_id
        assert update_args[1]["status"] == TaskStatus.FAILED.value
        assert "No handler registered" in update_args[1]["error_details"]

        mock_publish_started.assert_not_awaited() # Should not start if no handler
        mock_publish_failed.assert_awaited_once()
        fail_args = mock_publish_failed.await_args[0]
        assert fail_args[0] == sample_task
        assert "No handler registered" in fail_args[1]
        assert fail_args[2] is True  # is_final should be True


@pytest.mark.asyncio
async def test_process_single_task_handler_exception(test_agent, mock_agent_bus, create_sample_task):
    """Test processing when the command handler raises an exception using test_agent."""
    sample_task = create_sample_task(command_type="EXCEPTION_COMMAND")
    correlation_id = sample_task.correlation_id
    test_agent.pbm = AsyncMock(spec=ProjectBoardManager)

    # Register a handler that raises an error specifically for test_agent instance
    async def error_handler(task):
        raise ValueError("Handler crashed!")
    test_agent.register_command_handler("EXCEPTION_COMMAND", error_handler)

    with patch.object(test_agent, "publish_task_started", new_callable=AsyncMock) as mock_publish_started, \
         patch.object(test_agent, "publish_agent_error", new_callable=AsyncMock) as mock_publish_agent_error, \
         patch.object(test_agent, "publish_task_failed", new_callable=AsyncMock) as mock_publish_task_failed:

        await test_agent._process_single_task(sample_task, correlation_id)

        test_agent.pbm.update_working_task.assert_awaited_with(
            sample_task.task_id,
            {
                "status": TaskStatus.FAILED.value,
                "error_details": "Error processing task task-p-exc: Handler crashed!", # Adjusted task_id if create_sample_task changes it
                "traceback": ANY,
            },
        )

        mock_publish_started.assert_awaited_once_with(sample_task)
        mock_publish_agent_error.assert_awaited_once()
        
        # Correctly unpack and assert args and kwargs from the mock call
        # For a single call, await_args is a call object (call_obj).
        # call_obj.args is a tuple of positional arguments.
        # call_obj.kwargs is a dictionary of keyword arguments.
        call_obj = mock_publish_agent_error.await_args
        
        # Check positional arguments (e.g., error_message)
        assert "Error processing task" in call_obj.args[0]
        assert "Handler crashed!" in call_obj.args[0]
        
        # Check keyword arguments (e.g., task_id, exc_info)
        assert call_obj.kwargs["task_id"] == sample_task.task_id
        assert call_obj.kwargs["exc_info"] is True

        mock_publish_task_failed.assert_awaited_once() # Should also publish task failed


@pytest.mark.asyncio
async def test_process_single_task_validation_failure(test_agent, mock_agent_bus, create_sample_task):
    """Test processing when task validation fails using test_agent."""
    sample_task = create_sample_task(command_type="EXAMPLE_COMMAND") # Handler in ConcreteAgent
    correlation_id = sample_task.correlation_id
    test_agent.pbm = AsyncMock(spec=ProjectBoardManager)

    # Mock validation to return failure for the test_agent instance
    mock_validate = AsyncMock(return_value=(False, "Result is invalid"))
    test_agent._validate_task_completion = mock_validate

    with patch.object(test_agent, "publish_task_started", new_callable=AsyncMock) as mock_publish_started, \
         patch.object(test_agent, "publish_task_completed", new_callable=AsyncMock) as mock_publish_completed, \
         patch.object(test_agent, "publish_validation_failed", new_callable=AsyncMock) as mock_publish_validation_failed:

        await test_agent._process_single_task(sample_task, correlation_id)

        test_agent.pbm.update_working_task.assert_awaited_with(
            sample_task.task_id, {"status": TaskStatus.VALIDATION_FAILED.value, "validation_details": "Result is invalid"}
        )

        mock_publish_started.assert_awaited_once_with(sample_task)
        # ConcreteAgent's EXAMPLE_COMMAND handler returns {"result": "success"}
        mock_validate.assert_awaited_once_with(sample_task, {"result": "success"}, []) # Added required_keys
        mock_publish_validation_failed.assert_awaited_once_with(sample_task, "Result is invalid")
        mock_publish_completed.assert_not_awaited()
        test_agent.pbm.move_task_to_completed.assert_not_awaited() 