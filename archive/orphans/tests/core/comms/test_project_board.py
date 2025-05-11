# tests/core/comms/test_project_board.py
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import filelock
import pytest

# Add src to path to allow importing dreamos (adjust if needed)
SCRIPT_DIR = Path(__file__).parent.parent.parent.parent.resolve()
SRC_DIR = SCRIPT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dreamos.coordination.project_board_manager import (  # noqa: E402
    COMPLETED_TASKS_FILENAME,
    FUTURE_TASKS_FILENAME,
    WORKING_TASKS_FILENAME,
    ProjectBoardManager,
)

# Add import for ProjectBoardError if it exists elsewhere or handle if removed
# Placeholder: Assuming it might be part of ProjectBoardManager or a general exception
try:
    from dreamos.coordination.project_board_manager import ProjectBoardError
except ImportError:
    # Define a placeholder if not found, tests might need adjustment
    class ProjectBoardError(Exception):
        pass


# Assume compaction_utils has this error type if needed for mocking
# from dreamos.memory.compaction_utils import CompactionError

# --- Fixtures ---


@pytest.fixture
def board_manager(tmp_path: Path) -> ProjectBoardManager:
    """Provides a ProjectBoardManager instance using a temporary directory."""
    boards_dir = tmp_path / "project_boards"
    boards_dir.mkdir()
    # Create initial empty files to prevent FileNotFoundError during tests
    (boards_dir / FUTURE_TASKS_FILENAME).write_text("[]", encoding="utf-8")
    (boards_dir / WORKING_TASKS_FILENAME).write_text("[]", encoding="utf-8")
    (boards_dir / COMPLETED_TASKS_FILENAME).write_text("[]", encoding="utf-8")
    return ProjectBoardManager(boards_base_dir=boards_dir)


@pytest.fixture
def future_tasks_file(board_manager: ProjectBoardManager) -> Path:
    return board_manager._get_global_task_file_path(FUTURE_TASKS_FILENAME)


@pytest.fixture
def working_tasks_file(board_manager: ProjectBoardManager) -> Path:
    return board_manager._get_global_task_file_path(WORKING_TASKS_FILENAME)


@pytest.fixture
def completed_tasks_file(board_manager: ProjectBoardManager) -> Path:
    return board_manager._get_global_task_file_path(COMPLETED_TASKS_FILENAME)


# --- Helper Functions ---


def _read_json(file_path: Path) -> list:
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []  # Return empty on parse error for simplicity in tests


def _write_json(file_path: Path, data: list):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# --- Test Cases ---


# Test claim_future_task (Test Case 1.1)
class TestClaimFutureTask:
    def test_claim_success(
        self,
        board_manager: ProjectBoardManager,
        future_tasks_file: Path,
        working_tasks_file: Path,
    ):
        """Test Case 1.1.1: Successful claim moves task."""
        task_id = "task_claim_success"
        agent_id = "AgentTest"
        _write_json(future_tasks_file, [{"task_id": task_id, "status": "PENDING"}])

        result = board_manager.claim_future_task(task_id, agent_id)

        assert result is True
        future_tasks = _read_json(future_tasks_file)
        working_tasks = _read_json(working_tasks_file)
        assert len(future_tasks) == 0
        assert len(working_tasks) == 1
        claimed_task = working_tasks[0]
        assert claimed_task["task_id"] == task_id
        assert claimed_task["assigned_agent"] == agent_id
        assert claimed_task["status"] == "WORKING"
        assert "timestamp_claimed_utc" in claimed_task
        assert "timestamp_updated" in claimed_task

    def test_claim_not_found(
        self,
        board_manager: ProjectBoardManager,
        future_tasks_file: Path,
        working_tasks_file: Path,
    ):
        """Test Case 1.1.2: Claiming non-existent task fails."""
        task_id = "task_claim_not_found"
        agent_id = "AgentTest"
        _write_json(future_tasks_file, [])  # Ensure task isn't there

        result = board_manager.claim_future_task(task_id, agent_id)

        assert result is False
        assert len(_read_json(future_tasks_file)) == 0
        assert len(_read_json(working_tasks_file)) == 0

    def test_claim_already_working(
        self,
        board_manager: ProjectBoardManager,
        future_tasks_file: Path,
        working_tasks_file: Path,
    ):
        """Test Case 1.1.3: Claiming task already in working fails."""
        task_id = "task_claim_already_working"
        agent_id = "AgentTest"
        _write_json(future_tasks_file, [])
        _write_json(working_tasks_file, [{"task_id": task_id, "status": "WORKING"}])

        result = board_manager.claim_future_task(task_id, agent_id)

        assert result is False  # Fails because it's not found in future_tasks
        assert len(_read_json(future_tasks_file)) == 0
        assert len(_read_json(working_tasks_file)) == 1  # Working tasks unchanged

    # Add more claim tests: invalid format, concurrency (mocked/conceptual)


# Test move_task_to_completed (Test Case 1.3)
class TestMoveTaskToCompleted:
    def test_move_success(
        self,
        board_manager: ProjectBoardManager,
        working_tasks_file: Path,
        completed_tasks_file: Path,
    ):
        """Test Case 1.3.1: Successful move to completed."""
        task_id = "task_move_success"
        agent_id = "AgentTest"
        initial_task = {
            "task_id": task_id,
            "status": "WORKING",
            "assigned_agent": agent_id,
        }
        _write_json(working_tasks_file, [initial_task])
        _write_json(completed_tasks_file, [])

        final_updates = {"status": "COMPLETED", "notes": "All done!"}
        result = board_manager.move_task_to_completed(task_id, final_updates)

        assert result is True
        working_tasks = _read_json(working_tasks_file)
        completed_tasks = _read_json(completed_tasks_file)
        assert len(working_tasks) == 0
        assert len(completed_tasks) == 1
        moved_task = completed_tasks[0]
        assert moved_task["task_id"] == task_id
        assert moved_task["assigned_agent"] == agent_id  # Preserves original fields
        assert moved_task["status"] == "COMPLETED"
        assert moved_task["notes"] == "All done!"
        assert "timestamp_updated" in moved_task
        assert "timestamp_completed" in moved_task

    def test_move_not_found(
        self,
        board_manager: ProjectBoardManager,
        working_tasks_file: Path,
        completed_tasks_file: Path,
    ):
        """Test Case 1.3.2: Moving non-existent task fails."""
        task_id = "task_move_not_found"
        _write_json(working_tasks_file, [])
        _write_json(completed_tasks_file, [])

        final_updates = {"status": "COMPLETED"}
        result = board_manager.move_task_to_completed(task_id, final_updates)

        assert result is False
        assert len(_read_json(working_tasks_file)) == 0
        assert len(_read_json(completed_tasks_file)) == 0

    # Add more move tests: invalid format, concurrency (mocked/conceptual)


# Test update_task (Test Case 1.2)
class TestUpdateTask:
    def test_update_success(
        self, board_manager: ProjectBoardManager, working_tasks_file: Path
    ):
        """Test Case 1.2.1: Successful update of a working task."""
        task_id = "task_update_success"
        agent_id = "AgentTest"
        initial_task = {
            "task_id": task_id,
            "status": "WORKING",
            "assigned_agent": agent_id,
            "notes": "Initial note",
        }
        _write_json(working_tasks_file, [initial_task])

        updates = {"status": "WORKING", "notes": "Updated note", "progress_percent": 50}
        result = board_manager.update_task(task_id, agent_id, updates)

        assert result is True
        working_tasks = _read_json(working_tasks_file)
        assert len(working_tasks) == 1
        updated_task = working_tasks[0]
        assert updated_task["task_id"] == task_id
        assert updated_task["status"] == "WORKING"
        assert updated_task["notes"] == "Updated note"
        assert updated_task["progress_percent"] == 50
        assert "timestamp_updated" in updated_task  # Check timestamp updated

    def test_update_not_found(
        self, board_manager: ProjectBoardManager, working_tasks_file: Path
    ):
        """Test Case 1.2.2: Updating a non-existent task fails."""
        task_id = "task_update_not_found"
        agent_id = "AgentTest"
        _write_json(working_tasks_file, [])  # Ensure task isn't there

        updates = {"notes": "This should fail"}

        # Expecting update_task to raise TaskNotFoundError or return False
        # Based on claim_future_task returning False, assuming False return
        result = board_manager.update_task(task_id, agent_id, updates)
        assert result is False

        # Could also test for specific exception if that's the expected behavior:
        # with pytest.raises(TaskNotFoundError):
        #     board_manager.update_task(task_id, agent_id, updates)

        assert len(_read_json(working_tasks_file)) == 0  # Board unchanged

    # TODO: Add test for trying to update a task on the wrong board (e.g., future_tasks)
    # TODO: Add test for invalid update data (if schema validation is active)


# Test Error Conditions
class TestErrorConditions:
    @patch("filelock.FileLock.acquire")
    def test_lock_timeout_on_read(
        self, mock_acquire, board_manager: ProjectBoardManager, working_tasks_file: Path
    ):
        """Test BoardLockError is raised if lock times out during read."""
        # Ensure filelock is mocked correctly if FILELOCK_AVAILABLE is False in PBM
        if not board_manager.FILELOCK_AVAILABLE:
            pytest.skip("Filelock library not available, skipping lock test.")

        task_id = "task_lock_timeout"
        agent_id = "AgentTest"  # noqa: F841
        _write_json(working_tasks_file, [{"task_id": task_id, "status": "WORKING"}])

        mock_acquire.side_effect = filelock.Timeout("Mock Timeout")

        with pytest.raises(BoardLockError):  # noqa: F821
            # Calling a method that reads the board should trigger the error
            board_manager.get_task(task_id, board="working")

    @patch(
        "src.dreamos.coordination.project_board_manager.ProjectBoardManager._atomic_write"
    )
    def test_write_failure_on_update(
        self,
        mock_atomic_write,
        board_manager: ProjectBoardManager,
        working_tasks_file: Path,
    ):
        """Test update fails gracefully if underlying write fails."""
        task_id = "task_write_fail"
        agent_id = "AgentTest"
        initial_task = {"task_id": task_id, "status": "WORKING"}
        _write_json(working_tasks_file, [initial_task])

        mock_atomic_write.side_effect = IOError("Mock write failure")

        updates = {"notes": "Update that will fail to save"}

        # Depending on implementation, this might return False or raise ProjectBoardManagerError  # noqa: E501
        # Let's assume it returns False for now, consistent with other failures
        result = board_manager.update_task(task_id, agent_id, updates)
        assert result is False

        # Verify the original task board state wasn't corrupted (if possible)
        # This might be hard to assert perfectly without knowing PBM's internal state
        # after a failed write.
        # working_tasks = _read_json(working_tasks_file)
        # assert len(working_tasks) == 1
        # assert 'notes' not in working_tasks[0]

    # TODO: Add tests for lock timeout during write operations
    # TODO: Add tests for schema validation errors if applicable


# Test Validation Logic
class TestValidationLogic:
    @patch("subprocess.run")
    def test_validation_calls_flake8(
        self, mock_subprocess_run, board_manager: ProjectBoardManager
    ):
        """Test that _validate_task_completion calls flake8 for .py files."""
        task = MagicMock(spec=TaskMessage)  # noqa: F821
        task.task_id = "task_validate_flake8"
        result = {
            "summary": "Did stuff",
            "modified_files": ["src/file1.py", "README.md", "src/subdir/file2.py"],
        }
        modified_files_list = result["modified_files"]

        # Mock subprocess to simulate flake8 passing
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_subprocess_run.return_value = mock_process

        async def run_validation():
            # Must be run within an async function
            return await board_manager._validate_task_completion(
                task, result, modified_files_list
            )

        is_valid, details = asyncio.run(run_validation())

        assert is_valid is True
        assert "Validation passed." in details
        # Assert subprocess was called with the python files
        expected_cmd_part = [
            sys.executable,
            "-m",
            "flake8",
            "src/file1.py",
            "src/subdir/file2.py",
        ]
        # Check if the expected command part matches the beginning of the actual call args  # noqa: E501
        call_args, call_kwargs = mock_subprocess_run.call_args
        assert call_args[0][: len(expected_cmd_part)] == expected_cmd_part
        assert call_kwargs.get("cwd") == board_manager._project_root

    @patch("subprocess.run")
    def test_validation_fails_on_flake8_error(
        self, mock_subprocess_run, board_manager: ProjectBoardManager
    ):
        """Test that validation fails if flake8 returns errors."""
        task = MagicMock(spec=TaskMessage)  # noqa: F821
        task.task_id = "task_validate_flake8_fail"
        result = {"summary": "Did stuff", "modified_files": ["src/bad_file.py"]}
        modified_files_list = result["modified_files"]

        # Mock subprocess to simulate flake8 failing
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = "src/bad_file.py:1:1: F401 'os' imported but unused"
        mock_process.stderr = ""
        mock_subprocess_run.return_value = mock_process

        async def run_validation():
            return await board_manager._validate_task_completion(
                task, result, modified_files_list
            )

        is_valid, details = asyncio.run(run_validation())

        assert is_valid is False
        assert "flake8 failed" in details
        assert "F401 'os' imported but unused" in details
        mock_subprocess_run.assert_called_once()

    @patch("subprocess.run")
    def test_validation_handles_flake8_not_found(
        self, mock_subprocess_run, board_manager: ProjectBoardManager
    ):
        """Test validation handles FileNotFoundError if flake8 isn't installed."""
        task = MagicMock(spec=TaskMessage)  # noqa: F821
        task.task_id = "task_validate_flake8_notfound"
        result = {"summary": "Did stuff", "modified_files": ["src/some_file.py"]}
        modified_files_list = result["modified_files"]

        mock_subprocess_run.side_effect = FileNotFoundError("flake8 not found")

        async def run_validation():
            return await board_manager._validate_task_completion(
                task, result, modified_files_list
            )

        is_valid, details = asyncio.run(run_validation())

        assert is_valid is False  # Failure because validation couldn't run
        assert "flake8 command not found" in details

    # TODO: Add tests for basic validation checks (summary, dict format etc.)
    # TODO: Add test for case with no modified files
    # TODO: Add test for case where modified_files list contains non-strings or non-files  # noqa: E501


# TODO: Add tests for update_global_task
# TODO: Add tests for project-specific methods (get/set state, artifacts) if needed
# TODO: Add tests for error conditions (locking timeouts, write failures - may require mocking)  # noqa: E501

# {{ EDIT START: Add more test cases for validation and edge cases }}


class TestUpdateTaskEdgeCases:
    def test_update_task_on_future_board(
        self,
        board_manager: ProjectBoardManager,
        future_tasks_file: Path,
        working_tasks_file: Path,
    ):
        """Test updating a task that only exists on the future board fails."""
        task_id = "task_on_future"
        agent_id = "AgentTest"
        _write_json(future_tasks_file, [{"task_id": task_id, "status": "PENDING"}])
        _write_json(working_tasks_file, [])

        updates = {"notes": "Should not apply"}
        # Expect update_task to return False or raise TaskNotFoundError when task not in working board
        # Current PBM returns False if not found in working list
        result = board_manager.update_task(task_id, agent_id, updates)
        assert result is False
        # Ensure future tasks remain unchanged
        assert len(_read_json(future_tasks_file)) == 1
        assert len(_read_json(working_tasks_file)) == 0

    def test_update_task_on_completed_board(
        self,
        board_manager: ProjectBoardManager,
        completed_tasks_file: Path,
        working_tasks_file: Path,
    ):
        """Test updating a task that only exists on the completed board fails."""
        task_id = "task_on_completed"
        agent_id = "AgentTest"
        _write_json(completed_tasks_file, [{"task_id": task_id, "status": "COMPLETED"}])
        _write_json(working_tasks_file, [])

        updates = {"notes": "Should not apply"}
        result = board_manager.update_task(task_id, agent_id, updates)
        assert result is False
        assert len(_read_json(completed_tasks_file)) == 1
        assert len(_read_json(working_tasks_file)) == 0

    def test_update_task_with_invalid_update_data_type(
        self, board_manager: ProjectBoardManager, working_tasks_file: Path
    ):
        """Test update fails if 'updates' is not a dictionary (basic check)."""
        task_id = "task_invalid_update_type"
        agent_id = "AgentTest"
        _write_json(working_tasks_file, [{"task_id": task_id, "status": "WORKING"}])

        invalid_updates = "not_a_dict"
        # Expect TypeError or similar validation error
        with pytest.raises(TypeError):
            board_manager.update_task(task_id, agent_id, invalid_updates)
        # Check task was not modified
        working_tasks = _read_json(working_tasks_file)
        assert len(working_tasks) == 1
        assert "not_a_dict" not in str(working_tasks[0])


class TestInternalValidation:
    def test_validate_task_data_missing_id(self, board_manager: ProjectBoardManager):
        """Test internal validation rejects task data missing task_id."""
        invalid_data = {"summary": "Missing ID", "status": "PENDING"}
        # Assume _validate_task_data raises ProjectBoardError or ValueError
        with pytest.raises((ProjectBoardError, ValueError)):
            board_manager._validate_task_data(invalid_data, is_new=True)

    def test_validate_task_data_valid(self, board_manager: ProjectBoardManager):
        """Test internal validation accepts minimally valid task data."""
        valid_data = {
            "task_id": "valid-123",
            "summary": "Valid task",
            "status": "PENDING",
        }
        try:
            board_manager._validate_task_data(valid_data, is_new=True)
        except (ProjectBoardError, ValueError) as e:
            pytest.fail(f"Validation failed unexpectedly: {e}")

    def test_validate_task_data_completed_missing_modified_files(
        self, board_manager: ProjectBoardManager
    ):
        """Test internal validation rejects COMPLETED status without modified_files."""
        invalid_data = {
            "task_id": "comp-no-files",
            "summary": "Completed task",
            "status": "COMPLETED",  # Status requires modified_files
            # missing 'modified_files': []
        }
        # Assume validation raises ProjectBoardError or ValueError
        with pytest.raises(
            (ProjectBoardError, ValueError),
            match=r"modified_files.*required.*COMPLETED",
        ):
            board_manager._validate_task_data(
                invalid_data, is_new=False
            )  # Check existing task update

    def test_validate_task_data_completed_with_modified_files(
        self, board_manager: ProjectBoardManager
    ):
        """Test internal validation accepts COMPLETED status with modified_files."""
        valid_data = {
            "task_id": "comp-with-files",
            "summary": "Completed task",
            "status": "COMPLETED",
            "modified_files": ["src/file1.py"],
        }
        try:
            board_manager._validate_task_data(valid_data, is_new=False)
        except (ProjectBoardError, ValueError) as e:
            pytest.fail(
                f"Validation failed unexpectedly for completed task with files: {e}"
            )

    # {{ EDIT START: Add tests for schema validation errors }}
    def test_validate_task_data_schema_wrong_type(
        self, board_manager: ProjectBoardManager
    ):
        """Test internal validation rejects task data with incorrect field type based on schema."""
        # Assumes schema requires 'priority' to be a string, not integer
        invalid_data = {
            "task_id": "schema-wrong-type",
            "summary": "Task with wrong type",
            "status": "PENDING",
            "priority": 1,  # Incorrect type
        }
        # Assumes _validate_task_data raises TaskValidationError for schema issues
        with pytest.raises(TaskValidationError, match=r"Schema validation failed"):
            board_manager._validate_task_data(invalid_data, is_new=True)

    def test_validate_task_data_schema_missing_required(
        self, board_manager: ProjectBoardManager
    ):
        """Test internal validation rejects task data missing a schema-required field."""
        # Assumes schema requires 'summary' field
        invalid_data = {
            "task_id": "schema-missing-req",
            # 'summary': "Missing summary",
            "status": "PENDING",
        }
        with pytest.raises(TaskValidationError, match=r"Schema validation failed"):
            board_manager._validate_task_data(invalid_data, is_new=True)

    # {{ EDIT END }}


# {{ EDIT END }}
