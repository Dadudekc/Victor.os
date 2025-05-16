import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from continuous_operation import ContinuousOperationHandler


@pytest.fixture
def temp_queue_dir(tmp_path):
    """Create a temporary queue directory for testing."""
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    return queue_dir

@pytest.fixture
def handler(temp_queue_dir):
    """Create a continuous operation handler for testing."""
    return ContinuousOperationHandler(temp_queue_dir)

def test_initial_state(handler):
    """Test the initial state of the handler."""
    assert handler.cycle_count == 0
    assert handler.min_cycles == 25
    assert handler.cycle_timeout == 60

def test_cycle_increment(handler):
    """Test that cycles increment correctly."""
    handler.increment_cycle()
    assert handler.cycle_count == 1
    assert handler.last_cycle_time is not None

def test_cycle_reset(handler):
    """Test that cycles reset correctly."""
    handler.increment_cycle()
    handler.increment_cycle()
    handler.reset_cycle_count()
    assert handler.cycle_count == 0
    assert handler.last_cycle_time is not None

def test_cycle_health(handler):
    """Test cycle health checking."""
    assert handler.check_cycle_health() is True
    
    # Simulate timeout
    handler.last_cycle_time = datetime.now(timezone.utc).replace(year=2000)
    assert handler.check_cycle_health() is False
    assert handler.cycle_count == 0

def test_prompt_processing(handler):
    """Test prompt processing and cycle management."""
    result = handler.process_prompt("Agent-1", "resume autonomy")
    assert result is False  # Not enough cycles yet
    assert handler.cycle_count == 1

    # Process enough prompts to meet minimum cycles
    for _ in range(24):
        handler.process_prompt("Agent-1", "resume autonomy")
    
    assert handler.cycle_count == 25
    assert handler.process_prompt("Agent-1", "resume autonomy") is True

def test_operation_status(handler):
    """Test operation status reporting."""
    status = handler.get_operation_status()
    assert "cycle_count" in status
    assert "last_cycle_time" in status
    assert "is_healthy" in status
    assert "min_cycles_met" in status
    assert status["cycle_count"] == 0
    assert status["is_healthy"] is True
    assert status["min_cycles_met"] is False

def test_log_creation(handler):
    """Test that logs are created correctly."""
    handler.log_cycle_reset("test reason")
    handler.log_cycle_milestone()
    
    log_file = handler.queue_dir / "operation_log.jsonl"
    assert log_file.exists()
    
    with open(log_file) as f:
        lines = f.readlines()
        assert len(lines) == 2
        
        # Check reset log
        reset_log = json.loads(lines[0])
        assert reset_log["event"] == "cycle_reset"
        assert reset_log["reason"] == "test reason"
        
        # Check milestone log
        milestone_log = json.loads(lines[1])
        assert milestone_log["event"] == "cycle_milestone"

def test_prompt_file_creation(handler):
    """Test that prompt files are created correctly."""
    handler.process_prompt("Agent-1", "test prompt")
    
    assert handler.prompts_file.exists()
    
    with open(handler.prompts_file) as f:
        lines = f.readlines()
        assert len(lines) == 1
        
        prompt_entry = json.loads(lines[0])
        assert prompt_entry["agent_id"] == "Agent-1"
        assert prompt_entry["prompt"] == "test prompt"
        assert "timestamp" in prompt_entry 