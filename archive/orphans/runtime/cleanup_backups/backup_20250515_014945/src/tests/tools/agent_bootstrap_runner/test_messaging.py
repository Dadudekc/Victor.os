"""
Tests for the agent bootstrap runner messaging functionality
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from dreamos.tools.agent_bootstrap_runner.config import AgentConfig
from dreamos.tools.agent_bootstrap_runner.messaging import (
    ValidationResult,
    archive_inbox,
    publish_event,
    read_input_file,
    validate_message,
)


@pytest.fixture
def mock_config(tmp_path):
    """Create a mock agent configuration"""
    runtime_dir = tmp_path / "runtime"
    return AgentConfig("Agent-2", runtime_base=runtime_dir)

@pytest.fixture
def mock_bus():
    """Create a mock agent bus"""
    class MockBus:
        def __init__(self):
            self.published_events = []
            
        async def publish(self, topic: str, data: dict):
            self.published_events.append((topic, data))
            
    return MockBus()

@pytest.fixture
def mock_logger():
    """Create a mock logger"""
    class MockLogger:
        def __init__(self):
            self.logs = []
            
        def info(self, msg): self.logs.append(("INFO", msg))
        def error(self, msg): self.logs.append(("ERROR", msg))
        def warning(self, msg): self.logs.append(("WARNING", msg))
        def debug(self, msg): self.logs.append(("DEBUG", msg))
            
    return MockLogger()

async def test_publish_event(mock_bus, mock_logger, mock_config):
    """Test event publishing"""
    # Publish a test event
    await publish_event(
        mock_bus,
        mock_logger,
        mock_config.agent_id,
        "test.event",
        {"data": "test"}
    )
    
    # Check that event was published
    assert len(mock_bus.published_events) == 1
    topic, data = mock_bus.published_events[0]
    
    assert topic == "agent.test.event"
    assert data["agent_id"] == mock_config.agent_id
    assert data["data"] == "test"
    assert "timestamp" in data

def test_validate_message():
    """Test message validation"""
    # Valid JSON message
    valid_json = json.dumps({
        "prompt": "Test prompt",
        "id": "test-1"
    })
    result = validate_message(valid_json)
    assert result.passed
    assert result.error is None
    
    # Invalid JSON
    invalid_json = "{"
    result = validate_message(invalid_json)
    assert not result.passed
    assert "Invalid JSON" in result.error
    
    # Empty message
    result = validate_message("")
    assert not result.passed
    assert "Empty message" in result.error
    
    # Missing required fields
    invalid_content = json.dumps({"foo": "bar"})
    result = validate_message(invalid_content)
    assert not result.passed
    assert "Missing required fields" in result.error

def test_archive_inbox(mock_config, mock_logger):
    """Test inbox archiving"""
    # Create test inbox file
    inbox_data = {
        "messages": [
            {"id": "test-1", "prompt": "Test 1"},
            {"id": "test-2", "prompt": "Test 2"}
        ]
    }
    mock_config.inbox_file.parent.mkdir(parents=True, exist_ok=True)
    mock_config.inbox_file.write_text(json.dumps(inbox_data))
    
    # Create archive directory
    mock_config.archive_dir.mkdir(parents=True, exist_ok=True)
    
    # Archive inbox
    success = archive_inbox(mock_logger, mock_config)
    assert success
    
    # Check that inbox was moved to archive
    assert not mock_config.inbox_file.exists()
    archived_files = list(mock_config.archive_dir.glob("inbox_*.json"))
    assert len(archived_files) == 1
    
    # Verify archived content
    archived_data = json.loads(archived_files[0].read_text())
    assert archived_data == inbox_data

def test_read_input_file(mock_config, mock_logger):
    """Test reading input file"""
    # Create test input file
    test_content = "Test task content"
    mock_config.input_file.parent.mkdir(parents=True, exist_ok=True)
    mock_config.input_file.write_text(test_content)
    
    # Read input file
    content = read_input_file(mock_logger, mock_config)
    assert content == test_content
    
    # Test with missing file
    mock_config.input_file.unlink()
    content = read_input_file(mock_logger, mock_config)
    assert content is None
    
    # Check that warning was logged
    assert any("WARNING" in log for log in mock_logger.logs)

def test_message_validation_with_markdown():
    """Test validation of markdown messages"""
    # Valid markdown
    valid_md = """# Test Message
    
This is a test message with:
- Point 1
- Point 2

```python
print("Hello")
```
"""
    result = validate_message(valid_md)
    assert result.passed
    
    # Markdown with YAML frontmatter
    md_with_meta = """---
id: test-1
priority: high
---
# Test Message
Content here
"""
    result = validate_message(md_with_meta)
    assert result.passed 