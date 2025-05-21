"""
Tests for the Dream.OS Agent implementation.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from dreamos import Agent

class TestAgent(Agent):
    """Test agent implementation."""
    
    def _execute_task(self, task):
        """Execute a test task."""
        return {
            "status": "success",
            "result": task["parameters"]
        }

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

def test_agent_initialization(temp_dir):
    """Test agent initialization."""
    agent = TestAgent(
        name="test-agent",
        capabilities=["test_task"],
        state_dir=temp_dir
    )
    
    assert agent.name == "test-agent"
    assert "test_task" in agent.capabilities
    assert agent.state_dir == temp_dir
    assert agent.state["tasks_processed"] == 0
    assert agent.state["errors"] == 0

def test_task_processing(temp_dir):
    """Test task processing."""
    agent = TestAgent(
        name="test-agent",
        capabilities=["test_task"],
        state_dir=temp_dir
    )
    
    # Valid task
    task = {
        "id": "task-1",
        "type": "test_task",
        "parameters": {"test": "value"}
    }
    
    result = agent.process_task(task)
    assert result["status"] == "success"
    assert result["task_id"] == "task-1"
    assert result["result"] == {"test": "value"}
    assert agent.state["tasks_processed"] == 1
    assert agent.state["errors"] == 0
    
    # Invalid task type
    task = {
        "id": "task-2",
        "type": "invalid_task",
        "parameters": {}
    }
    
    result = agent.process_task(task)
    assert result["status"] == "error"
    assert agent.state["errors"] == 1

def test_state_persistence(temp_dir):
    """Test state persistence."""
    agent = TestAgent(
        name="test-agent",
        capabilities=["test_task"],
        state_dir=temp_dir
    )
    
    # Process a task
    task = {
        "id": "task-1",
        "type": "test_task",
        "parameters": {}
    }
    agent.process_task(task)
    
    # Save state
    agent.save_state()
    
    # Create new agent instance
    new_agent = TestAgent(
        name="test-agent",
        capabilities=["test_task"],
        state_dir=temp_dir
    )
    
    # Load state
    new_agent.load_state()
    
    assert new_agent.state["tasks_processed"] == 1
    assert new_agent.state["errors"] == 0 