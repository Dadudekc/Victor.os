# tests/coordination/test_project_board_manager.py

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY

import pytest

# E402 fixes: Move project imports after sys.path manipulation if needed
# (Assuming tests/ directory structure allows direct import here)
from dreamos.core.coordination.agent_bus import AgentBus, BaseEvent, EventType
# F811/F401 fixes for errors:
# from dreamos.core.errors import BoardLockError, TaskNotFoundError, TaskValidationError, ProjectBoardError
from dreamos.core.errors import (
    ProjectBoardError,
    BoardLockError,
    TaskNotFoundError,
    TaskValidationError,
) # Re-import specifically where needed or fix original definitions
from dreamos.core.coordination.task_nexus import (
    ProjectBoardManager, # Keep PBM import
    TaskStatusUpdatePayload, # Keep payload import
    TaskSchema # Keep schema import
)
# Assuming TaskSchema is needed for validation or task creation
# from dreamos.core.tasks.schema import TaskSchema

# Add src directory to path for imports
SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

# Module to test
from dreamos.coordination.project_board_manager import (
    BoardLockError,
    ProjectBoardManager,
    TaskNotFoundError,
    TaskValidationError,
)
from dreamos.core.config import AppConfig, PathsConfig
from dreamos.core.errors import (
    BoardLockError,
    ProjectBoardError,
    TaskNotFoundError,
    TaskValidationError,
)


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
        "timestamp_created_utc": time.time(),
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
        "timestamp_created_utc": time.time(),
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


# Fixture for a PBM instance configured for the temp directory
@pytest.fixture
def pbm_instance(mock_app_config: AppConfig, fs):
    """Fixture providing a PBM instance using mock config (DEPRECATED). Use 'pbm' fixture instead."""
    # EDIT START: Use the AppConfig-based fixture 'pbm' for consistency.
    # This fixture is kept for backward compatibility during refactor but should be removed.
    # All tests using this should be updated to use the 'pbm' fixture.
    print(
        "WARNING: Using deprecated fixture 'pbm_instance'. Refactor test to use 'pbm'."
    )

    # Re-implement using AppConfig for now to avoid immediate failure
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
    with patch("dreamos.coordination.project_board_manager.FILELOCK_AVAILABLE", False):
        manager = ProjectBoardManager(config=mock_app_config)
    return manager


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
def pbm_instance_with_real_schema(temp_test_dir):
    """Instance of PBM specifically for testing schema loading."""
    # Create a dummy schema file in the expected location within the temp dir
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
    schema_dir = temp_test_dir / "src" / "dreamos" / "coordination" / "tasks"
    schema_dir.mkdir(parents=True, exist_ok=True)
    schema_path = schema_dir / "task-schema.json"
    with open(schema_path, "w") as f:
        json.dump(schema_content, f)

    # Now instantiate PBM pointing to this temp project root
    future_path = "runtime/agent_comms/project_boards/future_tasks_schema_load.json"
    working_path = "runtime/agent_comms/project_boards/working_tasks_schema_load.json"
    manager = ProjectBoardManager(
        future_tasks_path=future_path,
        working_tasks_path=working_path,
        project_root=temp_test_dir,
    )
    return manager


# --- Test Cases ---


def test_pbm_initialization(pbm_instance, temp_test_dir):
    """Test if ProjectBoardManager initializes correctly."""
    assert pbm_instance is not None
    assert pbm_instance.project_root == temp_test_dir.resolve()
    assert pbm_instance.future_tasks_path.name == "future_tasks.json"
    assert pbm_instance.working_tasks_path.name == "working_tasks.json"
    assert pbm_instance.future_tasks == []
    assert pbm_instance.working_tasks == []


def test_add_task_future_success(pbm_instance, sample_task_details):
    """Test adding a valid task to the future board."""
    agent_id = "TestAgentAdd"
    success = pbm_instance.add_task(
        sample_task_details, agent_id, target_board="future"
    )
    assert success is True
    assert len(pbm_instance.future_tasks) == 1
    assert pbm_instance.future_tasks[0]["task_id"] == sample_task_details["task_id"]
    assert pbm_instance.future_tasks[0]["created_by"] == agent_id
    assert pbm_instance.future_tasks[0]["status"] == "PENDING"
    # Verify file content after save (requires reading the file)
    assert pbm_instance.future_tasks_path.exists()
    with open(pbm_instance.future_tasks_path, "r") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["task_id"] == sample_task_details["task_id"]


def test_add_task_working_success(pbm_instance, sample_task_details):
    """Test adding a valid task to the working board."""
    agent_id = "TestAgentAddWork"
    details = sample_task_details.copy()
    details["task_id"] = "TEST-TASK-WORK-001"
    success = pbm_instance.add_task(details, agent_id, target_board="working")
    assert success is True
    assert len(pbm_instance.working_tasks) == 1
    assert pbm_instance.working_tasks[0]["task_id"] == details["task_id"]
    assert pbm_instance.working_tasks[0]["created_by"] == agent_id
    # Verify file content
    assert pbm_instance.working_tasks_path.exists()
    with open(pbm_instance.working_tasks_path, "r") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["task_id"] == details["task_id"]


def test_add_task_duplicate_id(pbm_instance, sample_task_details):
    """Test adding a task with a duplicate ID fails."""
    agent_id = "TestAgentDup"
    # Add the task once
    pbm_instance.add_task(sample_task_details, agent_id, target_board="future")
    assert len(pbm_instance.future_tasks) == 1

    # Try adding again with the same ID
    success_duplicate = pbm_instance.add_task(
        sample_task_details, agent_id, target_board="future"
    )
    assert success_duplicate is False
    # Ensure only one task remains
    assert len(pbm_instance.future_tasks) == 1
    # Verify file content reflects only one task
    with open(pbm_instance.future_tasks_path, "r") as f:
        data = json.load(f)
    assert len(data) == 1


def test_add_task_missing_id(pbm_instance):
    """Test adding a task without a task_id raises validation error."""
    agent_id = "TestAgentInvalid"
    invalid_details = {"description": "Missing ID"}
    with pytest.raises(TaskValidationError):
        pbm_instance.add_task(invalid_details, agent_id, target_board="future")
    assert len(pbm_instance.future_tasks) == 0  # Ensure no task was added
    assert (
        not pbm_instance.future_tasks_path.exists()
    )  # File shouldn't be created on validation error


def test_add_task_missing_description(pbm_instance):
    """Test adding a task without a description raises validation error."""
    agent_id = "TestAgentInvalid"
    invalid_details = {"task_id": "INVALID-DESC-001"}
    with pytest.raises(TaskValidationError):
        pbm_instance.add_task(invalid_details, agent_id, target_board="future")
    assert len(pbm_instance.future_tasks) == 0
    assert not pbm_instance.future_tasks_path.exists()


def test_claim_task_success(pbm_instance, sample_task_details):
    """Test successfully claiming a PENDING task."""
    agent_id_add = "TestAgentAddClaim"
    agent_id_claim = "TestAgentClaim"
    # Add a task to future board first
    pbm_instance.add_task(sample_task_details, agent_id_add, "future")
    assert len(pbm_instance.future_tasks) == 1
    assert len(pbm_instance.working_tasks) == 0

    # Claim the task
    task_id = sample_task_details["task_id"]
    success_claim = pbm_instance.claim_task(task_id, agent_id_claim)

    assert success_claim is True
    # Verify state after claim
    assert len(pbm_instance.future_tasks) == 0
    assert len(pbm_instance.working_tasks) == 1
    claimed_task = pbm_instance.working_tasks[0]
    assert claimed_task["task_id"] == task_id
    assert claimed_task["status"] == "WORKING"
    assert claimed_task["assigned_agent"] == agent_id_claim
    assert "timestamp_claimed_utc" in claimed_task
    # Verify file contents
    assert (
        not pbm_instance.future_tasks_path.exists()
        or len(json.loads(pbm_instance.future_tasks_path.read_text())) == 0
    )
    assert pbm_instance.working_tasks_path.exists()
    with open(pbm_instance.working_tasks_path, "r") as f:
        working_data = json.load(f)
    assert len(working_data) == 1
    assert working_data[0]["task_id"] == task_id
    assert working_data[0]["status"] == "WORKING"
    assert working_data[0]["assigned_agent"] == agent_id_claim


def test_claim_task_not_found(pbm_instance):
    """Test claiming a task that does not exist raises error."""
    agent_id = "TestAgentClaimFail"
    with pytest.raises(TaskNotFoundError):
        pbm_instance.claim_task("NONEXISTENT-TASK-001", agent_id)


def test_claim_task_wrong_status(pbm_instance, sample_task_details):
    """Test claiming a task that is not PENDING fails."""
    agent_id_add = "TestAgentAddStatus"
    agent_id_claim = "TestAgentClaimStatus"
    task_id = sample_task_details["task_id"]
    # Add task and immediately update its status (requires update_task)
    pbm_instance.add_task(sample_task_details, agent_id_add, "future")
    # Need to manually modify the in-memory state and save for this test setup
    # Or implement update_task tests first
    pbm_instance.future_tasks[0][
        "status"
    ] = "COMPLETED"  # Set invalid status for claiming
    pbm_instance._save_file(pbm_instance.future_tasks_path, pbm_instance.future_tasks)

    success_claim = pbm_instance.claim_task(task_id, agent_id_claim)
    assert success_claim is False
    # Verify task remains on future board with original (modified) status
    assert len(pbm_instance.future_tasks) == 1
    assert pbm_instance.future_tasks[0]["status"] == "COMPLETED"
    assert len(pbm_instance.working_tasks) == 0


def test_update_task_success(pbm_instance, sample_task_details):
    """Test successfully updating a task on the working board."""
    agent_id_add = "TestAgentAddUpdate"
    agent_id_claim = "TestAgentClaimUpdate"
    agent_id_update = "TestAgentUpdate"
    task_id = sample_task_details["task_id"]
    # Add and claim the task first
    pbm_instance.add_task(sample_task_details, agent_id_add, "future")
    pbm_instance.claim_task(task_id, agent_id_claim)
    assert len(pbm_instance.working_tasks) == 1
    original_task = pbm_instance.working_tasks[0]
    original_timestamp = original_task["timestamp_updated"]

    # Update the task
    updates = {
        "status": "COMPLETED",
        "notes": ["Update note 1", "Update note 2"],
        "progress_summary": "Finished phase 1",
    }
    success_update = pbm_instance.update_task(task_id, updates, agent_id_update)

    assert success_update is True
    assert len(pbm_instance.working_tasks) == 1
    updated_task = pbm_instance.working_tasks[0]
    assert updated_task["task_id"] == task_id
    assert updated_task["status"] == "COMPLETED"
    assert updated_task["notes"] == [
        "Initial task notes.",
        "Update note 1",
        "Update note 2",
    ]  # Check notes append
    assert updated_task["progress_summary"] == "Finished phase 1"
    assert updated_task["timestamp_updated"] != original_timestamp
    assert "timestamp_completed_utc" in updated_task  # Added on status change

    # Verify file contents
    assert pbm_instance.working_tasks_path.exists()
    with open(pbm_instance.working_tasks_path, "r") as f:
        working_data = json.load(f)
    assert len(working_data) == 1
    assert working_data[0]["task_id"] == task_id
    assert working_data[0]["status"] == "COMPLETED"
    assert working_data[0]["notes"] == [
        "Initial task notes.",
        "Update note 1",
        "Update note 2",
    ]


def test_update_task_not_found(pbm_instance):
    """Test updating a task that does not exist raises TaskNotFoundError."""
    agent_id = "TestAgentUpdateFail"
    with pytest.raises(TaskNotFoundError):
        pbm_instance.update_task("NONEXISTENT-TASK-002", {"status": "FAILED"}, agent_id)


def test_update_task_future_board(pbm_instance, sample_task_details):
    """Test attempting to update a task still on the future board fails gracefully."""
    # Note: Current implementation only looks for task on working board for updates.
    # If this behaviour changes, this test needs adjustment.
    agent_id_add = "TestAgentAddUpdateFuture"
    agent_id_update = "TestAgentUpdateFutureFail"
    task_id = sample_task_details["task_id"]
    # Add task to future board
    pbm_instance.add_task(sample_task_details, agent_id_add, "future")
    assert len(pbm_instance.future_tasks) == 1

    with pytest.raises(
        TaskNotFoundError
    ):  # Expecting not found as it checks working board
        pbm_instance.update_task(task_id, {"status": "BLOCKED"}, agent_id_update)

    # Verify task is unchanged on future board
    assert len(pbm_instance.future_tasks) == 1
    assert pbm_instance.future_tasks[0]["status"] == "PENDING"  # Original status


def test_delete_task_future_success(pbm_instance, sample_task_details):
    """Test successfully deleting a task from the future board."""
    agent_id_add = "TestAgentAddDelete"
    agent_id_delete = "TestAgentDeleteFuture"
    task_id = sample_task_details["task_id"]
    # Add task to future board
    pbm_instance.add_task(sample_task_details, agent_id_add, "future")
    assert len(pbm_instance.future_tasks) == 1
    assert pbm_instance.future_tasks_path.exists()

    # Delete the task
    success_delete = pbm_instance.delete_task(task_id, agent_id_delete, "future")

    assert success_delete is True
    assert len(pbm_instance.future_tasks) == 0
    # Verify file is empty or non-existent after deletion
    assert (
        not pbm_instance.future_tasks_path.exists()
        or len(json.loads(pbm_instance.future_tasks_path.read_text())) == 0
    )


def test_delete_task_working_success(pbm_instance, sample_task_details):
    """Test successfully deleting a task from the working board."""
    agent_id_add = "TestAgentAddDelWork"
    agent_id_claim = "TestAgentClaimDelWork"
    agent_id_delete = "TestAgentDeleteWork"
    task_id = sample_task_details["task_id"]
    # Add and claim task
    pbm_instance.add_task(sample_task_details, agent_id_add, "future")
    pbm_instance.claim_task(task_id, agent_id_claim)
    assert len(pbm_instance.working_tasks) == 1
    assert pbm_instance.working_tasks_path.exists()

    # Delete the task from working board
    success_delete = pbm_instance.delete_task(task_id, agent_id_delete, "working")

    assert success_delete is True
    assert len(pbm_instance.working_tasks) == 0
    assert (
        not pbm_instance.working_tasks_path.exists()
        or len(json.loads(pbm_instance.working_tasks_path.read_text())) == 0
    )


def test_delete_task_not_found(pbm_instance):
    """Test deleting a non-existent task raises TaskNotFoundError."""
    agent_id = "TestAgentDeleteNonExistent"
    with pytest.raises(TaskNotFoundError):
        pbm_instance.delete_task("NONEXISTENT-TASK-DELETE", agent_id, "future")
    with pytest.raises(TaskNotFoundError):
        pbm_instance.delete_task("NONEXISTENT-TASK-DELETE", agent_id, "working")


@patch("dreamos.coordination.project_board_manager.ProjectBoardManager._save_file")
def test_claim_task_fail_save_working_rollback(
    mock_save_file, pbm_instance, sample_task_details
):
    """Test claim_task rollback when saving working_tasks fails."""
    agent_id_add = "TestAgentAddRollback"
    agent_id_claim = "TestAgentClaimRollback"
    task_id = sample_task_details["task_id"]

    # Add the task to future board
    pbm_instance.add_task(sample_task_details, agent_id_add, "future")
    assert len(pbm_instance.future_tasks) == 1
    original_future_list_state = [t.copy() for t in pbm_instance.future_tasks]

    # Configure mock _save_file:
    # 1st call (future_tasks with CLAIMING status) -> Success
    # 2nd call (working_tasks with new task) -> Fail (IOError)
    # 3rd call (future_tasks reverting status) -> Success (implicitly checked by verifying final state)
    def save_side_effect(file_path, data):
        if file_path == pbm_instance.future_tasks_path:
            # Allow first save (status: CLAIMING) and third save (rollback)
            print(f"Mock _save_file SUCCESS for: {file_path}")
            # To properly simulate, we should actually write the intermediate state
            # For simplicity, we'll just allow it to pass and check the PBM state later
            pass
        elif file_path == pbm_instance.working_tasks_path:
            print(f"Mock _save_file FAIL for: {file_path}")
            raise IOError("Simulated disk write error on working_tasks")
        else:
            raise ValueError(f"Unexpected file path in mock_save_file: {file_path}")

    # Apply the side effect
    # We need to track calls carefully
    call_count = 0

    def side_effect_wrapper(file_path, data):
        nonlocal call_count
        call_count += 1
        print(f"_save_file call #{call_count} for {file_path.name}")
        if call_count == 1 and file_path == pbm_instance.future_tasks_path:
            # First call: Save future with 'CLAIMING' - Success
            save_side_effect(file_path, data)
            # Verify the state written *would* have been CLAIMING
            assert data[0]["status"] == "CLAIMING"
        elif call_count == 2 and file_path == pbm_instance.working_tasks_path:
            # Second call: Save working - Fail
            save_side_effect(file_path, data)
        elif call_count == 3 and file_path == pbm_instance.future_tasks_path:
            # Third call: Rollback future - Success
            save_side_effect(file_path, data)
            # Verify the state written *would* be reverted
            assert data[0]["status"] == "PENDING"
        else:
            raise AssertionError(
                f"Unexpected call sequence to _save_file: Call {call_count}, Path {file_path.name}"
            )

    mock_save_file.side_effect = side_effect_wrapper

    # Attempt to claim the task - expected to fail overall due to IOError
    success_claim = pbm_instance.claim_task(task_id, agent_id_claim)

    assert success_claim is False
    assert (
        mock_save_file.call_count >= 2
    )  # Should attempt future(CLAIMING), working(FAIL), [future(ROLLBACK)]
    # Depending on exact execution path, rollback might happen in finally block or separate call
    # Check the final state is correct is more robust.

    # Verify final state: Task should be back in future_tasks with original status
    # Need to manually reload or trust the rollback logic updated the instance state
    pbm_instance.load_boards()  # Reload from simulated disk state (requires _save_file mock to simulate writes or test reads)
    # ---- OR ---- Check in-memory state *if* rollback updates it correctly:
    assert (
        len(pbm_instance.future_tasks) == 1
    ), "Task should be back in future_tasks list"
    assert pbm_instance.future_tasks[0]["task_id"] == task_id
    assert (
        pbm_instance.future_tasks[0]["status"] == "PENDING"
    ), "Task status should be reverted to PENDING"
    assert (
        len(pbm_instance.working_tasks) == 0
    ), "Task should not be in working_tasks list"


@patch("dreamos.coordination.project_board_manager.filelock.FileLock")
def test_update_task_lock_timeout(MockFileLockClass, pbm_instance, sample_task_details):
    """Test update_task raises BoardLockError on lock timeout."""
    agent_id_add = "TestAgentAddLock"
    agent_id_claim = "TestAgentClaimLock"
    agent_id_update = "TestAgentUpdateLock"
    task_id = sample_task_details["task_id"]
    # Add and claim the task first
    pbm_instance.add_task(sample_task_details, agent_id_add, "future")
    pbm_instance.claim_task(task_id, agent_id_claim)

    # Configure mock lock to raise Timeout
    mock_lock_instance = mock.MagicMock()
    mock_lock_instance.acquire.side_effect = filelock.Timeout("Simulated lock timeout")
    MockFileLockClass.return_value = mock_lock_instance

    updates = {"status": "BLOCKED"}
    with pytest.raises(BoardLockError):
        pbm_instance.update_task(task_id, updates, agent_id_update)

    # Ensure acquire was called
    mock_lock_instance.acquire.assert_called_once()
    # Ensure release was not called if acquire failed (depends on implementation, but typically yes)
    # mock_lock_instance.release.assert_not_called()


@patch("dreamos.coordination.project_board_manager.filelock.FileLock")
def test_claim_task_lock_timeout(MockFileLockClass, pbm_instance, sample_task_details):
    """Test claim_task raises BoardLockError on lock timeout."""
    agent_id_add = "TestAgentAddClaimLock"
    agent_id_claim = "TestAgentClaimLockFail"
    task_id = sample_task_details["task_id"]
    pbm_instance.add_task(sample_task_details, agent_id_add, "future")

    # Configure mock lock to raise Timeout
    mock_lock_instance = mock.MagicMock()
    # Simulate timeout on acquiring either lock (future or working)
    mock_lock_instance.acquire.side_effect = filelock.Timeout("Simulated lock timeout")
    MockFileLockClass.return_value = mock_lock_instance

    with pytest.raises(BoardLockError):
        pbm_instance.claim_task(task_id, agent_id_claim)

    mock_lock_instance.acquire.assert_called_once()  # Should fail on first lock acquire


def test_add_task_schema_validation_fail(mock_pbm_with_schema, sample_task_details):
    """Test add_task fails if schema validation fails."""
    agent_id = "TestAgentAddSchemaFail"
    # Configure mock validate to raise error
    mock_pbm_with_schema._mock_jsonschema_validate.side_effect = (
        jsonschema.ValidationError("Simulated schema validation error")
    )

    # Attempt to add the task
    # Note: add_task currently doesn't implement schema validation, this test anticipates it
    # Assuming validation *will be* added to add_task
    with pytest.raises(TaskValidationError) as excinfo:
        mock_pbm_with_schema.add_task(sample_task_details, agent_id, "future")
    assert "failed schema validation" in str(excinfo.value).lower()

    mock_pbm_with_schema._mock_jsonschema_validate.assert_called_once()
    assert len(mock_pbm_with_schema.future_tasks) == 0


def test_update_task_schema_validation_success(
    mock_pbm_with_schema, sample_task_details
):
    """Test update_task succeeds when schema validation passes."""
    agent_id_add = "TestAgentAddSchemaOk"
    agent_id_claim = "TestAgentClaimSchemaOk"
    agent_id_update = "TestAgentUpdateSchemaOk"
    task_id = sample_task_details["task_id"]
    # Add and claim the task
    # Need to use a PBM *without* the schema mock for setup
    setup_pbm = ProjectBoardManager(project_root=mock_pbm_with_schema.project_root)
    setup_pbm.add_task(sample_task_details, agent_id_add, "future")
    setup_pbm.claim_task(task_id, agent_id_claim)

    # Configure mock validate to succeed (default behavior of MagicMock)
    mock_pbm_with_schema._mock_jsonschema_validate.side_effect = None

    updates = {"status": "REVIEWING"}
    success = mock_pbm_with_schema.update_task(task_id, updates, agent_id_update)

    assert success is True
    mock_pbm_with_schema._mock_jsonschema_validate.assert_called_once()
    assert mock_pbm_with_schema.working_tasks[0]["status"] == "REVIEWING"


def test_update_task_schema_validation_fail(mock_pbm_with_schema, sample_task_details):
    """Test update_task fails if schema validation fails."""
    agent_id_add = "TestAgentAddSchemaFailUpd"
    agent_id_claim = "TestAgentClaimSchemaFailUpd"
    agent_id_update = "TestAgentUpdateSchemaFailUpd"
    task_id = sample_task_details["task_id"]
    # Add and claim the task
    setup_pbm = ProjectBoardManager(project_root=mock_pbm_with_schema.project_root)
    setup_pbm.add_task(sample_task_details, agent_id_add, "future")
    setup_pbm.claim_task(task_id, agent_id_claim)
    original_task_status = setup_pbm.working_tasks[0]["status"]

    # Configure mock validate to raise error
    mock_pbm_with_schema._mock_jsonschema_validate.side_effect = (
        jsonschema.ValidationError("Simulated schema validation error on update")
    )

    updates = {"priority": "INVALID_PRIORITY"}  # Update that might fail schema

    success = mock_pbm_with_schema.update_task(task_id, updates, agent_id_update)

    assert success is False  # update_task returns False on validation fail
    mock_pbm_with_schema._mock_jsonschema_validate.assert_called_once()
    # Verify task state wasn't changed in memory (or file)
    mock_pbm_with_schema.load_boards()  # Reload to be sure
    assert len(mock_pbm_with_schema.working_tasks) == 1
    assert mock_pbm_with_schema.working_tasks[0]["status"] == original_task_status
    assert (
        mock_pbm_with_schema.working_tasks[0]["priority"] == "HIGH"
    )  # Original priority


def test_load_schema_success(pbm_instance_with_real_schema):
    """Test that _load_schema correctly loads a valid schema file."""
    # The fixture already called __init__, which calls _load_schema
    assert pbm_instance_with_real_schema._task_schema is not None
    assert isinstance(pbm_instance_with_real_schema._task_schema, dict)
    assert pbm_instance_with_real_schema._task_schema["title"] == "DreamOS Task Schema"
    assert "task_id" in pbm_instance_with_real_schema._task_schema["properties"]


def test_load_schema_not_found(
    pbm_instance,
):  # Use regular instance without schema file
    """Test that _load_schema returns None if the schema file is not found."""
    # Ensure schema file does not exist in this fixture's temp dir
    schema_path = (
        pbm_instance.project_root
        / "src"
        / "dreamos"
        / "coordination"
        / "tasks"
        / "task-schema.json"
    )
    assert not schema_path.exists()

    # Call _load_schema directly (usually called in __init__)
    loaded_schema = pbm_instance._load_schema()
    assert loaded_schema is None
    # Verify the instance variable is also None
    assert pbm_instance._task_schema is None


def test_load_schema_invalid_json(temp_test_dir):  # Needs custom setup
    """Test _load_schema handles invalid JSON gracefully."""
    # Create an invalid schema file
    schema_dir = temp_test_dir / "src" / "dreamos" / "coordination" / "tasks"
    schema_dir.mkdir(parents=True, exist_ok=True)
    schema_path = schema_dir / "task-schema.json"
    with open(schema_path, "w") as f:
        f.write('{"invalid_json": ,}')  # Invalid JSON syntax

    # Instantiate PBM pointing to this temp project root
    manager = ProjectBoardManager(project_root=temp_test_dir)
    # __init__ calls _load_schema
    assert manager._task_schema is None  # Should be None due to load failure


# --- Tests for claim_ready_task ---
def test_claim_ready_task_success(
    self, pbm: ProjectBoardManager, sample_task_1: dict, fs
):
    """Test claiming a task from the ready queue."""
    agent_id = "agent-test-claim"
    # Setup: Add task to ready queue
    fs.create_file(pbm.ready_queue_path, contents=json.dumps([sample_task_1]))

    claimed = pbm.claim_ready_task(sample_task_1["task_id"], agent_id)
    assert claimed is True

    # Verify ready queue is empty
    with open(pbm.ready_queue_path, "r") as f:
        ready_data = json.load(f)
    assert len(ready_data) == 0

    # Verify working tasks has the task
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
    working_task["status"] = "IN_PROGRESS"  # Assume it was being worked on
    working_task["claimed_by"] = agent_id
    working_task["assigned_agent"] = agent_id
    fs.create_file(pbm.working_tasks_path, contents=json.dumps([working_task]))

    final_updates = {
        "status": "COMPLETED",
        "completion_summary": "Task finished successfully.",
        "completed_by": agent_id,  # PBM should add this
    }
    moved = pbm.move_task_to_completed(working_task["task_id"], final_updates)
    assert moved is True

    # Verify working is empty
    with open(pbm.working_tasks_path, "r") as f:
        working_data = json.load(f)
    assert len(working_data) == 0

    # Verify completed has the task
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
    # Setup
    task1_working = sample_task_1.copy()
    task1_working["status"] = "CLAIMED"
    task2_ready = sample_task_2.copy()
    fs.create_file(pbm.working_tasks_path, contents=json.dumps([task1_working]))
    fs.create_file(pbm.ready_queue_path, contents=json.dumps([task2_ready]))

    # Get from working
    retrieved_task1 = pbm.get_task(sample_task_1["task_id"], board="working")
    assert retrieved_task1 is not None
    assert retrieved_task1["task_id"] == sample_task_1["task_id"]

    # Get from ready
    retrieved_task2 = pbm.get_task(sample_task_2["task_id"], board="ready")
    assert retrieved_task2 is not None
    assert retrieved_task2["task_id"] == sample_task_2["task_id"]

    # Get using 'any'
    retrieved_task1_any = pbm.get_task(sample_task_1["task_id"], board="any")
    assert retrieved_task1_any is not None
    assert retrieved_task1_any["task_id"] == sample_task_1["task_id"]
    retrieved_task2_any = pbm.get_task(sample_task_2["task_id"], board="any")
    assert retrieved_task2_any is not None
    assert retrieved_task2_any["task_id"] == sample_task_2["task_id"]


def test_get_task_not_found(self, pbm: ProjectBoardManager, fs):
    """Test getting a non-existent task."""
    fs.create_file(pbm.working_tasks_path, contents="[]")
    fs.create_file(pbm.ready_queue_path, contents="[]")
    fs.create_file(pbm.backlog_path, contents="[]")
    fs.create_file(pbm.completed_tasks_path, contents="[]")

    assert pbm.get_task("nonexistent-task-id", board="any") is None
    assert pbm.get_task("nonexistent-task-id", board="working") is None


# TODO: Add tests for update_working_task
# TODO: Add tests mocking file locking

# Note: Removed erroneous __main__ block from previous edits
# if __name__ == '__main__':
#     unittest.main()
