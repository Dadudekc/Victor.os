from unittest.mock import patch

import pytest
from dreamos.cli import __main__, command_supervisor, task_editor


def test_cli_help():
    """Test that CLI shows help when no command is provided."""
    with patch("sys.argv", ["dreamos"]):
        with pytest.raises(SystemExit) as excinfo:
            __main__.main()
        assert excinfo.value.code == 1


def test_task_editor_command():
    """Test that edit-task command routes to task_editor.main."""
    with patch("sys.argv", ["dreamos", "edit-task", "--task-file", "test.json"]):
        with patch.object(task_editor, "main") as mock_main:
            __main__.main()
            mock_main.assert_called_once()


def test_command_supervisor_command():
    """Test that supervise command routes to command_supervisor.main."""
    with patch("sys.argv", ["dreamos", "supervise", "--log-level", "DEBUG"]):
        with patch.object(command_supervisor, "main") as mock_main:
            __main__.main()
            mock_main.assert_called_once()


def test_task_editor_args():
    """Test task_editor argument parsing."""
    with patch("sys.argv", ["task_editor", "--task-file", "custom.json", "--create"]):
        with patch("builtins.print") as mock_print:
            task_editor.main()
            mock_print.assert_called_with("Task Editor: Creating new task custom.json")


def test_command_supervisor_args():
    """Test command_supervisor argument parsing."""
    with patch("sys.argv", ["command_supervisor", "--log-level", "DEBUG"]):
        with patch("builtins.print") as mock_print:
            command_supervisor.main()
            mock_print.assert_called_with(
                "Command Supervisor: Starting with log level DEBUG"
            )
