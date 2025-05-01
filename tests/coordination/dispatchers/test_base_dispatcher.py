"""Tests for the base dispatcher functionality."""

import time
from queue import PriorityQueue
from typing import Any, Dict

import pytest
from pytest_mock import MockerFixture

from dreamos.coordination.dispatchers.dispatchers.base_dispatcher import BaseDispatcher


class MockDispatcher(BaseDispatcher):
    """Mock dispatcher for testing."""

    def __init__(self):
        super().__init__()
        self.executed_tasks = []

    def execute_task(self, task: Dict[str, Any], priority: int = 0) -> Dict[str, Any]:
        """Record task and return success, potentially raise error."""
        if task.get("payload", {}).get("force_error", False):
            raise ValueError("Forced execution error")
        self.executed_tasks.append(task)
        return {"success": True, "data": task}


def test_base_dispatcher_initialization():
    """Test dispatcher initialization."""
    dispatcher = MockDispatcher()
    assert not dispatcher.is_running
    assert dispatcher.current_task is None
    assert dispatcher.task_queue.empty()


def test_add_task():
    """Test adding tasks to the queue."""
    dispatcher = MockDispatcher()
    task = {"id": "test-1", "type": "test", "payload": {}}

    dispatcher.add_task(task)
    assert not dispatcher.task_queue.empty()
    assert dispatcher.task_queue.qsize() == 1


def test_add_task_with_priority():
    """Test adding tasks with different priorities."""
    dispatcher = MockDispatcher()
    task_low = {"id": "low-1", "type": "test", "payload": {}, "priority": 10}
    task_high = {"id": "high-1", "type": "test", "payload": {}, "priority": 1}
    task_mid = {"id": "mid-1", "type": "test", "payload": {}, "priority": 5}

    dispatcher.add_task(task_low)
    dispatcher.add_task(task_high)
    dispatcher.add_task(task_mid)

    assert dispatcher.task_queue.qsize() == 3

    dispatcher.run_dispatcher_loop()
    assert dispatcher.executed_tasks[0]["id"] == "high-1"

    pytest.skip("Implementation pending: Adapt based on actual queue and loop behavior")


def test_run_dispatcher_loop():
    """Test the dispatcher loop processes tasks."""
    dispatcher = MockDispatcher()
    tasks = [
        {"id": "test-1", "type": "test", "payload": {"value": 1}},
        {"id": "test-2", "type": "test", "payload": {"value": 2}},
    ]

    # Add tasks to queue
    for task in tasks:
        dispatcher.add_task(task)

    # Start loop and let it process one iteration
    dispatcher.run_dispatcher_loop()

    # Verify tasks were executed
    assert len(dispatcher.executed_tasks) > 0
    assert dispatcher.executed_tasks[0]["id"] == "test-1"


def test_run_dispatcher_loop_priority():
    """Test the dispatcher loop processes tasks in priority order."""
    dispatcher = MockDispatcher()
    tasks = [
        {"id": "task-low", "type": "test", "payload": {}, "priority": 10},
        {"id": "task-high", "type": "test", "payload": {}, "priority": 1},
        {"id": "task-mid", "type": "test", "payload": {}, "priority": 5},
    ]
    for task in tasks:
        dispatcher.add_task(task)

    dispatcher.run_dispatcher_loop()
    dispatcher.run_dispatcher_loop()
    dispatcher.run_dispatcher_loop()

    assert len(dispatcher.executed_tasks) == 3
    assert dispatcher.executed_tasks[0]["id"] == "task-high"
    assert dispatcher.executed_tasks[1]["id"] == "task-mid"
    assert dispatcher.executed_tasks[2]["id"] == "task-low"

    pytest.skip("Implementation pending: Adapt based on loop execution model")


def test_run_dispatcher_handles_execution_error():
    """Test that the loop continues if execute_task raises an error."""
    dispatcher = MockDispatcher()
    task_error = {
        "id": "error-1",
        "type": "error",
        "payload": {"force_error": True},
        "priority": 1,
    }
    task_ok = {"id": "ok-1", "type": "test", "payload": {}, "priority": 5}

    dispatcher.add_task(task_error)
    dispatcher.add_task(task_ok)

    dispatcher.run_dispatcher_loop()
    dispatcher.run_dispatcher_loop()

    assert len(dispatcher.executed_tasks) == 1
    assert dispatcher.executed_tasks[0]["id"] == "ok-1"

    pytest.skip("Implementation pending: Adapt based on loop/error handling")


def test_stop_dispatcher():
    """Test stopping the dispatcher loop."""
    dispatcher = MockDispatcher()
    dispatcher.run_dispatcher_loop()  # Start loop
    assert dispatcher.is_running

    dispatcher.stop()  # Stop loop
    assert not dispatcher.is_running


def test_get_status():
    """Test getting dispatcher status."""
    dispatcher = MockDispatcher()
    task = {"id": "test-1", "type": "test", "payload": {}}

    # Check initial status
    status = dispatcher.get_status()
    assert not status["is_running"]
    assert status["queue_size"] == 0
    assert status["current_task"] is None

    # Add task and check status
    dispatcher.add_task(task)
    status = dispatcher.get_status()
    assert status["queue_size"] == 1

    # Start processing and check status
    dispatcher.run_dispatcher_loop()
    status = dispatcher.get_status()
    assert status["is_running"]
