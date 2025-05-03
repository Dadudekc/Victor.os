from unittest.mock import MagicMock, patch

import pytest

# Assuming ProjectBoardManager is located here, adjust if necessary
from dreamos.core.coordination.project_board_manager import ProjectBoardManager

# Define test file path for mocking
TEST_BOARD_PATH = "runtime/agent_comms/project_boards/test_board.json"


@pytest.fixture
def mock_pbm():
    """Fixture to create a ProjectBoardManager instance with mocked file I/O."""
    with patch(
        'dreamos.core.coordination.project_board_manager.os.path.exists'
        ) as mock_exists, \
         patch(
            'dreamos.core.coordination.project_board_manager.open',
            new_callable=MagicMock
            ) as mock_open, \
         patch(
            'dreamos.core.coordination.project_board_manager.json.load'
            ) as mock_load, \
         patch(
            'dreamos.core.coordination.project_board_manager.json.dump'
            ) as mock_dump, \
         patch(
            'dreamos.core.coordination.project_board_manager.os.replace'
            ) as mock_replace, \
         patch(
            'dreamos.core.coordination.project_board_manager.FileLock'
            ) as MockFileLock:

        # Mock file lock context manager
        mock_lock_instance = MockFileLock.return_value
        mock_lock_instance.__enter__.return_value = mock_lock_instance
        mock_lock_instance.__exit__.return_value = None

        # Assume board exists and is empty initially for simplicity
        mock_exists.return_value = True
        mock_load.return_value = {'tasks': []}

        # Create PBM instance with a mock path
        pbm = ProjectBoardManager(board_file_path=TEST_BOARD_PATH)
        pbm._file_lock = MockFileLock(f"{TEST_BOARD_PATH}.lock")
        return pbm, mock_load, mock_dump, MockFileLock, mock_open, mock_replace


class TestProjectBoardManager:

    def test_initialization(self, mock_pbm):
        """Test basic PBM initialization."""
        pbm, _, _, _, _, _ = mock_pbm
        assert pbm.board_file_path == TEST_BOARD_PATH
        assert pbm._tasks == []  # Assuming initial load returns empty list

    def test_add_task_success(self, mock_pbm):
        """Test adding a valid task successfully."""
        pbm, mock_load, mock_dump, MockFileLock, mock_open, _ = mock_pbm
        mock_load.return_value = {'tasks': []}  # Ensure it starts empty

        new_task = {
            "task_id": "TEST-001",
            "name": "Test Task",
            "description": "A test task",
            "priority": "MEDIUM",
            "status": "PENDING",
            "assigned_agent": None,
            "dependencies": [],
            "notes": "",
            "created_at": "timestamp"
            # Add other required fields based on actual schema
        }

        pbm.add_task(new_task)

        # Verify the task was added internally
        assert len(pbm._tasks) == 1
        assert pbm._tasks[0]["task_id"] == "TEST-001"

        # Verify file lock was acquired and released
        MockFileLock.assert_called_with(f"{TEST_BOARD_PATH}.lock")
        mock_lock_instance = MockFileLock.return_value
        mock_lock_instance.__enter__.assert_called_once()
        mock_lock_instance.__exit__.assert_called_once()

        # Verify JSON dump was called with the updated task list
        mock_dump.assert_called_once()
        args, kwargs = mock_dump.call_args
        assert args[0] == {'tasks': [new_task]}
        assert 'indent' in kwargs  # Check formatting

    # TODO: Add tests for update_task_status, claim_future_task, complete_task
    # TODO: Add tests for list_tasks, get_task
    # TODO: Test error handling (TaskNotFound, ValidationError, Locking errors)
    # TODO: Test edge cases (empty board, duplicate IDs)
