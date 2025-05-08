import asyncio
import logging # Required if ConcreteAgent from conftest logs through self.logger
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dreamos.core.coordination.base_agent import BaseAgent # For MinimalAgent

# Fixtures like test_agent, mock_agent_bus are automatically discovered from conftest.py


def test_base_agent_init(
    test_agent, mock_agent_bus, tmp_path # test_agent is ConcreteAgent instance
): # Removed type hints to avoid importing ConcreteAgent here
    """Test basic initialization of the BaseAgent."""
    assert test_agent.agent_id == "test_agent_001"
    assert test_agent.agent_bus == mock_agent_bus
    assert test_agent.task_list_path == tmp_path / "tasks.json"
    assert isinstance(test_agent.logger, logging.Logger)
    assert test_agent._running is False
    assert "EXAMPLE_COMMAND" in test_agent._command_handlers


@pytest.mark.asyncio
async def test_base_agent_start(test_agent, mock_agent_bus):
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
async def test_base_agent_stop(test_agent, mock_agent_bus):
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


# Minimal agent for specific unsubscription test
class MinimalAgent(BaseAgent):
    async def _on_start(self):
        pass

    async def _on_stop(self):
        pass


@pytest.mark.asyncio
async def test_base_agent_stop_unsubscribes(mock_agent_bus, tmp_path):
    """Verify specifically that BaseAgent.stop calls agent_bus.unsubscribe."""
    agent = MinimalAgent(
        agent_id="stop_test_agent",
        agent_bus=mock_agent_bus,
        task_list_path=tmp_path / "tasks.json",
    )

    # Simulate the state after start() has run
    agent._running = True
    command_topic = f"dreamos.agent.{agent.agent_id}.task.command"
    # Get the actual handler reference; assume _handle_command exists and is suitable
    # If _handle_command relies on things not in MinimalAgent, this might need adjustment
    # or _handle_command needs to be mocked/simplified for MinimalAgent.
    # For this test, we primarily care that unsubscribe is called with *a* handler.
    command_handler = agent._handle_command
    agent._command_topic = command_topic
    agent._command_handler_ref = command_handler
    # Mock the task processor task object as it's needed in stop()
    agent._task_processor_task = AsyncMock(spec=asyncio.Task)
    agent._task_processor_task.cancel = MagicMock() # Ensure cancel can be called

    # Call stop
    await agent.stop()

    # Assert unsubscribe was called correctly
    mock_agent_bus.unsubscribe.assert_awaited_once_with(command_topic, command_handler) 