import os
import json
import time
import pytest
import threading
from pathlib import Path
from unittest.mock import MagicMock
from _agent_coordination.utils.mailbox_utils import process_directory_loop

def log_event(event_type, agent_id, data):
    """Mock log_event function for test coverage reporting."""
    print(f"[{event_type}] Agent: {agent_id}, Data: {data}")

@pytest.fixture
def test_dirs(tmp_path):
    """Create temporary test directories."""
    watch_dir = tmp_path / "watch"
    success_dir = tmp_path / "success"
    error_dir = tmp_path / "error"
    return watch_dir, success_dir, error_dir

def create_test_file(dir_path: Path, name: str, content: dict = None):
    """Helper to create a test JSON file."""
    if content is None:
        content = {"test": "data"}
    file_path = dir_path / f"{name}.json"
    file_path.write_text(json.dumps(content))
    return file_path

def test_directory_creation(test_dirs):
    """Test that the function creates necessary directories."""
    watch_dir, success_dir, error_dir = test_dirs
    stop_event = threading.Event()
    stop_event.set()  # Make the loop exit immediately
    
    process_directory_loop(
        watch_dir=watch_dir,
        process_func=lambda x: True,
        success_dir=success_dir,
        error_dir=error_dir,
        stop_event=stop_event
    )
    
    assert watch_dir.exists()
    assert success_dir.exists()
    assert error_dir.exists()
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_directory_creation"})

@pytest.mark.parametrize("process_func,expected_success,expected_error,expect_error_context", [
    (lambda path: True, True, False, False),
    (lambda path: False, False, True, False),
    (lambda path: (_ for _ in ()).throw(Exception("Test exception")), False, True, True),
])
def test_process_variants(test_dirs, process_func, expected_success, expected_error, expect_error_context):
    """Parametrized test for multiple processing outcomes."""
    watch_dir, success_dir, error_dir = test_dirs
    watch_dir.mkdir()
    # Create a test file
    test_file = create_test_file(watch_dir, "variant_test")
    processed = threading.Event()

    def wrap(path):
        processed.set()
        return process_func(path)

    stop_event = threading.Event()
    thread = threading.Thread(
        target=process_directory_loop,
        kwargs={
            'watch_dir': watch_dir,
            'process_func': wrap,
            'success_dir': success_dir,
            'error_dir': error_dir,
            'poll_interval': 1,
            'stop_event': stop_event
        }
    )
    thread.start()
    processed.wait(timeout=5)
    stop_event.set()
    thread.join(timeout=5)
    # Verify file movement
    assert not test_file.exists()
    assert (success_dir / test_file.name).exists() == expected_success
    assert (error_dir / test_file.name).exists() == expected_error
    if expect_error_context:
        data = json.loads((error_dir / test_file.name).read_text())
        assert 'error_context' in data
        assert 'timestamp_failed' in data['error_context']
        assert 'error_message' in data['error_context']
        assert 'Test exception' in data['error_context']['error_message']

def test_wrong_file_suffix(test_dirs):
    """Test handling of files with wrong suffix."""
    watch_dir, success_dir, error_dir = test_dirs
    watch_dir.mkdir()
    
    # Create a file with wrong suffix
    test_file = watch_dir / "test.txt"
    test_file.write_text("test data")
    processed = threading.Event()
    
    def process_func(path):
        processed.set()  # Should not be called
        return True
    
    stop_event = threading.Event()
    
    # Start processing in a thread
    thread = threading.Thread(target=process_directory_loop,
                            kwargs={
                                'watch_dir': watch_dir,
                                'process_func': process_func,
                                'success_dir': success_dir,
                                'error_dir': error_dir,
                                'poll_interval': 1,
                                'stop_event': stop_event
                            })
    thread.start()
    
    # Wait briefly
    time.sleep(2)
    stop_event.set()
    thread.join(timeout=5)
    
    # Check results
    assert test_file.exists()  # File should remain in watch dir
    assert not (success_dir / test_file.name).exists()
    assert not (error_dir / test_file.name).exists()
    assert not processed.is_set()  # Process func should not have been called
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_wrong_file_suffix"})

def test_stop_event_handling(test_dirs):
    """Test that stop event is properly handled."""
    watch_dir, success_dir, error_dir = test_dirs
    watch_dir.mkdir()
    
    stop_event = threading.Event()
    processed = threading.Event()
    
    def process_func(path):
        processed.set()
        return True
    
    # Start processing in a thread
    thread = threading.Thread(target=process_directory_loop,
                            kwargs={
                                'watch_dir': watch_dir,
                                'process_func': process_func,
                                'success_dir': success_dir,
                                'error_dir': error_dir,
                                'poll_interval': 10,  # Long poll interval
                                'stop_event': stop_event
                            })
    thread.start()
    
    # Set stop event immediately
    stop_event.set()
    
    # Thread should exit quickly despite long poll interval
    thread.join(timeout=2)
    assert not thread.is_alive()
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_stop_event_handling"})

if __name__ == '__main__':
    pytest.main(['-v', __file__]) 
