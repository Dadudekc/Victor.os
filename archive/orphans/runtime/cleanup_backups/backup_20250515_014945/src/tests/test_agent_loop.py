"""
Tests for the DreamOS Agent Loop implementation.
"""

import asyncio
from datetime import datetime
from unittest.mock import ANY, AsyncMock, Mock

import pytest

from dreamos.agents.loop.agent_loop import AgentLoop
from dreamos.automation.validation_utils import ValidationResult, ValidationStatus
from dreamos.core.config import AppConfig
from dreamos.core.coordination.base_agent import BaseAgent
from dreamos.core.project_board import ProjectBoardManager


class MockAgent(BaseAgent):
    """Mock agent for testing."""
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._active_tasks = {}
        self.logger = Mock()

    async def execute_task(self, task):
        return task.get("result", {})

@pytest.fixture
def mock_config():
    """Create a mock config."""
    config = Mock(spec=AppConfig)
    config.agent_loop_interval = 0.1
    return config

@pytest.fixture
def mock_pbm():
    """Create a mock project board manager."""
    pbm = Mock(spec=ProjectBoardManager)
    pbm.update_task_status = AsyncMock()
    return pbm

@pytest.fixture
def mock_agent_bus():
    """Create a mock agent bus."""
    bus = Mock()
    bus.publish = AsyncMock()
    return bus

@pytest.fixture
def agent_loop(mock_config, mock_pbm, mock_agent_bus):
    """Create an agent loop instance for testing."""
    agent = MockAgent("test_agent")
    return AgentLoop(
        agent=agent,
        config=mock_config,
        pbm=mock_pbm,
        agent_bus=mock_agent_bus
    )

@pytest.mark.asyncio
async def test_initialization(agent_loop):
    """Test agent loop initialization."""
    assert agent_loop.agent.agent_id == "test_agent"
    assert agent_loop.cycle_count == 0
    assert not agent_loop._running

@pytest.mark.asyncio
async def test_run_cycle(agent_loop):
    """Test running a single cycle."""
    # Add a task
    task_id = "test_task_001"
    agent_loop.agent._active_tasks[task_id] = {
        "status": "in_progress",
        "result": {
            "tests": [{"name": "test1", "status": "passed"}],
            "documentation": {"description": "test doc"},
            "implementation": {"code": "test code"},
            "demonstration": {"evidence": "test evidence"}
        }
    }

    # Run cycle
    await agent_loop.run_cycle()

    # Verify cycle count increased
    assert agent_loop.cycle_count == 1

@pytest.mark.asyncio
async def test_validate_completed_task(agent_loop):
    """Test validation of a completed task."""
    # Add a completed task
    task_id = "test_task_002"
    agent_loop.agent._active_tasks[task_id] = {
        "status": "completed",
        "result": {
            "tests": [{"name": "test1", "status": "passed"}],
            "documentation": {"description": "test doc"},
            "implementation": {"code": "test code"},
            "demonstration": {"evidence": "test evidence"}
        }
    }

    # Run validation
    await agent_loop._validate_completed_tasks()

    # Verify task was validated
    assert "validation" in agent_loop.agent._active_tasks[task_id]

@pytest.mark.asyncio
async def test_validation_failure(agent_loop):
    """Test handling of validation failure."""
    # Add a completed task with missing validation data
    task_id = "test_task_003"
    agent_loop.agent._active_tasks[task_id] = {
        "status": "completed",
        "result": {
            "tests": [],  # Missing tests
            "documentation": {},  # Missing documentation
            "implementation": {},  # Missing implementation
            "demonstration": {}  # Missing demonstration
        }
    }

    # Run validation
    await agent_loop._validate_completed_tasks()

    # Verify task was marked as validation failed
    assert agent_loop.agent._active_tasks[task_id]["status"] == "validation_failed"
    assert "validation" in agent_loop.agent._active_tasks[task_id]

    # Verify violation was logged
    agent_loop.agent_bus.publish.assert_called_with(
        "agent.validation.violation",
        {
            "agent_id": "test_agent",
            "task_id": task_id,
            "timestamp": ANY,
            "validation_result": agent_loop.agent._active_tasks[task_id]["validation"]["details"]
        }
    )

@pytest.mark.asyncio
async def test_escalation_to_thea(agent_loop):
    """Test escalation to THEA after repeated validation failures."""
    # Add a task with validation history
    task_id = "test_task_004"
    agent_loop.agent._active_tasks[task_id] = {
        "status": "completed",
        "validation_history": [
            {"timestamp": datetime.utcnow().isoformat(), "status": "failed"},
            {"timestamp": datetime.utcnow().isoformat(), "status": "failed"}
        ],
        "result": {
            "tests": [],
            "documentation": {},
            "implementation": {},
            "demonstration": {}
        }
    }

    # Run validation
    await agent_loop._validate_completed_tasks()

    # Verify escalation to THEA
    agent_loop.agent_bus.publish.assert_called_with(
        "thea.validation.escalation",
        {
            "agent_id": "test_agent",
            "task_id": task_id,
            "timestamp": ANY,
            "validation_result": agent_loop.agent._active_tasks[task_id]["validation"]["details"],
            "validation_history": agent_loop.agent._active_tasks[task_id]["validation_history"]
        }
    )

@pytest.mark.asyncio
async def test_error_handling(agent_loop):
    """Test error handling in the agent loop."""
    # Add a task that will raise an error
    task_id = "test_task_005"
    agent_loop.agent._active_tasks[task_id] = {
        "status": "in_progress",
        "result": None
    }

    # Mock execute_task to raise an error
    agent_loop.agent.execute_task = AsyncMock(side_effect=Exception("Test error"))

    # Run cycle
    await agent_loop.run_cycle()

    # Verify error was handled
    assert agent_loop.agent._active_tasks[task_id]["status"] == "error"
    assert "error" in agent_loop.agent._active_tasks[task_id]

    # Verify error was logged
    agent_loop.agent_bus.publish.assert_called_with(
        "agent.error",
        {
            "agent_id": "test_agent",
            "error_type": "Exception",
            "error_message": "Test error",
            "timestamp": ANY
        }
    )

@pytest.mark.asyncio
async def test_start_stop(agent_loop):
    """Test starting and stopping the agent loop."""
    # Start the loop
    start_task = asyncio.create_task(agent_loop.start())
    
    # Let it run for a short time
    await asyncio.sleep(0.2)
    
    # Stop the loop
    await agent_loop.stop()
    
    # Wait for the loop to stop
    await start_task
    
    # Verify the loop stopped
    assert not agent_loop._running 