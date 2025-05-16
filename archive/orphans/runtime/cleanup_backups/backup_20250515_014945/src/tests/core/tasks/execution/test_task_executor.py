"""
Tests for the TaskExecutor class.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dreamos.core.tasks.execution.task_executor import TaskExecutor
from dreamos.core.tasks.nexus.task_nexus import Task, TaskNexus


@pytest.fixture
def mock_task_nexus():
    """Create a mock TaskNexus instance."""
    mock = MagicMock(spec=TaskNexus)
    return mock


@pytest.fixture
def task_executor(mock_task_nexus):
    """Create a TaskExecutor instance with a mock TaskNexus."""
    return TaskExecutor(mock_task_nexus)


class TestTaskExecutor:
    """Tests for the TaskExecutor class."""

    def test_init(self, task_executor, mock_task_nexus):
        """Test that TaskExecutor initializes correctly."""
        assert task_executor.task_nexus == mock_task_nexus
        assert isinstance(task_executor.execution_history, dict)
        assert len(task_executor.execution_history) == 0

    @pytest.mark.asyncio
    async def test_execute_task_not_found(self, task_executor, mock_task_nexus):
        """Test execute_task when the task is not found."""
        # Configure the mock to return None (task not found)
        mock_task_nexus.get_task_by_id.return_value = None

        # Execute the task
        result = await task_executor.execute_task("nonexistent_task", "agent_1")

        # Verify the result
        assert result is False
        mock_task_nexus.get_task_by_id.assert_called_once_with("nonexistent_task")
        mock_task_nexus.update_task_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_task_success(self, task_executor, mock_task_nexus):
        """Test execute_task when the task is executed successfully."""
        # Create a mock task
        mock_task = MagicMock(spec=Task)
        mock_task.task_id = "test_task_1"
        mock_task.tags = ["test_type"]

        # Configure the mock to return the task
        mock_task_nexus.get_task_by_id.return_value = mock_task

        # Patch the _execute_task_by_type method to return a success result
        with patch.object(
            task_executor,
            "_execute_task_by_type",
            new_callable=AsyncMock,
            return_value={"success": True, "result": {"data": "test_result"}},
        ):
            # Execute the task
            result = await task_executor.execute_task("test_task_1", "agent_1")

            # Verify the result
            assert result is True
            mock_task_nexus.get_task_by_id.assert_called_once_with("test_task_1")
            mock_task_nexus.update_task_status.assert_called_with(
                "test_task_1", "completed", {"data": "test_result"}
            )

            # Verify that the execution history was updated
            assert "test_task_1" in task_executor.execution_history
            assert len(task_executor.execution_history["test_task_1"]) == 1
            assert task_executor.execution_history["test_task_1"][0]["agent_id"] == "agent_1"
            assert task_executor.execution_history["test_task_1"][0]["attempt_number"] == 1

    @pytest.mark.asyncio
    async def test_execute_task_failure(self, task_executor, mock_task_nexus):
        """Test execute_task when the task execution fails."""
        # Create a mock task
        mock_task = MagicMock(spec=Task)
        mock_task.task_id = "test_task_2"
        mock_task.tags = ["test_type"]

        # Configure the mock to return the task
        mock_task_nexus.get_task_by_id.return_value = mock_task

        # Patch the _execute_task_by_type method to return a failure result
        with patch.object(
            task_executor,
            "_execute_task_by_type",
            new_callable=AsyncMock,
            return_value={"success": False, "error": "test_error"},
        ):
            # Execute the task
            result = await task_executor.execute_task("test_task_2", "agent_1")

            # Verify the result
            assert result is False
            mock_task_nexus.get_task_by_id.assert_called_once_with("test_task_2")
            mock_task_nexus.update_task_status.assert_called_with(
                "test_task_2", "failed", "test_error"
            )

    @pytest.mark.asyncio
    async def test_execute_task_exception(self, task_executor, mock_task_nexus):
        """Test execute_task when an exception occurs during execution."""
        # Create a mock task
        mock_task = MagicMock(spec=Task)
        mock_task.task_id = "test_task_3"
        mock_task.tags = ["test_type"]

        # Configure the mock to return the task
        mock_task_nexus.get_task_by_id.return_value = mock_task

        # Patch the _execute_task_by_type method to raise an exception
        with patch.object(
            task_executor,
            "_execute_task_by_type",
            new_callable=AsyncMock,
            side_effect=Exception("test_exception"),
        ):
            # Execute the task
            result = await task_executor.execute_task("test_task_3", "agent_1")

            # Verify the result
            assert result is False
            mock_task_nexus.get_task_by_id.assert_called_once_with("test_task_3")
            mock_task_nexus.update_task_status.assert_called_with(
                "test_task_3", "failed", {"error": "test_exception"}
            )

    @pytest.mark.asyncio
    async def test_execute_task_by_type(self, task_executor):
        """Test _execute_task_by_type method."""
        # Create a mock task
        mock_task = MagicMock(spec=Task)
        mock_task.task_id = "test_task_4"
        mock_task.tags = ["test_type"]

        # Execute the task by type
        result = await task_executor._execute_task_by_type(mock_task)

        # Verify the result
        assert result["success"] is True
        assert "result" in result
        assert "execution_id" in result["result"]
        assert "timestamp" in result["result"]
        assert "details" in result["result"]
        assert "test_type" in result["result"]["details"]

    def test_get_execution_history(self, task_executor):
        """Test get_execution_history method."""
        # Add some execution history
        task_executor.execution_history = {
            "test_task_5": [
                {
                    "timestamp": "2023-01-01T00:00:00+00:00",
                    "agent_id": "agent_1",
                    "attempt_number": 1,
                }
            ]
        }

        # Get the execution history
        history = task_executor.get_execution_history("test_task_5")

        # Verify the result
        assert len(history) == 1
        assert history[0]["agent_id"] == "agent_1"
        assert history[0]["attempt_number"] == 1

        # Test getting history for a non-existent task
        assert task_executor.get_execution_history("nonexistent_task") == []

    def test_clear_execution_history_specific_task(self, task_executor):
        """Test clear_execution_history method for a specific task."""
        # Add some execution history
        task_executor.execution_history = {
            "test_task_6": [
                {
                    "timestamp": "2023-01-01T00:00:00+00:00",
                    "agent_id": "agent_1",
                    "attempt_number": 1,
                }
            ],
            "test_task_7": [
                {
                    "timestamp": "2023-01-01T00:00:00+00:00",
                    "agent_id": "agent_1",
                    "attempt_number": 1,
                }
            ],
        }

        # Clear the execution history for a specific task
        task_executor.clear_execution_history("test_task_6")

        # Verify the result
        assert "test_task_6" not in task_executor.execution_history
        assert "test_task_7" in task_executor.execution_history

    def test_clear_execution_history_all(self, task_executor):
        """Test clear_execution_history method for all tasks."""
        # Add some execution history
        task_executor.execution_history = {
            "test_task_8": [
                {
                    "timestamp": "2023-01-01T00:00:00+00:00",
                    "agent_id": "agent_1",
                    "attempt_number": 1,
                }
            ],
            "test_task_9": [
                {
                    "timestamp": "2023-01-01T00:00:00+00:00",
                    "agent_id": "agent_1",
                    "attempt_number": 1,
                }
            ],
        }

        # Clear all execution history
        task_executor.clear_execution_history()

        # Verify the result
        assert len(task_executor.execution_history) == 0 