"""
Tests for the Dream.OS Task Manager implementation.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import time
from dreamos import TaskManager

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

def test_task_manager_initialization(temp_dir):
    """Test task manager initialization."""
    manager = TaskManager(state_dir=temp_dir)
    
    assert manager.state_dir == temp_dir
    assert len(manager.tasks) == 0
    assert len(manager.completed_tasks) == 0

def test_add_task(temp_dir):
    """Test adding tasks."""
    manager = TaskManager(state_dir=temp_dir)
    
    # Add a task
    task_id = manager.add_task(
        task_type="test_task",
        parameters={"test": "value"},
        priority=1
    )
    
    assert task_id in manager.tasks
    task = manager.tasks[task_id]
    assert task["type"] == "test_task"
    assert task["parameters"] == {"test": "value"}
    assert task["priority"] == 1
    assert task["status"] == "pending"

def test_get_next_task(temp_dir):
    """Test getting next task."""
    manager = TaskManager(state_dir=temp_dir)
    
    # Add tasks with different priorities
    task1_id = manager.add_task(
        task_type="test_task",
        parameters={"test": "value1"},
        priority=2
    )
    
    task2_id = manager.add_task(
        task_type="test_task",
        parameters={"test": "value2"},
        priority=1
    )
    
    # Get next task (should be task2 due to higher priority)
    task = manager.get_next_task()
    assert task["id"] == task2_id
    assert task["parameters"] == {"test": "value2"}

def test_task_dependencies(temp_dir):
    """Test task dependencies."""
    manager = TaskManager(state_dir=temp_dir)
    
    # Add a task
    task1_id = manager.add_task(
        task_type="test_task",
        parameters={"test": "value1"}
    )
    
    # Add a dependent task
    task2_id = manager.add_task(
        task_type="test_task",
        parameters={"test": "value2"},
        dependencies=[task1_id]
    )
    
    # Get next task (should be task1)
    task = manager.get_next_task()
    assert task["id"] == task1_id
    
    # Complete task1
    manager.update_task_status(task1_id, "completed")
    
    # Now task2 should be available
    task = manager.get_next_task()
    assert task["id"] == task2_id

def test_task_status_update(temp_dir):
    """Test updating task status."""
    manager = TaskManager(state_dir=temp_dir)
    
    # Add a task
    task_id = manager.add_task(
        task_type="test_task",
        parameters={"test": "value"}
    )
    
    # Update status
    manager.update_task_status(
        task_id,
        "completed",
        result={"result": "success"}
    )
    
    # Check task moved to completed
    assert task_id not in manager.tasks
    assert task_id in manager.completed_tasks
    
    completed_task = manager.completed_tasks[task_id]
    assert completed_task["status"] == "completed"
    assert completed_task["result"] == {"result": "success"}

def test_state_persistence(temp_dir):
    """Test state persistence."""
    manager = TaskManager(state_dir=temp_dir)
    
    # Add and complete a task
    task_id = manager.add_task(
        task_type="test_task",
        parameters={"test": "value"}
    )
    manager.update_task_status(task_id, "completed")
    
    # Create new manager instance
    new_manager = TaskManager(state_dir=temp_dir)
    
    # Check state loaded
    assert task_id in new_manager.completed_tasks
    assert new_manager.completed_tasks[task_id]["status"] == "completed" 