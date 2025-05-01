# tests/scripts/utils/test_simple_task_updater.py
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add helper to find project root if not standard
# Assume PROJECT_ROOT is determined correctly as in the script itself
SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent  # Adjust if test dir structure differs
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "utils" / "simple_task_updater.py"

# --- Fixtures ---


@pytest.fixture
def mock_board_manager():
    """Mocks the ProjectBoardManager class."""
    with patch("scripts.utils.simple_task_updater.ProjectBoardManager") as MockPBM:
        instance = MockPBM.return_value
        instance.claim_future_task = MagicMock(return_value=True)  # Default success
        instance.update_working_task = MagicMock(return_value=True)  # Default success
        instance.move_task_to_completed = MagicMock(
            return_value=True
        )  # Default success
        yield instance


# --- Helper Function ---


def run_script(args: list[str]) -> subprocess.CompletedProcess:
    """Runs the script with given arguments."""
    command = [sys.executable, str(SCRIPT_PATH)] + args
    # Use cwd=PROJECT_ROOT to ensure relative paths in script work
    result = subprocess.run(command, capture_output=True, text=True, cwd=PROJECT_ROOT)
    print(f"CMD: {' '.join(command)}")  # Debugging
    print(f"STDOUT: {result.stdout}")
    print(f"STDERR: {result.stderr}")
    return result


# --- Test Cases (Test Case 3) ---


class TestSimpleTaskUpdaterScript:

    def test_claim_success(self, mock_board_manager: MagicMock):
        """Test Case 3.1: Claim action success."""
        task_id = "task_claim_1"
        agent_id = "AgentScriptTest"
        result = run_script(["claim", task_id, agent_id])
        assert result.returncode == 0
        mock_board_manager.claim_future_task.assert_called_once_with(
            task_id=task_id, agent_id=agent_id
        )
        assert (
            "claimed successfully" in result.stderr
        )  # Script logs INFO to stderr via basicConfig

    def test_claim_failure_board(self, mock_board_manager: MagicMock):
        """Test Case simulating board manager failure during claim."""
        mock_board_manager.claim_future_task.return_value = False
        task_id = "task_claim_fail"
        agent_id = "AgentScriptTest"
        result = run_script(["claim", task_id, agent_id])
        assert result.returncode != 0
        mock_board_manager.claim_future_task.assert_called_once_with(
            task_id=task_id, agent_id=agent_id
        )
        assert "Failed to claim task" in result.stderr

    def test_claim_missing_arg(self):
        """Test Case 3.7: Claim action missing agent_id."""
        task_id = "task_claim_missing"
        result = run_script(["claim", task_id])
        assert result.returncode != 0
        assert "the following arguments are required: agent_id" in result.stderr

    def test_update_working_success(self, mock_board_manager: MagicMock):
        """Test Case 3.3: Update action success (non-completion)."""
        task_id = "task_update_1"
        status = "IN_PROGRESS"
        notes = "Testing notes"
        result = run_script(["update", task_id, status, "--notes", notes])
        assert result.returncode == 0
        mock_board_manager.update_working_task.assert_called_once()
        # Check that the updates dict passed is correct (ignore timestamp)
        call_args, call_kwargs = mock_board_manager.update_working_task.call_args
        assert call_kwargs["task_id"] == task_id
        assert call_kwargs["updates"]["status"] == status
        assert call_kwargs["updates"]["notes"] == notes
        assert "updated successfully" in result.stderr
        mock_board_manager.move_task_to_completed.assert_not_called()

    def test_update_completed_success(self, mock_board_manager: MagicMock):
        """Test Case 3.4: Update action success (completion status)."""
        task_id = "task_complete_1"
        status = "COMPLETED"
        notes = "All finished"
        result = run_script(["update", task_id, status, "--notes", notes])
        assert result.returncode == 0
        mock_board_manager.move_task_to_completed.assert_called_once()
        # Check that the updates dict passed is correct (ignore timestamp)
        call_args, call_kwargs = mock_board_manager.move_task_to_completed.call_args
        assert call_kwargs["task_id"] == task_id
        assert call_kwargs["final_updates"]["status"] == status
        assert call_kwargs["final_updates"]["notes"] == notes
        assert "timestamp_completed" in call_kwargs["final_updates"]
        assert "successfully moved to completed" in result.stderr
        mock_board_manager.update_working_task.assert_not_called()

    def test_update_failure_board(self, mock_board_manager: MagicMock):
        """Test Case simulating board manager failure during update."""
        mock_board_manager.update_working_task.return_value = False
        task_id = "task_update_fail"
        status = "FAILED"
        result = run_script(["update", task_id, status])
        assert result.returncode != 0
        mock_board_manager.update_working_task.assert_called_once()
        assert "Failed to update task" in result.stderr

    def test_update_move_failure_board(self, mock_board_manager: MagicMock):
        """Test Case simulating board manager failure during move to completed."""
        mock_board_manager.move_task_to_completed.return_value = False
        task_id = "task_move_fail"
        status = "COMPLETED"
        result = run_script(["update", task_id, status])
        assert result.returncode != 0
        mock_board_manager.move_task_to_completed.assert_called_once()
        assert "Failed to move task" in result.stderr

    def test_update_missing_arg(self):
        """Test Case 3.8: Update action missing status."""
        task_id = "task_update_missing"
        result = run_script(["update", task_id])
        assert result.returncode != 0
        assert "the following arguments are required: status" in result.stderr

    def test_invalid_action(self):
        """Test Case 3.6: Invalid action."""
        result = run_script(["delete", "task_invalid"])  # Assuming delete isn't valid
        assert result.returncode != 0
        assert "invalid choice: 'delete'" in result.stderr


# TODO: Add tests for --board_file argument if needed
# TODO: Add tests for mailbox interactions if they are integrated here
