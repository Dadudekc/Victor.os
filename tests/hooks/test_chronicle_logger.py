from unittest.mock import MagicMock, mock_open, patch  # noqa: I001

import pytest
from dreamos.coordination.agent_bus import (  # Assuming EventType might be used
    BaseEvent,
    EventType,
)
from dreamos.hooks.chronicle_logger import ChronicleLoggerHook

# Remove the skipped stub function
# @pytest.mark.skip(reason='Test stub for coverage tracking')
# def test_stub_for_chronicle_logger():
#     pass


@pytest.fixture
def mock_agent_bus_instance() -> MagicMock:
    """Provides a mock AgentBus instance."""
    bus = MagicMock()
    # Make subscribe a simple mock function for now
    bus.subscribe = MagicMock()
    return bus


# Patch AgentBus instantiation for the duration of the test class/module
@patch("dreamos.hooks.chronicle_logger.AgentBus")
@patch("dreamos.hooks.chronicle_logger.Path.mkdir")  # Mock directory creation
@patch("builtins.open", new_callable=mock_open)  # Mock file open/write/read
@patch("dreamos.hooks.chronicle_logger.threading.Lock")  # Mock the lock
def test_chronicle_logger_init(
    MockLock,
    mock_file_open,
    mock_mkdir,
    MockAgentBus,
    mock_agent_bus_instance,
    tmp_path,
):
    """Test initialization creates files/dirs, lock, and subscribes."""
    MockAgentBus.return_value = (
        mock_agent_bus_instance  # Return the mock instance when AgentBus() is called
    )
    mock_lock_instance = MockLock.return_value

    chronicle_file = tmp_path / "test_chronicle.md"
    hook = ChronicleLoggerHook(chronicle_path=chronicle_file)

    # Assertions
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    # Check if file was created with header (if it didn't exist)
    # mock_file_open.assert_called_with(chronicle_file, 'w', encoding='utf-8')
    # handle = mock_file_open()
    # handle.write.assert_called_once_with("# Dreamscape Chronicle\n---\n\n") # Check header write  # noqa: E501
    assert hook.chronicle_path == chronicle_file
    MockLock.assert_called_once()  # Check lock was created
    assert hook._lock == mock_lock_instance
    MockAgentBus.assert_called_once()  # Check AgentBus was instantiated
    assert hook.agent_bus == mock_agent_bus_instance
    # Check subscription
    mock_agent_bus_instance.subscribe.assert_called_once_with("*", hook._handle_event)


@patch(
    "dreamos.hooks.chronicle_logger.AgentBus"
)  # Need to patch bus even if not used directly in format
def test_chronicle_logger_format_entry(MockAgentBus):
    """Test the _format_entry method produces correct Markdown."""
    hook = ChronicleLoggerHook()  # Initialize minimally for formatting

    test_data = {
        "task_id": "task-123",
        "agent_id": "AgentTest",
        "status": "RUNNING",
        "message": "Processing data...",
    }
    event = BaseEvent(event_type=EventType.TASK_STATUS_UPDATE, data=test_data)

    formatted_entry = hook._format_entry(event)

    assert f"Event: {EventType.TASK_STATUS_UPDATE}" in formatted_entry
    assert "Task: task-123" in formatted_entry
    assert "Agent**: AgentTest" in formatted_entry
    assert "Outcome**: RUNNING" in formatted_entry
    assert "Details**: Processing data..." in formatted_entry
    assert formatted_entry.endswith("---\n\n")


@patch("dreamos.hooks.chronicle_logger.AgentBus")
@patch("dreamos.hooks.chronicle_logger.threading.Lock")
@patch("builtins.open", new_callable=mock_open)
def test_chronicle_logger_handle_event(
    mock_file_open, MockLock, MockAgentBus, mock_agent_bus_instance, tmp_path
):
    """Test that _handle_event formats and writes the log entry."""
    MockAgentBus.return_value = mock_agent_bus_instance
    mock_lock_instance = MockLock.return_value
    # Mock the context manager methods for the lock
    mock_lock_instance.__enter__ = MagicMock()
    mock_lock_instance.__exit__ = MagicMock()

    chronicle_file = tmp_path / "handle_test.md"
    hook = ChronicleLoggerHook(chronicle_path=chronicle_file)

    # Create a mock event
    test_data = {
        "agent_id": "HandlerAgent",
        "status": "COMPLETE",
        "message": "Task done.",
    }
    event = BaseEvent(event_type=EventType.TASK_COMPLETED, data=test_data)

    # Call the handler directly
    hook._handle_event(event)

    # Assertions
    mock_lock_instance.__enter__.assert_called_once()  # Lock acquired
    mock_file_open.assert_called_with(
        chronicle_file, "a", encoding="utf-8"
    )  # Opened in append mode
    handle = mock_file_open()
    # Check that write was called (content check is implicitly done by testing _format_entry)  # noqa: E501
    assert handle.write.call_count == 1
    # Check the content roughly
    written_content = handle.write.call_args[0][0]
    assert "Event: TASK_COMPLETED" in written_content
    assert "HandlerAgent" in written_content
    assert "COMPLETE" in written_content
    assert "Task done." in written_content
    mock_lock_instance.__exit__.assert_called_once()  # Lock released
