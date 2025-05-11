from unittest.mock import MagicMock, patch

import pytest

# Assuming ProjectBoardManager is located here, adjust if necessary
from dreamos.core.coordination.project_board_manager import ProjectBoardManager

# Define test file path for mocking
TEST_BOARD_PATH = "runtime/agent_comms/project_boards/test_board.json"


@pytest.fixture
def mock_pbm():
    """Fixture to create a ProjectBoardManager instance with mocked file I/O."""
    with (
        patch(
            "dreamos.core.coordination.project_board_manager.os.path.exists"
        ) as mock_exists,
        patch(
            "dreamos.core.coordination.project_board_manager.open",
            new_callable=MagicMock,
        ) as mock_open,
        patch("dreamos.core.coordination.project_board_manager.json.load") as mock_load,
        patch("dreamos.core.coordination.project_board_manager.json.dump") as mock_dump,
        patch(
            "dreamos.core.coordination.project_board_manager.os.replace"
        ) as mock_replace,
        patch(
            "dreamos.core.coordination.project_board_manager.FileLock"
        ) as mock_filelock_class,
    ):
        # Mock file lock context manager
        mock_lock_instance = mock_filelock_class.return_value
        mock_lock_instance.__enter__.return_value = mock_lock_instance
        mock_lock_instance.__exit__.return_value = None

        # Assume board exists and is empty initially for simplicity
        mock_exists.return_value = True
        mock_load.return_value = {"tasks": []}

        # Create PBM instance with a mock path
        pbm = ProjectBoardManager(board_file_path=TEST_BOARD_PATH)
        pbm._file_lock = mock_filelock_class(f"{TEST_BOARD_PATH}.lock")
        return pbm, mock_load, mock_dump, mock_filelock_class, mock_open, mock_replace


@pytest.fixture
def mock_multi_board_pbm(tmp_path):
    """Fixture for PBM interacting with multiple mocked board files."""
    boards_dir = tmp_path / "project_boards_multi"
    boards_dir.mkdir()

    mock_board_data = {
        "future_tasks.jsonl": [],
        "working_tasks.jsonl": [],
        "completed_tasks.jsonl": [],
    }

    # Create initial files
    (boards_dir / "future_tasks.jsonl").write_text("[]", encoding="utf-8")
    (boards_dir / "working_tasks.jsonl").write_text("[]", encoding="utf-8")
    (boards_dir / "completed_tasks.jsonl").write_text("[]", encoding="utf-8")

    # Mock _load_board to return specific data based on filename
    def mock_load_board_func(self, filename):
        # Nonlocal needed if we want to modify the outer dict directly
        # but returning a copy based on filename is cleaner
        if filename in mock_board_data:
            # Return a copy to avoid side effects between tests if data is modified
            return mock_board_data[filename][:]
        return []  # Return empty list if file unknown

    # Mock _atomic_write to update our in-memory dict
    captured_writes = {}

    def mock_atomic_write_func(self, filename, data):
        captured_writes[filename] = data  # Store what *would* be written
        # Update the in-memory store too for subsequent loads in the same test
        if filename in mock_board_data:
            mock_board_data[filename] = data
        print(f"Mock write to {filename}: {len(data)} tasks")  # Debugging

    with patch.object(
        ProjectBoardManager, "_load_board", mock_load_board_func
    ), patch.object(
        ProjectBoardManager, "_atomic_write", mock_atomic_write_func
    ), patch(
        "dreamos.core.coordination.project_board_manager.FileLock"
    ) as mock_filelock_class:
        mock_lock_instance = mock_filelock_class.return_value
        mock_lock_instance.__enter__.return_value = mock_lock_instance
        mock_lock_instance.__exit__.return_value = None

        # Instantiate PBM - board_file_path might not be used directly now
        pbm = ProjectBoardManager(boards_base_dir=boards_dir)
        # Attach the mocked data and capture dict for assertions
        pbm._mock_board_data = mock_board_data
        pbm._captured_writes = captured_writes
        yield pbm  # Provide the configured PBM instance


class TestProjectBoardManager:
    def test_initialization(self, mock_pbm):
        """Test that the ProjectBoardManager initializes correctly,
        loading an empty task list when the board file is mocked.
        Verifies board path and initial empty task state.
        """
        pbm, _, _, _, _, _ = mock_pbm
        assert pbm.board_file_path == TEST_BOARD_PATH
        assert pbm._tasks == []  # Assuming initial load returns empty list

    def test_add_task_success(self, mock_pbm):
        """Test successfully adding a valid task to an empty board.
        Verifies internal task list update, file lock usage, and that
        the correct data is passed to json.dump for saving.
        """
        pbm, mock_load, mock_dump, mock_filelock_class, mock_open, _ = mock_pbm
        mock_load.return_value = {"tasks": []}  # Ensure it starts empty

        new_task = {
            "task_id": "TEST-001",
            "name": "Test Task",
            "description": "A test task",
            "priority": "MEDIUM",
            "status": "PENDING",
            "assigned_agent": None,
            "dependencies": [],
            "notes": "",
            "created_at": "timestamp",
            # Add other required fields based on actual schema
        }

        pbm.add_task(new_task)

        # Verify the task was added internally
        assert len(pbm._tasks) == 1
        assert pbm._tasks[0]["task_id"] == "TEST-001"

        # Verify file lock was acquired and released
        mock_filelock_class.assert_called_with(f"{TEST_BOARD_PATH}.lock")
        mock_lock_instance = mock_filelock_class.return_value
        mock_lock_instance.__enter__.assert_called_once()
        mock_lock_instance.__exit__.assert_called_once()

        # Verify JSON dump was called with the updated task list
        mock_dump.assert_called_once()
        args, kwargs = mock_dump.call_args
        assert args[0] == {"tasks": [new_task]}
        assert "indent" in kwargs  # Check formatting

    def test_add_task_duplicate_id_should_fail(self, mock_pbm):
        """Test that attempting to add a task with an ID that already exists
        on the board raises the appropriate error (e.g., ValueError).
        Verifies that the board state remains unchanged and no save occurs.
        """
        pbm, mock_load, mock_dump, mock_filelock_class, mock_open, _ = mock_pbm

        existing_task = {
            "task_id": "DUPLICATE-001",
            "name": "Existing Task",
            "status": "PENDING",
            # ... other fields
        }
        # Pre-load the board with an existing task
        mock_load.return_value = {"tasks": [existing_task]}
        pbm._load_board()  # Force reload with mock data

        duplicate_task = {
            "task_id": "DUPLICATE-001",  # Same ID
            "name": "Duplicate Task",
            "status": "PENDING",
            # ... other fields
        }

        # Expect an error (e.g., ValueError or custom TaskValidationError)
        # Adjust the expected exception based on PBM implementation
        with pytest.raises(ValueError):  # Or TaskValidationError, etc.
            pbm.add_task(duplicate_task)

        # Verify board state didn't change and no dump occurred
        assert len(pbm._tasks) == 1
        assert pbm._tasks[0]["task_id"] == "DUPLICATE-001"
        mock_dump.assert_not_called()

    def test_get_task_success(self, mock_pbm):
        """Test retrieving an existing task by its ID successfully.
        Verifies the correct task data is returned.
        """
        pbm, mock_load, _, _, _, _ = mock_pbm

        existing_task = {
            "task_id": "GET-001",
            "name": "Task To Get",
            "status": "PENDING",
            # ... other fields
        }
        mock_load.return_value = {"tasks": [existing_task]}
        pbm._load_board()

        retrieved_task = pbm.get_task("GET-001")
        assert retrieved_task is not None
        assert retrieved_task["task_id"] == "GET-001"
        assert retrieved_task["name"] == "Task To Get"

    def test_get_task_not_found(self, mock_pbm):
        """Test that attempting to retrieve a task with a non-existent ID
        raises the appropriate error (TaskNotFoundError).
        """
        pbm, mock_load, _, _, _, _ = mock_pbm
        mock_load.return_value = {"tasks": []}  # Empty board
        pbm._load_board()

        # Expect TaskNotFoundError (adjust if PBM uses a different exception)
        from dreamos.core.errors import TaskNotFoundError  # Assuming this exists

        with pytest.raises(TaskNotFoundError):
            pbm.get_task("NON-EXISTENT-001")

    def test_update_task_status_success(self, mock_pbm):
        """Test successfully updating the status of an existing task.
        Verifies the internal state change, lock usage, and that the
        correct updated data is passed to json.dump.
        """
        pbm, mock_load, mock_dump, mock_filelock_class, _, _ = mock_pbm

        task_to_update = {
            "task_id": "UPDATE-001",
            "name": "Task To Update",
            "status": "PENDING",
            # ... other fields
        }
        mock_load.return_value = {"tasks": [task_to_update]}
        pbm._load_board()

        # Verify initial status
        assert pbm._tasks[0]["status"] == "PENDING"

        pbm.update_task_status("UPDATE-001", "WORKING")

        # Verify status updated internally
        assert len(pbm._tasks) == 1
        assert pbm._tasks[0]["task_id"] == "UPDATE-001"
        assert pbm._tasks[0]["status"] == "WORKING"

        # Verify lock and dump were called
        mock_filelock_class.assert_called_with(f"{TEST_BOARD_PATH}.lock")
        mock_lock_instance = mock_filelock_class.return_value
        # Lock should be called for load and update
        assert mock_lock_instance.__enter__.call_count == 2
        assert mock_lock_instance.__exit__.call_count == 2
        mock_dump.assert_called_once()
        args, kwargs = mock_dump.call_args
        assert args[0]["tasks"][0]["status"] == "WORKING"  # Check dumped data

    def test_update_task_status_not_found(self, mock_pbm):
        """Test that attempting to update the status of a non-existent task
        raises TaskNotFoundError and does not attempt to save.
        """
        pbm, mock_load, mock_dump, mock_filelock_class, _, _ = mock_pbm
        mock_load.return_value = {"tasks": []}  # Empty board
        pbm._load_board()

        from dreamos.core.errors import TaskNotFoundError

        with pytest.raises(TaskNotFoundError):
            pbm.update_task_status("NON-EXISTENT-001", "WORKING")

        # Verify no dump occurred
        mock_dump.assert_not_called()

    # Assuming ProjectBoardManager has a `claim_future_task` method
    # And separate boards (e.g., future_tasks.json, working_tasks.json)
    # This test will need significant adjustment based on actual PBM logic
    # For now, adding placeholder structure

    def test_claim_future_task_success(self, mock_pbm):
        """Placeholder: Test claiming a task successfully (moves between boards)."""
        pbm, mock_load, mock_dump, mock_filelock_class, _, mock_replace = mock_pbm
        # Mock setup would involve multiple board files and loading logic
        # TODO: Mock _load_board to handle multiple paths (future/working)
        # TODO: Pre-load a task in the 'future' board mock data
        # Call pbm.claim_future_task(task_id, agent_id)
        # TODO: Assert task removed from 'future' mock data
        # TODO: Assert task added to 'working' mock data (or internal state)
        # TODO: Assert correct file dumps occurred (write to both files)
        pass

    def test_claim_future_task_not_found(self, mock_pbm):
        """Placeholder: Test claiming a non-existent task fails."""
        pbm, mock_load, mock_dump, mock_filelock_class, _, _ = mock_pbm
        # TODO: Mock _load_board for multiple paths
        # TODO: Ensure task_id does not exist in 'future' board mock data
        # Call pbm.claim_future_task(non_existent_task_id, agent_id)
        # TODO: Assert expected error is raised (e.g., TaskNotFoundError)
        # TODO: Assert no file dumps occurred
        pass

    # Assuming ProjectBoardManager has a `complete_task` method
    # that likely moves tasks to a completed board or updates status.
    # Placeholder structure:
    def test_complete_task_success(self, mock_pbm):
        """Placeholder: Test completing a task successfully."""
        pbm, mock_load, mock_dump, mock_filelock_class, _, mock_replace = mock_pbm
        # Mock setup: Load a task into the working state (mock working board)
        # TODO: Mock _load_board to handle multiple paths (working/completed)
        # TODO: Pre-load a task in the 'working' board mock data
        # Call pbm.complete_task(task_id, result_summary)
        # TODO: Assert task removed from 'working' mock data (or status updated)
        # TODO: Assert task added to 'completed' mock data (or status updated)
        # TODO: Assert correct file dumps occurred
        pass

    def test_complete_task_not_found(self, mock_pbm):
        """Placeholder: Test completing a non-existent task fails."""
        pbm, mock_load, mock_dump, mock_filelock_class, _, _ = mock_pbm
        # TODO: Mock _load_board for multiple paths
        # TODO: Ensure task_id does not exist in 'working' board mock data
        # Call pbm.complete_task(non_existent_task_id, result_summary)
        # TODO: Assert expected error is raised (e.g., TaskNotFoundError)
        # TODO: Assert no file dumps occurred
        pass

    def test_list_tasks_empty(self, mock_pbm):
        """Test listing tasks when the board is empty.
        Verifies that an empty list is returned.
        """
        pbm, mock_load, _, _, _, _ = mock_pbm
        mock_load.return_value = {"tasks": []}  # Ensure empty board
        pbm._load_board()

        tasks = pbm.list_tasks()
        assert tasks == []

    def test_list_tasks_with_data(self, mock_pbm):
        """Test listing tasks returns the correct data when the board has tasks.
        Verifies the length and content of the returned list.
        """
        pbm, mock_load, _, _, _, _ = mock_pbm
        mock_tasks = [
            {"task_id": "LIST-001", "name": "Task A"},
            {"task_id": "LIST-002", "name": "Task B"},
        ]
        mock_load.return_value = {"tasks": mock_tasks}
        pbm._load_board()

        tasks = pbm.list_tasks()
        assert len(tasks) == 2
        assert tasks == mock_tasks  # Should return a copy of internal list

    # TODO: Test error handling (ValidationError, Locking errors)
    # TODO: Test edge cases (empty board)

    def test_claim_future_task_success_multi(self, mock_multi_board_pbm):
        """Test claiming a task successfully moves it from future to working (multi-board mock)."""
        pbm = mock_multi_board_pbm
        task_id = "claim-multi-1"
        agent_id = "MultiAgent"

        # Setup: Put task in the mocked future board data
        pbm._mock_board_data["future_tasks.jsonl"] = [
            {"task_id": task_id, "status": "PENDING"}
        ]
        pbm._mock_board_data["working_tasks.jsonl"] = []

        # Act
        result = pbm.claim_future_task(task_id, agent_id)

        # Assert
        assert result is True

        # Check captured writes (what would have been saved)
        assert "future_tasks.jsonl" in pbm._captured_writes
        assert "working_tasks.jsonl" in pbm._captured_writes
        assert len(pbm._captured_writes["future_tasks.jsonl"]) == 0
        assert len(pbm._captured_writes["working_tasks.jsonl"]) == 1
        working_task = pbm._captured_writes["working_tasks.jsonl"][0]
        assert working_task["task_id"] == task_id
        assert working_task["status"] == "WORKING"
        assert working_task["assigned_agent"] == agent_id

    def test_claim_future_task_not_found_multi(self, mock_multi_board_pbm):
        """Test claiming a non-existent task fails (multi-board mock)."""
        pbm = mock_multi_board_pbm
        task_id = "claim-multi-missing"
        agent_id = "MultiAgent"

        # Setup: Ensure boards are empty
        pbm._mock_board_data["future_tasks.jsonl"] = []
        pbm._mock_board_data["working_tasks.jsonl"] = []
        pbm._captured_writes.clear()  # Clear previous writes

        # Act & Assert
        # Expect False return or TaskNotFoundError depending on implementation
        # Assuming False based on previous tests
        result = pbm.claim_future_task(task_id, agent_id)
        assert result is False
        # Assert no writes occurred
        assert "future_tasks.jsonl" not in pbm._captured_writes
        assert "working_tasks.jsonl" not in pbm._captured_writes
