"""Unit tests for the safe_edit_json_list CLI script."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# Adjust the path to import the script correctly
# Assuming tests are run from the project root (D:\Dream.os)
SCRIPT_PATH = Path("src/dreamos/cli/safe_edit_json_list.py").resolve()
# Ensure the script's directory is in the path for imports within the script itself
# sys.path.insert(0, str(SCRIPT_PATH.parent.parent.parent)) # Already handled in script, but safer?  # noqa: E501

# Import the target function IF NEEDED directly (usually test via CLI runner)
# If the script uses __name__ == "__main__", import the click command object
try:
    from src.dreamos.cli.safe_edit_json_list import SafeEditError  # noqa: F401
    from src.dreamos.cli.safe_edit_json_list import _atomic_write_json  # noqa: F401
    from src.dreamos.cli.safe_edit_json_list import (
        safe_edit_json_list,
    )
except ImportError as e:
    pytest.fail(f"Failed to import safe_edit_json_list: {e}\nSys path: {sys.path}")


# --- Fixtures ---


@pytest.fixture
def runner():
    """Provides a Click CliRunner instance."""
    return CliRunner()


@pytest.fixture
def mock_filelock():
    """Mocks the filelock library."""
    mock_lock_instance = MagicMock()
    mock_lock_class = MagicMock(return_value=mock_lock_instance)

    # Ensure is_locked is False initially and after release
    mock_lock_instance.is_locked = False

    def acquire_side_effect(*args, **kwargs):
        mock_lock_instance.is_locked = True
        return None  # Simulate successful acquire

    def release_side_effect(*args, **kwargs):
        mock_lock_instance.is_locked = False
        return None  # Simulate successful release

    mock_lock_instance.acquire.side_effect = acquire_side_effect
    mock_lock_instance.release.side_effect = release_side_effect

    with patch("src.dreamos.cli.safe_edit_json_list.filelock") as mock_fl:
        mock_fl.FileLock = mock_lock_class
        mock_fl.Timeout = Exception  # Mock Timeout exception if needed
        with patch("src.dreamos.cli.safe_edit_json_list.FILELOCK_AVAILABLE", True):
            yield mock_lock_class, mock_lock_instance


@pytest.fixture
def temp_json_file(tmp_path):
    """Creates a temporary JSON file for testing."""

    def _create_file(content: list):
        file_path = tmp_path / "test_list.json"
        lock_path = tmp_path / "test_list.json.lock"
        # Ensure lock file doesn't exist initially
        if lock_path.exists():
            lock_path.unlink()
        file_path.write_text(json.dumps(content, indent=2))
        return file_path

    return _create_file


# --- Test Cases ---


def test_add_item_success(runner, temp_json_file, mock_filelock):
    """Test adding a new item successfully."""
    mock_lock_class, mock_lock_instance = mock_filelock
    initial_data = [{"id": "task1", "value": "A"}]
    file_path = temp_json_file(initial_data)
    item_to_add = {"id": "task2", "value": "B"}
    item_data_json = json.dumps(item_to_add)

    with patch(
        "src.dreamos.cli.safe_edit_json_list._atomic_write_json"
    ) as mock_atomic_write:
        result = runner.invoke(
            safe_edit_json_list,
            [
                "--target-file",
                str(file_path),
                "--action",
                "add",
                "--item-id-key",
                "id",
                "--item-data",
                item_data_json,
            ],
        )

    assert result.exit_code == 0
    assert f"Success: File {file_path} updated (action: add)." in result.output
    mock_lock_instance.acquire.assert_called_once()
    mock_lock_instance.release.assert_called_once()

    # Check that _atomic_write_json was called with the correct data
    expected_data = initial_data + [item_to_add]
    mock_atomic_write.assert_called_once_with(file_path, expected_data)


def test_add_item_to_empty_file(runner, temp_json_file, mock_filelock):
    """Test adding an item to an initially empty JSON file."""
    mock_lock_class, mock_lock_instance = mock_filelock
    file_path = temp_json_file([])  # Start with empty list
    item_to_add = {"id": "task1", "value": "A"}
    item_data_json = json.dumps(item_to_add)

    with patch(
        "src.dreamos.cli.safe_edit_json_list._atomic_write_json"
    ) as mock_atomic_write:
        result = runner.invoke(
            safe_edit_json_list,
            [
                "--target-file",
                str(file_path),
                "--action",
                "add",
                "--item-id-key",
                "id",
                "--item-data",
                item_data_json,
            ],
        )

    assert result.exit_code == 0
    assert f"Success: File {file_path} updated (action: add)." in result.output
    mock_lock_instance.acquire.assert_called_once()
    mock_lock_instance.release.assert_called_once()
    mock_atomic_write.assert_called_once_with(file_path, [item_to_add])


def test_remove_item_success(runner, temp_json_file, mock_filelock):
    """Test removing an existing item successfully."""
    mock_lock_class, mock_lock_instance = mock_filelock
    initial_data = [{"task_id": "t1", "v": 1}, {"task_id": "t2", "v": 2}]
    file_path = temp_json_file(initial_data)

    with patch(
        "src.dreamos.cli.safe_edit_json_list._atomic_write_json"
    ) as mock_atomic_write:
        result = runner.invoke(
            safe_edit_json_list,
            [
                "--target-file",
                str(file_path),
                "--action",
                "remove",
                "--item-id-key",
                "task_id",
                "--item-id",
                "t1",
            ],
        )

    assert result.exit_code == 0
    assert f"Success: File {file_path} updated (action: remove)." in result.output
    mock_lock_instance.acquire.assert_called_once()
    mock_lock_instance.release.assert_called_once()
    expected_data = [{"task_id": "t2", "v": 2}]
    mock_atomic_write.assert_called_once_with(file_path, expected_data)


def test_remove_item_not_found(runner, temp_json_file, mock_filelock):
    """Test removing an item that does not exist (should be a no-op)."""
    mock_lock_class, mock_lock_instance = mock_filelock
    initial_data = [{"task_id": "t1", "v": 1}, {"task_id": "t2", "v": 2}]
    file_path = temp_json_file(initial_data)

    with patch(
        "src.dreamos.cli.safe_edit_json_list._atomic_write_json"
    ) as mock_atomic_write:
        result = runner.invoke(
            safe_edit_json_list,
            [
                "--target-file",
                str(file_path),
                "--action",
                "remove",
                "--item-id-key",
                "task_id",
                "--item-id",
                "t3",  # Item does not exist
            ],
        )

    assert result.exit_code == 0
    # Check for the specific no-changes message
    assert (
        f"Success: No changes needed for file {file_path} (action: remove)."
        in result.output
    )
    mock_lock_instance.acquire.assert_called_once()
    mock_lock_instance.release.assert_called_once()
    mock_atomic_write.assert_not_called()  # File should not be rewritten


def test_update_item_success(runner, temp_json_file, mock_filelock):
    """Test updating an existing item successfully."""
    mock_lock_class, mock_lock_instance = mock_filelock
    initial_data = [{"id": "task1", "value": "A"}, {"id": "task2", "value": "B"}]
    file_path = temp_json_file(initial_data)
    item_update_data = {"value": "A_updated", "new_field": True}
    item_data_json = json.dumps(item_update_data)

    with patch(
        "src.dreamos.cli.safe_edit_json_list._atomic_write_json"
    ) as mock_atomic_write:
        result = runner.invoke(
            safe_edit_json_list,
            [
                "--target-file",
                str(file_path),
                "--action",
                "update",
                "--item-id-key",
                "id",
                "--item-id",
                "task1",
                "--item-data",
                item_data_json,
            ],
        )

    assert result.exit_code == 0
    assert f"Success: File {file_path} updated (action: update)." in result.output
    mock_lock_instance.acquire.assert_called_once()
    mock_lock_instance.release.assert_called_once()
    expected_data = [
        {"id": "task1", "value": "A_updated", "new_field": True},
        {"id": "task2", "value": "B"},
    ]
    mock_atomic_write.assert_called_once_with(file_path, expected_data)


def test_update_item_not_found(runner, temp_json_file, mock_filelock):
    """Test updating an item that does not exist (should be a no-op)."""
    mock_lock_class, mock_lock_instance = mock_filelock
    initial_data = [{"id": "task1", "value": "A"}]
    file_path = temp_json_file(initial_data)
    item_update_data = {"value": "C"}
    item_data_json = json.dumps(item_update_data)

    with patch(
        "src.dreamos.cli.safe_edit_json_list._atomic_write_json"
    ) as mock_atomic_write:
        result = runner.invoke(
            safe_edit_json_list,
            [
                "--target-file",
                str(file_path),
                "--action",
                "update",
                "--item-id-key",
                "id",
                "--item-id",
                "task3",  # Item does not exist
                "--item-data",
                item_data_json,
            ],
        )

    assert result.exit_code == 0
    assert (
        f"Success: No changes needed for file {file_path} (action: update)."
        in result.output
    )
    mock_lock_instance.acquire.assert_called_once()
    mock_lock_instance.release.assert_called_once()
    mock_atomic_write.assert_not_called()


def test_invalid_json_item_data(runner, temp_json_file):
    """Test providing invalid JSON for item-data."""
    file_path = temp_json_file([{"id": "task1"}])
    invalid_json = '{"id": "task2", "value": '  # Missing closing quote and brace

    result = runner.invoke(
        safe_edit_json_list,
        [
            "--target-file",
            str(file_path),
            "--action",
            "add",
            "--item-id-key",
            "id",
            "--item-data",
            invalid_json,
        ],
    )

    assert result.exit_code == 1
    assert "Error: Invalid JSON provided for --item-data" in result.output


def test_item_data_not_dict(runner, temp_json_file):
    """Test providing item-data that is not a JSON object."""
    file_path = temp_json_file([])
    not_dict_json = "[1, 2, 3]"  # JSON array, not object

    result = runner.invoke(
        safe_edit_json_list,
        [
            "--target-file",
            str(file_path),
            "--action",
            "add",
            "--item-id-key",
            "id",
            "--item-data",
            not_dict_json,
        ],
    )

    assert result.exit_code == 1
    assert "Error: item-data must be a JSON object (dictionary)." in result.output


def test_missing_item_id_for_remove(runner, temp_json_file):
    """Test calling remove without providing --item-id."""
    file_path = temp_json_file([{"id": "task1"}])

    result = runner.invoke(
        safe_edit_json_list,
        [
            "--target-file",
            str(file_path),
            "--action",
            "remove",
            "--item-id-key",
            "id",  # Missing --item-id
            # '--item-id', 'task1'
        ],
    )

    assert result.exit_code == 1
    assert "Error: --item-id is required for action 'remove'" in result.output


def test_missing_item_data_for_add(runner, temp_json_file):
    """Test calling add without providing --item-data."""
    file_path = temp_json_file([])

    result = runner.invoke(
        safe_edit_json_list,
        [
            "--target-file",
            str(file_path),
            "--action",
            "add",
            "--item-id-key",
            "id",  # Missing --item-data
            # '--item-data', '{}'
        ],
    )

    assert result.exit_code == 1
    assert (
        "Error: --item-data (as JSON string) is required for action 'add'"
        in result.output
    )


def test_target_file_not_list(runner, tmp_path, mock_filelock):
    """Test targeting a file that contains a JSON object, not a list."""
    mock_lock_class, mock_lock_instance = mock_filelock
    file_path = tmp_path / "not_a_list.json"
    file_path.write_text('{"key": "value"}')  # Write an object, not a list

    item_to_add = {"id": "task1"}
    item_data_json = json.dumps(item_to_add)

    result = runner.invoke(
        safe_edit_json_list,
        [
            "--target-file",
            str(file_path),
            "--action",
            "add",
            "--item-id-key",
            "id",
            "--item-data",
            item_data_json,
        ],
    )

    assert result.exit_code == 1
    assert (
        f"Error: Target file {file_path} does not contain a valid JSON list."
        in result.output
    )
    mock_lock_instance.acquire.assert_called_once()  # Lock should still be acquired
    mock_lock_instance.release.assert_called_once()  # And released


def test_target_file_invalid_json(runner, tmp_path, mock_filelock):
    """Test targeting a file with invalid JSON content."""
    mock_lock_class, mock_lock_instance = mock_filelock
    file_path = tmp_path / "invalid.json"
    file_path.write_text('["item1", {"id":')  # Invalid JSON

    item_to_add = {"id": "task1"}
    item_data_json = json.dumps(item_to_add)

    result = runner.invoke(
        safe_edit_json_list,
        [
            "--target-file",
            str(file_path),
            "--action",
            "add",
            "--item-id-key",
            "id",
            "--item-data",
            item_data_json,
        ],
    )

    assert result.exit_code == 1
    assert f"Error: Failed to decode JSON from {file_path}" in result.output
    mock_lock_instance.acquire.assert_called_once()
    mock_lock_instance.release.assert_called_once()


# Test _atomic_write_json directly? Maybe not necessary if CLI tests cover it.
# Could add tests for lock timeout if feasible to simulate with mock.
# Could add tests for the no-filelock-library warning.
