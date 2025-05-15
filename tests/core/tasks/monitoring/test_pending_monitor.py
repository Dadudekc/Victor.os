"""
Tests for the PendingTaskMonitor class.
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from dreamos.core.tasks.monitoring.pending_monitor import PendingTaskMonitor
from dreamos.core.tasks.nexus.task_nexus import Task, TaskNexus


@pytest.fixture
def mock_task_nexus():
    """Create a mock TaskNexus instance."""
    mock = MagicMock(spec=TaskNexus)
    return mock


@pytest.fixture
def config():
    """Create a configuration dictionary for the PendingTaskMonitor."""
    return {
        "pending_timeout_seconds": 3600,  # 1 hour
        "escalation_strategy": "log_only",
    }


@pytest.fixture
def pending_task_monitor(mock_task_nexus, config):
    """Create a PendingTaskMonitor instance with a mock TaskNexus."""
    return PendingTaskMonitor(mock_task_nexus, config)


class TestPendingTaskMonitor:
    """Tests for the PendingTaskMonitor class."""

    def test_init(self, pending_task_monitor, mock_task_nexus, config):
        """Test that PendingTaskMonitor initializes correctly."""
        assert pending_task_monitor.task_nexus == mock_task_nexus
        assert pending_task_monitor.config == config
        assert isinstance(pending_task_monitor.last_check_time, datetime)

    @pytest.mark.asyncio
    async def test_check_pending_tasks_no_tasks(self, pending_task_monitor, mock_task_nexus):
        """Test check_pending_tasks when there are no pending tasks."""
        # Configure the mock to return an empty list
        mock_task_nexus.get_all_tasks.return_value = []

        # Check pending tasks
        await pending_task_monitor.check_pending_tasks()

        # Verify the result
        mock_task_nexus.get_all_tasks.assert_called_once_with(status="pending")
        # No tasks, so _handle_stalled_task should not be called

    @pytest.mark.asyncio
    async def test_check_pending_tasks_no_stalled_tasks(
        self, pending_task_monitor, mock_task_nexus
    ):
        """Test check_pending_tasks when there are pending tasks but none are stalled."""
        # Create a mock task that was created recently
        mock_task = MagicMock(spec=Task)
        mock_task.task_id = "test_task_1"
        mock_task.created_at = datetime.now(timezone.utc).isoformat()

        # Configure the mock to return the task
        mock_task_nexus.get_all_tasks.return_value = [mock_task]

        # Check pending tasks
        await pending_task_monitor.check_pending_tasks()

        # Verify the result
        mock_task_nexus.get_all_tasks.assert_called_once_with(status="pending")
        # Task is not stalled, so _handle_stalled_task should not be called

    @pytest.mark.asyncio
    async def test_check_pending_tasks_stalled_task(
        self, pending_task_monitor, mock_task_nexus
    ):
        """Test check_pending_tasks when there is a stalled task."""
        # Create a mock task that was created long ago
        mock_task = MagicMock(spec=Task)
        mock_task.task_id = "test_task_2"
        mock_task.created_at = (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).isoformat()  # 2 hours ago

        # Configure the mock to return the task
        mock_task_nexus.get_all_tasks.return_value = [mock_task]

        # Patch the _handle_stalled_task method
        with patch.object(
            pending_task_monitor, "_handle_stalled_task", new_callable=AsyncMock
        ) as mock_handle_stalled_task:
            # Check pending tasks
            await pending_task_monitor.check_pending_tasks()

            # Verify the result
            mock_task_nexus.get_all_tasks.assert_called_once_with(status="pending")
            mock_handle_stalled_task.assert_called_once_with(mock_task)

    @pytest.mark.asyncio
    async def test_check_pending_tasks_invalid_timestamp(
        self, pending_task_monitor, mock_task_nexus
    ):
        """Test check_pending_tasks when a task has an invalid timestamp."""
        # Create a mock task with an invalid timestamp
        mock_task = MagicMock(spec=Task)
        mock_task.task_id = "test_task_3"
        mock_task.created_at = "invalid_timestamp"

        # Configure the mock to return the task
        mock_task_nexus.get_all_tasks.return_value = [mock_task]

        # Check pending tasks
        await pending_task_monitor.check_pending_tasks()

        # Verify the result
        mock_task_nexus.get_all_tasks.assert_called_once_with(status="pending")
        # Invalid timestamp, so _handle_stalled_task should not be called

    @pytest.mark.asyncio
    async def test_handle_stalled_task_log_only(
        self, pending_task_monitor, mock_task_nexus
    ):
        """Test _handle_stalled_task with log_only strategy."""
        # Create a mock task
        mock_task = MagicMock(spec=Task)
        mock_task.task_id = "test_task_4"

        # Handle the stalled task
        await pending_task_monitor._handle_stalled_task(mock_task)

        # Verify the result
        # With log_only strategy, no methods should be called on task_nexus

    @pytest.mark.asyncio
    async def test_handle_stalled_task_mark_stalled(
        self, pending_task_monitor, mock_task_nexus
    ):
        """Test _handle_stalled_task with mark_stalled strategy."""
        # Set the escalation strategy
        pending_task_monitor.config["escalation_strategy"] = "mark_stalled"

        # Create a mock task
        mock_task = MagicMock(spec=Task)
        mock_task.task_id = "test_task_5"

        # Handle the stalled task
        await pending_task_monitor._handle_stalled_task(mock_task)

        # Verify the result
        mock_task_nexus.update_task_status.assert_called_once_with(
            "test_task_5", "stalled"
        )

    @pytest.mark.asyncio
    async def test_handle_stalled_task_reassign(
        self, pending_task_monitor, mock_task_nexus
    ):
        """Test _handle_stalled_task with reassign strategy."""
        # Set the escalation strategy
        pending_task_monitor.config["escalation_strategy"] = "reassign"

        # Create a mock task
        mock_task = MagicMock(spec=Task)
        mock_task.task_id = "test_task_6"

        # Handle the stalled task
        await pending_task_monitor._handle_stalled_task(mock_task)

        # Verify the result
        mock_task_nexus.update_task_status.assert_called_once_with(
            "test_task_6", "pending"
        )

    @pytest.mark.asyncio
    async def test_handle_stalled_task_escalate(
        self, pending_task_monitor, mock_task_nexus
    ):
        """Test _handle_stalled_task with escalate strategy."""
        # Set the escalation strategy
        pending_task_monitor.config["escalation_strategy"] = "escalate"

        # Create a mock task
        mock_task = MagicMock(spec=Task)
        mock_task.task_id = "test_task_7"

        # Handle the stalled task
        with patch("uuid.uuid4", return_value=MagicMock(hex="12345678")):
            await pending_task_monitor._handle_stalled_task(mock_task)

            # Verify the result
            mock_task_nexus.add_task.assert_called_once()
            task_dict = mock_task_nexus.add_task.call_args[0][0]
            assert task_dict["task_id"] == "escalation_test_task_7_12345678"
            assert "Investigate stalled task" in task_dict["description"]
            assert task_dict["priority"] == "high"
            assert "escalation" in task_dict["tags"]
            assert "stalled_task" in task_dict["tags"]
            assert task_dict["related_task_id"] == "test_task_7"

    @pytest.mark.asyncio
    async def test_handle_stalled_task_unknown_strategy(
        self, pending_task_monitor, mock_task_nexus
    ):
        """Test _handle_stalled_task with an unknown strategy."""
        # Set the escalation strategy
        pending_task_monitor.config["escalation_strategy"] = "unknown"

        # Create a mock task
        mock_task = MagicMock(spec=Task)
        mock_task.task_id = "test_task_8"

        # Handle the stalled task
        await pending_task_monitor._handle_stalled_task(mock_task)

        # Verify the result
        # With unknown strategy, no methods should be called on task_nexus

    @pytest.mark.asyncio
    async def test_handle_stalled_task_escalate_exception(
        self, pending_task_monitor, mock_task_nexus
    ):
        """Test _handle_stalled_task with escalate strategy when an exception occurs."""
        # Set the escalation strategy
        pending_task_monitor.config["escalation_strategy"] = "escalate"

        # Create a mock task
        mock_task = MagicMock(spec=Task)
        mock_task.task_id = "test_task_9"

        # Configure the mock to raise an exception
        mock_task_nexus.add_task.side_effect = Exception("test_exception")

        # Handle the stalled task
        await pending_task_monitor._handle_stalled_task(mock_task)

        # Verify the result
        mock_task_nexus.add_task.assert_called_once()
        # Exception is caught and logged, no further action 