import json
from unittest.mock import MagicMock, patch

import pytest

# Import AppConfig to create a mock
from dreamos.core.config import AppConfig, PathsConfig

# Adjust import based on actual project structure
from dreamos.memory.memory_manager import MemoryManager


@pytest.fixture
def mock_config(tmp_path):
    """Provides a mock AppConfig with necessary paths."""
    # Create a mock PathsConfig pointing to tmp_path
    paths = PathsConfig(
        runtime=tmp_path / "runtime",
        logs=tmp_path / "runtime" / "logs",
        agent_comms=tmp_path / "runtime" / "agent_comms",
        central_task_boards=tmp_path
        / "runtime"
        / "agent_comms"
        / "central_task_boards",
        # Assuming memory path is derived or needed
        memory=tmp_path / "runtime" / "memory",
        project_root=tmp_path,  # Mock project root as tmp_path for simplicity
        # Add other required PathsConfig fields if MemoryManager needs them
    )
    # Create a mock AppConfig
    config = MagicMock(spec=AppConfig)
    config.paths = paths
    # Mock other AppConfig attributes if needed by MemoryManager
    return config


@pytest.fixture
def temp_memory_file(mock_config):
    """Provides a temporary path for the memory file based on mock_config."""
    # Ensure the directory exists based on the mock config
    memory_dir = mock_config.paths.memory
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir / "core_fragments.json"


@pytest.fixture
def memory_manager(temp_memory_file, mock_config):
    """Provides a MemoryManager instance using the temp file and mock config."""
    # Pass the mock config during instantiation
    return MemoryManager(file_path=temp_memory_file, config=mock_config)


# --- Test Cases ---


def test_memory_manager_initialization_creates_file(temp_memory_file, mock_config):
    """Test that initializing MemoryManager creates the file if it doesn't exist."""
    # Ensure file doesn't exist initially
    if temp_memory_file.exists():
        temp_memory_file.unlink()

    assert not temp_memory_file.exists()
    # Pass mock_config to constructor
    MemoryManager(file_path=temp_memory_file, config=mock_config)
    assert temp_memory_file.exists()
    # Check for empty JSON object {}
    try:
        content = temp_memory_file.read_text()
        assert json.loads(content) == {}
    except json.JSONDecodeError:
        # Handle case where file might be created but empty, depending on impl.
        assert temp_memory_file.read_text() == "{}"  # Explicit check for the string


def test_memory_manager_initialization_loads_existing(temp_memory_file, mock_config):
    """Test that initializing loads data from an existing valid file."""
    initial_data = {"frag1": {"data": "value1"}}
    temp_memory_file.write_text(json.dumps(initial_data))

    manager = MemoryManager(file_path=temp_memory_file, config=mock_config)
    assert manager.memory == initial_data


def test_load_memory_handles_empty_file(memory_manager, temp_memory_file):
    """Test loading from an empty file results in an empty dictionary."""
    temp_memory_file.write_text("")  # Empty file
    assert memory_manager.load_memory() is True
    assert memory_manager.memory == {}


def test_load_memory_handles_invalid_json(memory_manager, temp_memory_file):
    """Test loading invalid JSON returns False and resets memory."""
    temp_memory_file.write_text("this is not json")
    memory_manager.memory = {"old": "data"}  # Pre-set some data

    assert memory_manager.load_memory() is False
    assert memory_manager.memory == {}  # Memory should be reset


def test_load_memory_handles_non_dict_json(memory_manager, temp_memory_file):
    """Test loading valid JSON that is not a dictionary returns False."""
    temp_memory_file.write_text(json.dumps([1, 2, 3]))  # JSON array, not object
    memory_manager.memory = {"old": "data"}

    assert memory_manager.load_memory() is False
    assert memory_manager.memory == {}


def test_save_memory_writes_correctly(memory_manager, temp_memory_file):
    """Test that save_memory writes the current state to the file."""
    data_to_save = {"fragA": {"a": 1}, "fragB": {"b": True}}
    memory_manager.memory = data_to_save
    assert memory_manager.save_memory() is True

    # Read back and verify
    reloaded_data = json.loads(temp_memory_file.read_text())
    assert reloaded_data == data_to_save


@patch("pathlib.Path.write_text")
def test_save_memory_handles_write_error(mock_write_text, memory_manager):
    """Test that save_memory returns False if writing fails."""
    mock_write_text.side_effect = IOError("Disk full")
    memory_manager.memory = {"test": "data"}

    assert memory_manager.save_memory() is False


# --- CRUD Tests ---


def test_save_fragment_adds_new(memory_manager):
    """Test saving a new fragment."""
    assert memory_manager.save_fragment("new_id", {"key": "value"}) is True
    assert "new_id" in memory_manager.memory
    assert memory_manager.memory["new_id"] == {"key": "value"}


def test_save_fragment_updates_existing(memory_manager):
    """Test saving an existing fragment updates it."""
    memory_manager.memory = {"existing_id": {"old": "data"}}
    assert memory_manager.save_fragment("existing_id", {"new": "stuff"}) is True
    assert memory_manager.memory["existing_id"] == {"new": "stuff"}


def test_save_fragment_invalid_input(memory_manager):
    """Test save_fragment handles invalid ID or data."""
    initial_memory = memory_manager.memory.copy()
    assert memory_manager.save_fragment("", {"data": 1}) is False  # Empty ID
    assert (
        memory_manager.save_fragment("good_id", "not a dict") is False
    )  # Invalid data type
    assert memory_manager.memory == initial_memory  # Memory should not change


def test_load_fragment_returns_data(memory_manager):
    """Test loading an existing fragment."""
    memory_manager.memory = {"fragX": {"x": 123}}
    assert memory_manager.load_fragment("fragX") == {"x": 123}


def test_load_fragment_returns_none_for_missing(memory_manager):
    """Test loading a non-existent fragment returns None."""
    memory_manager.memory = {"fragX": {"x": 123}}
    assert memory_manager.load_fragment("missing_frag") is None


def test_delete_fragment_removes_existing(memory_manager):
    """Test deleting an existing fragment."""
    memory_manager.memory = {"frag_to_del": {"a": 1}, "other_frag": {"b": 2}}
    assert memory_manager.delete_fragment("frag_to_del") is True
    assert "frag_to_del" not in memory_manager.memory
    assert "other_frag" in memory_manager.memory  # Ensure others remain


def test_delete_fragment_handles_missing(memory_manager):
    """Test deleting a non-existent fragment returns False and doesn't error."""
    memory_manager.memory = {"other_frag": {"b": 2}}
    initial_memory = memory_manager.memory.copy()
    assert memory_manager.delete_fragment("missing_frag") is False
    assert memory_manager.memory == initial_memory  # Memory should not change


def test_list_fragment_ids(memory_manager):
    """Test listing fragment IDs."""
    memory_manager.memory = {"id1": {}, "id_abc": {}, "xyz": {}}
    ids = memory_manager.list_fragment_ids()
    assert isinstance(ids, list)
    assert sorted(ids) == sorted(["id1", "id_abc", "xyz"])


def test_list_fragment_ids_empty(memory_manager):
    """Test listing fragment IDs when memory is empty."""
    memory_manager.memory = {}
    assert memory_manager.list_fragment_ids() == []
