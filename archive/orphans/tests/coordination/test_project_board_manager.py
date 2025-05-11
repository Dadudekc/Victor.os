# tests/coordination/test_project_board_manager.py

import argparse
import json
import sys
import time
from pathlib import Path
from unittest import mock
from unittest.mock import patch

import pytest

# from dreamos.core.coordination.task_nexus import ( # Removed - ModuleNotFoundError
#     TaskNexus,
#     TaskStatus,
#     TaskPriority,
# )
# from dreamos.core.coordination.agent_bus import AgentBus, BaseEvent, EventType # Removed - Causes ImportError  # noqa: E501
from dreamos.core.config import AppConfig, PathsConfig

# E402 fixes: Move project imports after sys.path manipulation if needed
# (Assuming tests/ directory structure allows direct import here)
# from dreamos.core.coordination.agent_bus import AgentBus, BaseEvent, EventType
# F811/F401 fixes for errors:
# from dreamos.core.errors import BoardLockError, TaskNotFoundError, TaskValidationError, ProjectBoardError  # noqa: E501
from dreamos.core.errors import (  # Re-import specifically where needed or fix original definitions  # noqa: E501
    BoardLockError,
    ProjectBoardError,  # ADDED: Import ProjectBoardError
    TaskNotFoundError,
    TaskValidationError,
)

# Add src directory to path for imports
SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

# EDIT START: Import jsonschema for mocking exceptions
import jsonschema  # noqa: E402

# Module to test
from dreamos.coordination.project_board_manager import (  # noqa: E402
    BoardLockError,  # noqa: F811
    ProjectBoardManager,
    TaskNotFoundError,  # noqa: F811
    TaskValidationError,  # noqa: F811
)
from dreamos.core.errors import (  # noqa: E402
    BoardLockError,  # noqa: F811
    TaskNotFoundError,  # noqa: F811
    TaskValidationError,  # noqa: F811
)

# EDIT END


# Mock filelock if not installed or for testing purposes
class MockFileLock:
    def __init__(self, path, timeout):
        self.path = path
        self.timeout = timeout
        self._locked = False

    def __enter__(self):
        # Simulate potential timeout
        # if simulate_timeout:
        #     raise filelock.Timeout("Simulated timeout")
        if self._locked:
            raise RuntimeError("Lock already acquired in this mock context")
        print(f"Mock Lock Acquired: {self.path}")
        self._locked = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"Mock Lock Released: {self.path}")
        self._locked = False


# Replace filelock globally for tests if needed, or patch per test
# Replace if filelock lib is not installed for test env
# if project_board_manager.filelock is None:
#     project_board_manager.filelock = MagicMock()
#     project_board_manager.filelock.FileLock = MockFileLock
#     project_board_manager.filelock.Timeout = TimeoutError # Or a custom mock exception

# Mock jsonschema if needed - Now required for these tests
# Assume jsonschema is importable, otherwise tests will fail

# --- Test Fixtures ---


@pytest.fixture
def mock_app_config(tmp_path: Path) -> AppConfig:
    """Provides a mock AppConfig pointing to a temporary directory."""
    runtime_path = tmp_path / "runtime"
    boards_path = runtime_path / "agent_comms" / "central_task_boards"
    logs_path = runtime_path / "logs"
    schema_path = SRC_DIR / "dreamos" / "coordination" / "tasks" / "task-schema.json"

    # Create a dummy schema file if it doesn't exist in the source
    # (pyfakefs won't see the real one unless explicitly added)
    schema_dir = schema_path.parent
    schema_dir.mkdir(parents=True, exist_ok=True)  # Ensure dir exists
    if not schema_path.exists():
        # Create a minimal valid schema for testing basic validation
        schema_content = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "DreamOS Task",
            "description": "Schema for a task managed by DreamOS",
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Unique task identifier"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "status": {"type": "string"},
                # Add other core properties as needed for tests
            },
            "required": [
                "task_id",
                "name",
                "description",
                "status",
            ],  # Example requirements
        }
        with open(schema_path, "w") as f:
            json.dump(schema_content, f)

    # Ensure paths used by PBM exist within the mock config
    boards_path.mkdir(parents=True, exist_ok=True)

    # Create a basic config structure
    config = AppConfig(
        paths=PathsConfig(
            runtime=runtime_path,
            logs=logs_path,
            agent_comms=runtime_path / "agent_comms",
            central_task_boards=boards_path,
            task_schema=schema_path,
            project_root=tmp_path,
        )
    )
    setattr(config, "config_file_path", tmp_path / "runtime/config/dummy_config.yaml")
    return config


@pytest.fixture
def pbm(mock_app_config: AppConfig, fs):  # Add fs fixture from pyfakefs
    """Provides a PBM instance initialized with mock config and fake filesystem."""
    # Ensure the schema file exists in the fake filesystem *before* PBM init
    if not fs.exists(mock_app_config.paths.task_schema):
        schema_content = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "DreamOS Task",
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "status": {"type": "string"},
            },
            "required": ["task_id", "name", "description", "status"],
        }
        fs.create_file(
            mock_app_config.paths.task_schema, contents=json.dumps(schema_content)
        )

    # Ensure the base boards directory exists in the fake filesystem
    fs.create_dir(mock_app_config.paths.central_task_boards)

    # Disable file locking for tests unless specifically testing locking
    with patch("dreamos.coordination.project_board_manager.FILELOCK_AVAILABLE", False):
        # Need to create the instance *after* fs has potentially created schema
        manager = ProjectBoardManager(config=mock_app_config)
        yield manager  # Use yield for setup/teardown if needed


@pytest.fixture
def sample_task_1() -> dict:
    """A sample valid task dictionary."""
    return {
        "task_id": "test-task-001",
        "name": "Test Task One",
        "description": "Description for test task 1",
        "priority": "MEDIUM",
        "status": "PENDING",
        "assigned_agent": None,
        "created_by": "pytest-fixture",
        "timestamp_created_utc": time.time(),  # noqa: F821
    }


@pytest.fixture
def sample_task_2() -> dict:
    """Another sample valid task dictionary."""
    return {
        "task_id": "test-task-002",
        "name": "Test Task Two",
        "description": "Description for test task 2",
        "priority": "HIGH",
        "status": "PENDING",
        "assigned_agent": None,
        "created_by": "pytest-fixture",
        "timestamp_created_utc": time.time(),  # noqa: F821
    }


@pytest.fixture
def temp_test_dir(tmp_path):  # tmp_path is a pytest fixture
    test_dir = tmp_path / "pbm_test"
    test_dir.mkdir()
    # Create necessary subdirs if PBM expects them
    (test_dir / "runtime/agent_comms/project_boards").mkdir(parents=True, exist_ok=True)
    yield test_dir
    # Teardown: remove the directory after test completes
    # shutil.rmtree(test_dir) # tmp_path handles cleanup


# Fixture for sample valid task data
@pytest.fixture
def sample_task_details():
    return {
        "task_id": "TEST-TASK-001",
        "description": "A sample task for testing.",
        "priority": "HIGH",
        "notes": ["Initial task notes."],  # Added notes for testing update append
        # Add other fields required by schema if known
    }


@pytest.fixture
def mock_pbm_with_schema(mock_app_config: AppConfig, fs):
    """Provides a PBM instance where jsonschema is mocked, using AppConfig."""
    # EDIT START: Refactor to use AppConfig and fs fixtures
    # Ensure schema exists in fake filesystem
    if not fs.exists(mock_app_config.paths.task_schema):
        schema_content = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "DreamOS Task",
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "status": {"type": "string"},
            },
            "required": ["task_id", "name", "description", "status"],
        }
        fs.create_file(
            mock_app_config.paths.task_schema, contents=json.dumps(schema_content)
        )
    fs.create_dir(mock_app_config.paths.central_task_boards)

    # Patch jsonschema within the PBM module's scope
    with patch(
        "dreamos.coordination.project_board_manager.jsonschema"
    ) as mock_jsonschema_lib:
        mock_jsonschema_lib.validate = mock.MagicMock()
        mock_jsonschema_lib.exceptions = mock.MagicMock()
        # Simulate the specific exception type jsonschema raises
        mock_jsonschema_lib.exceptions.ValidationError = jsonschema.ValidationError

        # Instantiate PBM *while the patch is active* using AppConfig
        with patch(
            "dreamos.coordination.project_board_manager.FILELOCK_AVAILABLE", False
        ):
            manager = ProjectBoardManager(config=mock_app_config)

        # Crucially, ensure the schema is loaded (PBM __init__ does this)
        assert manager._task_schema is not None, "Schema must load for validation tests"

        # Attach the mock validate function for inspection
        manager._mock_jsonschema_validate = mock_jsonschema_lib.validate
        yield manager  # Return the manager instance with mocked validation
    # OLD IMPLEMENTATION - REMOVED
    # future_path = "runtime/agent_comms/project_boards/future_tasks_schema.json"
    # working_path = "runtime/agent_comms/project_boards/working_tasks_schema.json"
    # manager = ProjectBoardManager(
    #     future_tasks_path=future_path,
    #     working_tasks_path=working_path,
    #     project_root=temp_test_dir,
    # )
    # manager._task_schema = manager._load_schema()
    # assert manager._task_schema is not None, "Schema must load for validation tests"
    # manager._mock_jsonschema_validate = mock_jsonschema_lib.validate
    # yield manager
    # EDIT END


@pytest.fixture
# TODO: Rename this fixture to avoid confusion with the removed deprecated 'pbm_instance'. e.g., 'pbm_with_real_schema'  # noqa: E501
def pbm_with_real_schema(mock_app_config: AppConfig, fs):
    """Provides a PBM instance using a real schema file (in fake fs), no mocking of jsonschema."""
    # Ensure schema exists in fake filesystem
    if not fs.exists(mock_app_config.paths.task_schema):
        schema_content = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "DreamOS Task Schema",
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["task_id", "description"],
        }
        fs.create_file(
            mock_app_config.paths.task_schema, contents=json.dumps(schema_content)
        )
    fs.create_dir(mock_app_config.paths.central_task_boards)

    # Disable file locking
    with patch("dreamos.coordination.project_board_manager.FILELOCK_AVAILABLE", False):
        manager = ProjectBoardManager(config=mock_app_config)
        yield manager


# --- Test Cases ---


def test_pbm_initialization(pbm: ProjectBoardManager, temp_test_dir):
    """Test if ProjectBoardManager initializes correctly."""
    assert pbm is not None
    assert pbm.config.paths.project_root == temp_test_dir.resolve()
    assert pbm.backlog_path.name == "task_backlog.json"
    assert pbm.working_tasks_path.name == "working_tasks.json"
    assert pbm.list_backlog_tasks() == []
    assert pbm.list_ready_queue_tasks() == []
    assert pbm.list_completed_tasks() == []


def test_add_task_future_success(pbm: ProjectBoardManager, sample_task_details):
    """Test adding a valid task to the future board (now backlog)."""
    agent_id = "TestAgentAdd"
    success = pbm.add_task_to_backlog(sample_task_details, agent_id)
    assert success is True
    backlog_tasks = pbm.list_backlog_tasks()
    assert len(backlog_tasks) == 1
    assert backlog_tasks[0]["task_id"] == sample_task_details["task_id"]
    assert backlog_tasks[0]["created_by"] == agent_id
    assert backlog_tasks[0]["status"] == "PENDING"
    assert pbm.backlog_path.exists()
    with open(pbm.backlog_path, "r") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["task_id"] == sample_task_details["task_id"]


def test_add_task_duplicate_id(pbm: ProjectBoardManager, sample_task_details):
    """Test adding a task with a duplicate ID fails (to backlog)."""
    agent_id = "TestAgentDup"
    pbm.add_task_to_backlog(sample_task_details, agent_id)
    assert len(pbm.list_backlog_tasks()) == 1

    success_duplicate = pbm.add_task_to_backlog(sample_task_details, agent_id)
    assert success_duplicate is False
    assert len(pbm.list_backlog_tasks()) == 1
    with open(pbm.backlog_path, "r") as f:
        data = json.load(f)
    assert len(data) == 1


def test_add_task_missing_id(pbm: ProjectBoardManager):
    """Test adding a task without a task_id raises validation error."""
    agent_id = "TestAgentInvalid"
    invalid_details = {"description": "Missing ID"}
    with pytest.raises(TaskValidationError):
        pbm.add_task_to_backlog(invalid_details, agent_id)
    assert len(pbm.list_backlog_tasks()) == 0
    assert (
        not pbm.backlog_path.exists()
        or len(json.loads(pbm.backlog_path.read_text())) == 0
    )


def test_add_task_missing_description(pbm: ProjectBoardManager):
    """Test adding a task without a description raises validation error."""
    agent_id = "TestAgentInvalid"
    invalid_details = {"task_id": "INVALID-DESC-001"}
    with pytest.raises(TaskValidationError):
        pbm.add_task_to_backlog(invalid_details, agent_id)
    assert len(pbm.list_backlog_tasks()) == 0
    assert (
        not pbm.backlog_path.exists()
        or len(json.loads(pbm.backlog_path.read_text())) == 0
    )


def test_claim_task_success(pbm: ProjectBoardManager, sample_task_details):
    """Test successfully claiming a PENDING task."""
    agent_id_add = "TestAgentAddClaim"
    agent_id_claim = "TestAgentClaim"
    pbm.add_task_to_backlog(sample_task_details, agent_id_add)
    assert len(pbm.list_backlog_tasks()) == 1
    assert len(pbm.list_ready_queue_tasks()) == 0

    task_id = sample_task_details["task_id"]
    success_claim = pbm.claim_ready_task(task_id, agent_id_claim)

    assert success_claim is True
    assert len(pbm.list_backlog_tasks()) == 0
    assert len(pbm.list_ready_queue_tasks()) == 0
    claimed_task = pbm.list_ready_queue_tasks()[0]
    assert claimed_task["task_id"] == task_id
    assert claimed_task["status"] == "CLAIMED"
    assert claimed_task["assigned_agent"] == agent_id_claim
    assert "timestamp_claimed_utc" in claimed_task
    assert pbm.backlog_path.exists()
    with open(pbm.backlog_path, "r") as f:
        working_data = json.load(f)
    assert len(working_data) == 0
    assert pbm.ready_queue_path.exists()
    with open(pbm.ready_queue_path, "r") as f:
        ready_data = json.load(f)
    assert len(ready_data) == 0


def test_claim_task_not_found(pbm: ProjectBoardManager):
    """Test claiming a task that does not exist raises error."""
    agent_id = "TestAgentClaimFail"
    with pytest.raises(TaskNotFoundError):
        pbm.claim_ready_task("NONEXISTENT-TASK-001", agent_id)


def test_claim_task_wrong_status(pbm: ProjectBoardManager, sample_task_details):
    """Test claiming a task that is not PENDING fails."""
    agent_id_add = "TestAgentAddStatus"
    agent_id_claim = "TestAgentClaimStatus"
    task_id = sample_task_details["task_id"]
    pbm.add_task_to_backlog(sample_task_details, agent_id_add)
    pbm.future_tasks[0]["status"] = "COMPLETED"  # Set invalid status for claiming
    pbm._save_file(pbm.future_tasks_path, pbm.future_tasks)

    success_claim = pbm.claim_ready_task(task_id, agent_id_claim)
    assert success_claim is False
    assert len(pbm.list_backlog_tasks()) == 1
    assert pbm.list_ready_queue_tasks()[0]["status"] == "COMPLETED"


def test_update_task_success(pbm: ProjectBoardManager, sample_task_details):
    """Test successfully updating a task on the working board."""
    agent_id_add = "TestAgentAddUpdate"
    agent_id_claim = "TestAgentClaimUpdate"
    agent_id_update = "TestAgentUpdate"
    task_id = sample_task_details["task_id"]
    pbm.add_task_to_backlog(sample_task_details, agent_id_add)
    pbm.claim_ready_task(task_id, agent_id_claim)
    assert len(pbm.list_ready_queue_tasks()) == 0
    assert len(pbm.list_working_tasks()) == 1
    original_task = pbm.list_working_tasks()[0]
    original_timestamp = original_task["timestamp_updated"]

    updates = {
        "status": "COMPLETED",
        "notes": ["Update note 1", "Update note 2"],
        "progress_summary": "Finished phase 1",
    }
    success_update = pbm.update_task(task_id, updates, agent_id_update)

    assert success_update is True
    assert len(pbm.list_working_tasks()) == 1
    updated_task = pbm.list_working_tasks()[0]
    assert updated_task["task_id"] == task_id
    assert updated_task["status"] == "COMPLETED"
    assert updated_task["notes"] == [
        "Initial task notes.",
        "Update note 1",
        "Update note 2",
    ]
    assert updated_task["progress_summary"] == "Finished phase 1"
    assert updated_task["timestamp_updated"] != original_timestamp
    assert "timestamp_completed_utc" in updated_task

    assert pbm.backlog_path.exists()
    with open(pbm.backlog_path, "r") as f:
        working_data = json.load(f)
    assert len(working_data) == 0
    assert pbm.ready_queue_path.exists()
    with open(pbm.ready_queue_path, "r") as f:
        ready_data = json.load(f)
    assert len(ready_data) == 0


def test_update_task_not_found(pbm: ProjectBoardManager):
    """Test updating a task that does not exist raises TaskNotFoundError."""
    agent_id = "TestAgentUpdateFail"
    with pytest.raises(TaskNotFoundError):
        pbm.update_task("NONEXISTENT-TASK-002", {"status": "FAILED"}, agent_id)


def test_update_task_future_board(pbm: ProjectBoardManager, sample_task_details):
    """Test attempting to update a task still on the future board fails gracefully."""
    agent_id_add = "TestAgentAddUpdateFuture"
    agent_id_update = "TestAgentUpdateFutureFail"
    task_id = sample_task_details["task_id"]
    pbm.add_task_to_backlog(sample_task_details, agent_id_add)
    assert len(pbm.list_backlog_tasks()) == 1

    with pytest.raises(
        TaskNotFoundError
    ):  # Expecting not found as it checks working board
        pbm.update_task(task_id, {"status": "BLOCKED"}, agent_id_update)

    assert len(pbm.list_backlog_tasks()) == 1
    assert pbm.list_ready_queue_tasks()[0]["status"] == "PENDING"  # Original status


def test_delete_task_future_success(pbm: ProjectBoardManager, sample_task_details):
    """Test successfully deleting a task from the future board."""
    agent_id_add = "TestAgentAddDelete"
    agent_id_delete = "TestAgentDeleteFuture"
    task_id = sample_task_details["task_id"]
    pbm.add_task_to_backlog(sample_task_details, agent_id_add)
    assert len(pbm.list_backlog_tasks()) == 1
    assert pbm.backlog_path.exists()

    success_delete = pbm.delete_task(task_id, agent_id_delete, "future")

    assert success_delete is True
    assert len(pbm.list_backlog_tasks()) == 0
    assert (
        not pbm.backlog_path.exists()
        or len(json.loads(pbm.backlog_path.read_text())) == 0
    )


def test_delete_task_working_success(pbm: ProjectBoardManager, sample_task_details):
    """Test successfully deleting a task from the working board."""
    agent_id_add = "TestAgentAddDelWork"
    agent_id_claim = "TestAgentClaimDelWork"
    agent_id_delete = "TestAgentDeleteWork"
    task_id = sample_task_details["task_id"]
    pbm.add_task_to_backlog(sample_task_details, agent_id_add)
    pbm.claim_ready_task(task_id, agent_id_claim)
    assert len(pbm.list_ready_queue_tasks()) == 0
    assert pbm.ready_queue_path.exists()

    success_delete = pbm.delete_task(task_id, agent_id_delete, "working")

    assert success_delete is True
    assert len(pbm.list_ready_queue_tasks()) == 0
    assert (
        not pbm.ready_queue_path.exists()
        or len(json.loads(pbm.ready_queue_path.read_text())) == 0
    )


def test_delete_task_not_found(pbm: ProjectBoardManager):
    """Test deleting a non-existent task raises TaskNotFoundError."""
    agent_id = "TestAgentDeleteNonExistent"
    with pytest.raises(TaskNotFoundError):
        pbm.delete_task("NONEXISTENT-TASK-DELETE", agent_id, "future")
    with pytest.raises(TaskNotFoundError):
        pbm.delete_task("NONEXISTENT-TASK-DELETE", agent_id, "working")


@patch("dreamos.coordination.project_board_manager.ProjectBoardManager._save_file")
def test_claim_task_fail_save_working_rollback(
    mock_save_file, pbm: ProjectBoardManager, sample_task_details
):
    """Test claim_task rollback when saving working_tasks fails."""
    agent_id_add = "TestAgentAddRollback"
    agent_id_claim = "TestAgentClaimRollback"
    task_id = sample_task_details["task_id"]

    pbm.add_task_to_backlog(sample_task_details, agent_id_add)
    assert len(pbm.list_backlog_tasks()) == 1
    original_backlog_list_state = [t.copy() for t in pbm.list_backlog_tasks()]  # noqa: F841

    def save_side_effect(file_path, data):
        if file_path == pbm.future_tasks_path:
            print(f"Mock _save_file SUCCESS for: {file_path}")
            pass
        elif file_path == pbm.ready_queue_path:
            print(f"Mock _save_file FAIL for: {file_path}")
            raise IOError("Simulated disk write error on ready_queue")
        else:
            raise ValueError(f"Unexpected file path in mock_save_file: {file_path}")

    call_count = 0

    def side_effect_wrapper(file_path, data):
        nonlocal call_count
        call_count += 1
        print(f"_save_file call #{call_count} for {file_path.name}")
        if call_count == 1 and file_path == pbm.future_tasks_path:
            save_side_effect(file_path, data)
            assert data[0]["status"] == "CLAIMING"
        elif call_count == 2 and file_path == pbm.ready_queue_path:
            save_side_effect(file_path, data)
        elif call_count == 3 and file_path == pbm.future_tasks_path:
            save_side_effect(file_path, data)
            assert data[0]["status"] == "PENDING"
        else:
            raise AssertionError(
                f"Unexpected call sequence to _save_file: Call {call_count}, Path {file_path.name}"  # noqa: E501
            )

    mock_save_file.side_effect = side_effect_wrapper

    success_claim = pbm.claim_ready_task(task_id, agent_id_claim)

    assert success_claim is False
    assert mock_save_file.call_count >= 2

    pbm.load_boards()
    assert len(pbm.list_backlog_tasks()) == 1, "Task should be back in backlog list"
    assert pbm.list_backlog_tasks()[0]["task_id"] == task_id
    assert (
        pbm.list_backlog_tasks()[0]["status"] == "PENDING"
    ), "Task status should be reverted to PENDING"
    assert (
        len(pbm.list_ready_queue_tasks()) == 0
    ), "Task should not be in ready_queue list"


@patch("dreamos.coordination.project_board_manager.filelock.FileLock")
def test_update_task_lock_timeout(
    MockFileLockClass, pbm: ProjectBoardManager, sample_task_details
):
    """Test update_task raises BoardLockError on lock timeout."""
    agent_id_add = "TestAgentAddLock"
    agent_id_claim = "TestAgentClaimLock"
    agent_id_update = "TestAgentUpdateLock"
    task_id = sample_task_details["task_id"]
    pbm.add_task_to_backlog(sample_task_details, agent_id_add)
    pbm.claim_ready_task(task_id, agent_id_claim)

    mock_lock_instance = mock.MagicMock()
    mock_lock_instance.acquire.side_effect = filelock.Timeout("Simulated lock timeout")  # noqa: F821
    MockFileLockClass.return_value = mock_lock_instance

    updates = {"status": "BLOCKED"}
    with pytest.raises(BoardLockError):
        pbm.update_task(task_id, updates, agent_id_update)

    mock_lock_instance.acquire.assert_called_once()


@patch("dreamos.coordination.project_board_manager.filelock.FileLock")
def test_claim_task_lock_timeout(
    MockFileLockClass, pbm: ProjectBoardManager, sample_task_details
):
    """Test claim_task raises BoardLockError on lock timeout."""
    agent_id_add = "TestAgentAddClaimLock"
    agent_id_claim = "TestAgentClaimLockFail"
    task_id = sample_task_details["task_id"]
    pbm.add_task_to_backlog(sample_task_details, agent_id_add)

    mock_lock_instance = mock.MagicMock()
    mock_lock_instance.acquire.side_effect = filelock.Timeout("Simulated lock timeout")  # noqa: F821
    MockFileLockClass.return_value = mock_lock_instance

    with pytest.raises(BoardLockError):
        pbm.claim_ready_task(task_id, agent_id_claim)

    mock_lock_instance.acquire.assert_called_once()


# --- Tests for Schema Validation ---


# Patch the validate function directly where it's used
@patch("dreamos.coordination.project_board_manager.jsonschema.validate")
def test_add_task_schema_validation_fail(
    mock_jsonschema_validate, pbm: ProjectBoardManager, sample_task_details
):
    """Test adding a task fails when schema validation raises ValidationError."""
    # Configure the mock to raise the specific error PBM expects to catch
    mock_jsonschema_validate.side_effect = jsonschema.exceptions.ValidationError(
        "Simulated schema validation error on add"
    )
    agent_id = "agent-test-add-schema-fail"

    # Expect PBM to catch jsonschema.ValidationError and raise TaskValidationError
    with pytest.raises(TaskValidationError) as excinfo:
        pbm.add_task_to_backlog(sample_task_details, agent_id)

    # Check that our mock was called
    mock_jsonschema_validate.assert_called_once()
    # Check the raised exception message includes the original error message
    assert "Simulated schema validation error on add" in str(excinfo.value)
    assert "failed schema validation" in str(excinfo.value)


@patch("dreamos.coordination.project_board_manager.jsonschema.validate")
def test_update_task_schema_validation_success(
    mock_jsonschema_validate,
    pbm_with_real_schema: ProjectBoardManager,
    sample_task_details,
):
    """Test update_working_task passes schema validation with valid data."""
    pbm = pbm_with_real_schema  # Use the renamed fixture
    task_id = sample_task_details["task_id"]

    # Add initial task (assume valid or mock validation)
    with patch.object(pbm, "_validate_task") as mock_validate_initial:
        pbm.add_task_to_board("ready", sample_task_details)

    # Valid updates
    updates = {"notes": "Updated notes", "priority": "LOW"}

    # Mock the jsonschema.validate call itself to just pass (no exception)
    mock_jsonschema_validate.return_value = None

    try:
        pbm.update_working_task(task_id, updates)
    except TaskValidationError as e:
        pytest.fail(f"Schema validation failed unexpectedly: {e}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during update: {e}")

    # Assert jsonschema.validate was called (or however validation is triggered)
    mock_jsonschema_validate.assert_called_once()
    call_args = mock_jsonschema_validate.call_args[0]
    assert call_args[0]["notes"] == "Updated notes"  # Check instance being validated


@patch("dreamos.coordination.project_board_manager.jsonschema.validate")
def test_update_task_schema_validation_fail(
    mock_jsonschema_validate,
    pbm_with_real_schema: ProjectBoardManager,
    sample_task_details,
):
    """Test update_working_task raises TaskValidationError on schema failure."""
    pbm = pbm_with_real_schema  # Use the renamed fixture
    task_id = sample_task_details["task_id"]

    # Add initial task
    with patch.object(pbm, "_validate_task") as mock_validate_initial:
        pbm.add_task_to_board("ready", sample_task_details)

    # Invalid updates (e.g., wrong type for priority)
    updates = {"priority": {"level": "VERY LOW"}}  # Example invalid data

    # Mock jsonschema.validate to raise a validation error
    mock_jsonschema_validate.side_effect = jsonschema.ValidationError(
        "Mock validation error"
    )

    with pytest.raises(
        TaskValidationError, match=r"Task data failed schema validation"
    ):
        pbm.update_working_task(task_id, updates)

    # Assert jsonschema.validate was called
    mock_jsonschema_validate.assert_called_once()


# --- Tests for Schema Loading ---


def test_load_schema_success(pbm: ProjectBoardManager):
    """Test that the schema is loaded correctly on initialization."""
    # The pbm fixture ensures PBM is initialized
    # with a path to a *real* schema file (handled by the fixture setup).
    # We just need to check if the schema object is populated.
    assert pbm._task_schema is not None
    assert isinstance(pbm._task_schema, dict)
    assert "$schema" in pbm._task_schema  # Check for a key expected in the schema


def test_load_schema_not_found(
    pbm: ProjectBoardManager,
):
    """Test that _load_schema returns None if the schema file is not found."""
    schema_path = (
        pbm.config.paths.project_root
        / "src"
        / "dreamos"
        / "coordination"
        / "tasks"
        / "task-schema.json"
    )
    assert not schema_path.exists()

    loaded_schema = pbm._load_schema()
    assert loaded_schema is None
    assert pbm._task_schema is None


def test_load_schema_invalid_json(temp_test_dir):
    """Test _load_schema handles invalid JSON gracefully."""
    schema_dir = temp_test_dir / "src" / "dreamos" / "coordination" / "tasks"
    schema_dir.mkdir(parents=True, exist_ok=True)
    schema_path = schema_dir / "task-schema.json"
    with open(schema_path, "w") as f:
        f.write('{"invalid_json": ,}')

    manager = ProjectBoardManager(project_root=temp_test_dir)
    assert manager._task_schema is None


# --- Tests for claim_ready_task ---
def test_claim_ready_task_success(
    self, pbm: ProjectBoardManager, sample_task_1: dict, fs
):
    """Test claiming a task from the ready queue."""
    agent_id = "agent-test-claim"
    fs.create_file(pbm.ready_queue_path, contents=json.dumps([sample_task_1]))

    claimed = pbm.claim_ready_task(sample_task_1["task_id"], agent_id)
    assert claimed is True

    with open(pbm.ready_queue_path, "r") as f:
        ready_data = json.load(f)
    assert len(ready_data) == 0

    assert fs.exists(pbm.working_tasks_path)
    with open(pbm.working_tasks_path, "r") as f:
        working_data = json.load(f)
    assert len(working_data) == 1
    task_in_working = working_data[0]
    assert task_in_working["task_id"] == sample_task_1["task_id"]
    assert task_in_working["status"] == "CLAIMED"
    assert task_in_working["claimed_by"] == agent_id
    assert task_in_working["assigned_agent"] == agent_id
    assert "timestamp_claimed_utc" in task_in_working


def test_claim_task_not_in_ready(self, pbm: ProjectBoardManager, fs):
    """Test claiming a task not in the ready queue."""
    fs.create_file(pbm.ready_queue_path, contents="[]")
    agent_id = "agent-test-claim-fail"

    with pytest.raises(TaskNotFoundError):
        pbm.claim_ready_task("nonexistent-task-id", agent_id)
    assert not fs.exists(pbm.working_tasks_path)


# --- Tests for move_task_to_completed ---
def test_move_task_to_completed_success(
    self, pbm: ProjectBoardManager, sample_task_1: dict, fs
):
    """Test moving a task from working to completed."""
    agent_id = "agent-test-complete"
    working_task = sample_task_1.copy()
    working_task["status"] = "IN_PROGRESS"
    working_task["claimed_by"] = agent_id
    working_task["assigned_agent"] = agent_id
    fs.create_file(pbm.working_tasks_path, contents=json.dumps([working_task]))

    final_updates = {
        "status": "COMPLETED",
        "completion_summary": "Task finished successfully.",
        "completed_by": agent_id,
    }
    moved = pbm.move_task_to_completed(working_task["task_id"], final_updates)
    assert moved is True

    with open(pbm.working_tasks_path, "r") as f:
        working_data = json.load(f)
    assert len(working_data) == 0

    assert fs.exists(pbm.completed_tasks_path)
    with open(pbm.completed_tasks_path, "r") as f:
        completed_data = json.load(f)
    assert len(completed_data) == 1
    task_in_completed = completed_data[0]
    assert task_in_completed["task_id"] == working_task["task_id"]
    assert task_in_completed["status"] == "COMPLETED"
    assert (
        task_in_completed["completion_summary"] == final_updates["completion_summary"]
    )
    assert task_in_completed["completed_by"] == agent_id
    assert "timestamp_completed_utc" in task_in_completed
    assert "timestamp_updated" in task_in_completed


def test_move_task_to_completed_not_found(self, pbm: ProjectBoardManager, fs):
    """Test moving a task not in the working board."""
    fs.create_file(pbm.working_tasks_path, contents="[]")
    agent_id = "agent-test-complete-fail"
    final_updates = {"status": "COMPLETED", "completed_by": agent_id}

    with pytest.raises(TaskNotFoundError):
        pbm.move_task_to_completed("nonexistent-task-id", final_updates)
    assert not fs.exists(pbm.completed_tasks_path)


# --- Tests for get_task ---
def test_get_task_success(
    self, pbm: ProjectBoardManager, sample_task_1: dict, sample_task_2: dict, fs
):
    """Test getting a task from various boards."""
    task1_working = sample_task_1.copy()
    task1_working["status"] = "CLAIMED"
    task2_ready = sample_task_2.copy()
    fs.create_file(pbm.working_tasks_path, contents=json.dumps([task1_working]))
    fs.create_file(pbm.ready_queue_path, contents=json.dumps([task2_ready]))

    retrieved_task1 = pbm.get_task(sample_task_1["task_id"], board="working")
    assert retrieved_task1 is not None
    assert retrieved_task1["task_id"] == sample_task_1["task_id"]

    retrieved_task2 = pbm.get_task(sample_task_2["task_id"], board="ready")
    assert retrieved_task2 is not None
    assert retrieved_task2["task_id"] == sample_task_2["task_id"]

    retrieved_task1_any = pbm.get_task(sample_task_1["task_id"], board="any")
    assert retrieved_task1_any is not None
    assert retrieved_task1_any["task_id"] == sample_task_1["task_id"]
    retrieved_task2_any = pbm.get_task(sample_task_2["task_id"], board="any")
    assert retrieved_task2_any is not None
    assert retrieved_task2_any["task_id"] == sample_task_2["task_id"]


def test_get_task_not_found(self, pbm: ProjectBoardManager, fs):
    """Test getting a non-existent task."""
    fs.create_file(pbm.backlog_path, contents="[]")
    fs.create_file(pbm.ready_queue_path, contents="[]")
    fs.create_file(pbm.working_tasks_path, contents="[]")
    fs.create_file(pbm.completed_tasks_path, contents="[]")

    task = pbm.get_task("nonexistent-task")
    assert task is None


# --- New Test Class for promote_task_to_ready ---
class TestPromoteTaskToReady:
    def test_promote_success(self, pbm: ProjectBoardManager, sample_task_1: dict, fs):
        """Test successfully promoting a task from backlog to ready."""
        backlog_tasks = [sample_task_1]
        fs.create_file(pbm.backlog_path, contents=json.dumps(backlog_tasks))
        fs.create_file(pbm.ready_queue_path, contents="[]")

        result = pbm.promote_task_to_ready(sample_task_1["task_id"])

        assert result is True
        # Verify backlog is now empty
        final_backlog = pbm._load_backlog()
        assert final_backlog == []
        # Verify ready queue has the task
        final_ready = pbm._load_ready_queue()
        assert len(final_ready) == 1
        assert final_ready[0]["task_id"] == sample_task_1["task_id"]
        assert final_ready[0]["status"] == "READY"

    def test_promote_not_found(self, pbm: ProjectBoardManager, fs):
        """Test promoting a task that doesn't exist in the backlog."""
        fs.create_file(pbm.backlog_path, contents="[]")
        fs.create_file(pbm.ready_queue_path, contents="[]")

        with pytest.raises(TaskNotFoundError):
            pbm.promote_task_to_ready("nonexistent-task")

        # Verify boards remain empty
        assert pbm._load_backlog() == []
        assert pbm._load_ready_queue() == []

    def test_promote_already_ready(
        self, pbm: ProjectBoardManager, sample_task_1: dict, fs
    ):
        """Test promoting a task already in the ready queue (should fail)."""
        sample_task_1["status"] = "READY"
        ready_tasks = [sample_task_1]
        fs.create_file(pbm.backlog_path, contents="[]")
        fs.create_file(pbm.ready_queue_path, contents=json.dumps(ready_tasks))

        with pytest.raises(ProjectBoardError) as excinfo:
            pbm.promote_task_to_ready(sample_task_1["task_id"])
        assert "Cannot promote task" in str(excinfo.value)
        assert "already in ready queue" in str(excinfo.value)

        # Verify boards are unchanged
        assert pbm._load_backlog() == []
        assert (
            pbm._load_ready_queue() == ready_tasks
        )  # Should still contain the original task

    def test_promote_working_task(
        self, pbm: ProjectBoardManager, sample_task_1: dict, fs
    ):
        """Test promoting a task that is currently working (should fail)."""
        sample_task_1["status"] = "WORKING"
        working_tasks = [sample_task_1]
        fs.create_file(pbm.backlog_path, contents="[]")
        fs.create_file(pbm.ready_queue_path, contents="[]")
        fs.create_file(pbm.working_tasks_path, contents=json.dumps(working_tasks))

        with pytest.raises(ProjectBoardError) as excinfo:
            pbm.promote_task_to_ready(sample_task_1["task_id"])
        assert "Cannot promote task" in str(excinfo.value)
        assert "found in working tasks" in str(excinfo.value)

        # Verify boards are unchanged
        assert pbm._load_backlog() == []
        assert pbm._load_ready_queue() == []
        assert pbm._load_working_tasks() == working_tasks

    def test_promote_completed_task(
        self, pbm: ProjectBoardManager, sample_task_1: dict, fs
    ):
        """Test promoting a task that is already completed (should fail)."""
        sample_task_1["status"] = "COMPLETED"
        completed_tasks = [sample_task_1]
        fs.create_file(pbm.backlog_path, contents="[]")
        fs.create_file(pbm.ready_queue_path, contents="[]")
        fs.create_file(pbm.completed_tasks_path, contents=json.dumps(completed_tasks))

        with pytest.raises(ProjectBoardError) as excinfo:
            pbm.promote_task_to_ready(sample_task_1["task_id"])
        assert "Cannot promote task" in str(excinfo.value)
        assert "found in completed tasks" in str(excinfo.value)

        # Verify boards are unchanged
        assert pbm._load_backlog() == []
        assert pbm._load_ready_queue() == []
        assert pbm._load_completed_tasks() == completed_tasks


# --- End New Test Class ---


# --- New Test Class for _create_from_cli_args ---
# Requires mocking AppConfig loading or providing a mock config
class TestCreateFromCliArgs:
    @patch("dreamos.coordination.project_board_manager.AppConfig.load")
    def test_create_from_cli_basic(self, mock_load_config, mock_app_config):
        """Test basic creation using CLI args."""
        # Configure the mock AppConfig returned by load
        mock_load_config.return_value = mock_app_config

        args = argparse.Namespace(
            # Define attributes expected by _create_from_cli_args if any
            # e.g., config_path=None, lock_timeout=None
            # If it only relies on AppConfig.load(), this might be simple
        )

        pbm_instance = ProjectBoardManager._create_from_cli_args(args)

        assert isinstance(pbm_instance, ProjectBoardManager)
        assert pbm_instance.config == mock_app_config
        # Check if lock_timeout was potentially overridden by args (if applicable)
        # assert pbm_instance.lock_timeout == expected_timeout
        mock_load_config.assert_called_once()  # Verify config loading

    @patch("dreamos.coordination.project_board_manager.AppConfig.load")
    def test_create_from_cli_with_overrides(self, mock_load_config, mock_app_config):
        """Test creation with CLI args overriding defaults (if applicable)."""
        # This test depends heavily on what _create_from_cli_args actually *does*
        # with the args object. If it passes args to AppConfig.load or overrides
        # PBM attributes directly, tests need to reflect that.
        # Example: Assuming it could override lock_timeout

        mock_load_config.return_value = mock_app_config
        custom_timeout = 30

        args = argparse.Namespace(
            lock_timeout=custom_timeout  # Example override
        )

        pbm_instance = ProjectBoardManager._create_from_cli_args(args)

        assert isinstance(pbm_instance, ProjectBoardManager)
        # This assertion depends on implementation detail:
        # Does _create_from_cli_args pass timeout to PBM init?
        # assert pbm_instance.lock_timeout == custom_timeout
        mock_load_config.assert_called_once()


# --- End New Test Class ---

# Note: Removed erroneous __main__ block from previous edits
# if __name__ == '__main__':
#     unittest.main()
