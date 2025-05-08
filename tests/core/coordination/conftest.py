import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dreamos.core.coordination.base_agent import (
    BaseAgent,
    TaskMessage,
    TaskPriority,
    TaskStatus,
)
# NOTE: Import ProjectBoardManager if it's used as a spec for mocks within fixtures in this file.
# from dreamos.core.pbm.project_board_manager import ProjectBoardManager


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


# --- Mock Concrete Agent for specific tests ---
class MockConcreteAgent(BaseAgent):
    async def _on_start(self):
        pass

    async def _on_stop(self):
        pass

    # Need a default handler for tests using mock_agent
    async def handle_default_test_command(self, task: TaskMessage) -> dict:
        return {"result": "mock success", "summary": "Mock handler ran"}


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
        # Add a handler for EXCEPTION_COMMAND if it's commonly tested with test_agent
        # async def error_handler(task): raise ValueError("Handler crashed!")
        # agent.register_command_handler("EXCEPTION_COMMAND", error_handler)
        return agent


# Helper function to create tasks for testing
def create_sample_task(
    task_id="test-task-123",
    command_type="TEST_CMD",
    params=None,
    status=TaskStatus.ACCEPTED,
    priority=TaskPriority.MEDIUM, # Added default priority
):
    return TaskMessage(
        task_id=task_id,
        task_type=command_type,
        command_type=command_type,  # Ensure command_type is set too
        params=params or {},
        status=status,
        priority=priority,
    )


# Fixture to provide a BaseAgent instance with more mocked dependencies for specific scenarios
@pytest.fixture
def mock_agent(mock_agent_bus: MagicMock, tmp_path: Path):
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
        patch.object(BaseAgent, "publish_validation_failed", new_callable=AsyncMock), # Assuming this event helper exists
        patch.object(BaseAgent, "publish_agent_error", new_callable=AsyncMock),
    ):
        agent = MockConcreteAgent(
            agent_id=agent_id,
            agent_bus=mock_agent_bus,
            task_list_path=tmp_path / "tasks.json",
        )
        agent.register_command_handler(
            "test_command", agent.handle_default_test_command
        )
        agent.persist_task_update = mock_persist  # Attach mock for easy access in tests
        yield agent 