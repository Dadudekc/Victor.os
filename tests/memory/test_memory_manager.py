import json
from pathlib import Path
from unittest.mock import patch

import pytest

# Adjust import based on actual project structure
from dreamos.memory.memory_manager import MemoryManager


@pytest.fixture
def temp_memory_file(tmp_path):
    """Provides a temporary path for the memory file."""
    return tmp_path / "test_fragments.json"


@pytest.fixture
def memory_manager(temp_memory_file):
    """Provides a MemoryManager instance using the temp file."""
    return MemoryManager(file_path=temp_memory_file)


# --- Test Cases ---


def test_memory_manager_initialization_creates_file(temp_memory_file):
    """Test that initializing MemoryManager creates the file if it doesn't exist."""
    assert not temp_memory_file.exists()
    MemoryManager(file_path=temp_memory_file)
    assert temp_memory_file.exists()
    assert temp_memory_file.read_text() == "{}"


def test_memory_manager_initialization_loads_existing(temp_memory_file):
    """Test that initializing loads data from an existing valid file."""
    initial_data = {"frag1": {"data": "value1"}}
    temp_memory_file.write_text(json.dumps(initial_data))

    manager = MemoryManager(file_path=temp_memory_file)
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
