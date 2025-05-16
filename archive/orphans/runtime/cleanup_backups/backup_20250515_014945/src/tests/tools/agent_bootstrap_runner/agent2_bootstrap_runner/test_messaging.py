"""
Tests for the messaging module
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dreamos.tools.agent2_bootstrap_runner.messaging import (
    archive_inbox,
    create_seed_inbox,
    load_inbox,
    publish_event,
    read_input_file,
    update_inbox_with_prompt,
)


class TestPublishEvent:
    @pytest.mark.asyncio
    async def test_publish_event_success(self, mock_logger, mock_agent_bus):
        """Test successful event publishing"""
        agent_id = "Agent-2"
        event_type = "test.event"
        data = {"key": "value"}
        
        # Call publish_event
        await publish_event(mock_agent_bus, mock_logger, agent_id, event_type, data)
        
        # Check that bus.publish was called with correct arguments
        mock_agent_bus.publish.assert_called_once()
        args = mock_agent_bus.publish.call_args[0]
        
        # Check event type
        assert args[0] == f"dreamos.{agent_id.lower()}.{event_type}"
        
        # Check event data
        event = args[1]
        assert event.event_type == f"dreamos.{agent_id.lower()}.{event_type}"
        assert event.source_id == agent_id
        assert event.data == data
        
        # Check logger was not called (no errors)
        mock_logger.warning.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_publish_event_failure(self, mock_logger, mock_agent_bus):
        """Test event publishing with failure"""
        agent_id = "Agent-2"
        event_type = "test.event"
        data = {"key": "value"}
        
        # Make bus.publish raise an exception
        mock_agent_bus.publish.side_effect = Exception("Test error")
        
        # Call publish_event
        await publish_event(mock_agent_bus, mock_logger, agent_id, event_type, data)
        
        # Check that warning was logged
        mock_logger.warning.assert_called_once()

class TestArchiveInbox:
    def test_archive_inbox_success(self, mock_logger, mock_agent_config, tmp_path):
        """Test successful inbox archiving"""
        # Create mock inbox file
        inbox_file = tmp_path / "inbox.json"
        inbox_file.write_text('{"test": "data"}')
        
        # Set up mock config
        mock_agent_config.inbox_file = inbox_file
        mock_agent_config.archive_dir = tmp_path / "archive"
        mock_agent_config.archive_dir.mkdir(exist_ok=True)
        
        # Call archive_inbox
        with patch('time.time', return_value=12345):
            result = archive_inbox(mock_logger, mock_agent_config)
        
        # Check result
        assert result is True
        
        # Check that inbox file was moved to archive
        assert not inbox_file.exists()
        archive_file = mock_agent_config.archive_dir / "inbox.12345.json"
        assert archive_file.exists()
        assert archive_file.read_text() == '{"test": "data"}'
        
        # Check logger was called
        mock_logger.debug.assert_called_once()
    
    def test_archive_inbox_no_file(self, mock_logger, mock_agent_config):
        """Test archiving non-existent inbox file"""
        # Set up mock config with non-existent inbox file
        mock_agent_config.inbox_file = Path("/nonexistent/inbox.json")
        
        # Call archive_inbox
        result = archive_inbox(mock_logger, mock_agent_config)
        
        # Check result
        assert result is False
        
        # Check logger was not called
        mock_logger.debug.assert_not_called()
        mock_logger.error.assert_not_called()
    
    def test_archive_inbox_error(self, mock_logger, mock_agent_config, tmp_path):
        """Test archiving with error"""
        # Create mock inbox file
        inbox_file = tmp_path / "inbox.json"
        inbox_file.write_text('{"test": "data"}')
        
        # Set up mock config
        mock_agent_config.inbox_file = inbox_file
        mock_agent_config.archive_dir = tmp_path / "archive"  # Don't create archive dir
        
        # Call archive_inbox
        result = archive_inbox(mock_logger, mock_agent_config)
        
        # Check result
        assert result is False
        
        # Check that inbox file still exists
        assert inbox_file.exists()
        
        # Check logger was called with error
        mock_logger.error.assert_called_once()

class TestLoadInbox:
    def test_load_inbox_dict(self, mock_logger, mock_agent_config, tmp_path):
        """Test loading inbox with dict format"""
        # Create mock inbox file with dict format
        inbox_file = tmp_path / "inbox.json"
        inbox_data = {"prompt_id": "test-123", "prompt": "Test prompt"}
        inbox_file.write_text(json.dumps(inbox_data))
        
        # Set up mock config
        mock_agent_config.inbox_file = inbox_file
        
        # Call load_inbox
        result = load_inbox(mock_logger, mock_agent_config)
        
        # Check result
        assert len(result) == 1
        assert result[0] == inbox_data
        
        # Check logger was called
        mock_logger.info.assert_called_once()
    
    def test_load_inbox_list(self, mock_logger, mock_agent_config, tmp_path):
        """Test loading inbox with list format"""
        # Create mock inbox file with list format
        inbox_file = tmp_path / "inbox.json"
        inbox_data = [
            {"prompt_id": "test-123", "prompt": "Test prompt 1"},
            {"prompt_id": "test-456", "prompt": "Test prompt 2"}
        ]
        inbox_file.write_text(json.dumps(inbox_data))
        
        # Set up mock config
        mock_agent_config.inbox_file = inbox_file
        
        # Call load_inbox
        result = load_inbox(mock_logger, mock_agent_config)
        
        # Check result
        assert len(result) == 2
        assert result == inbox_data
        
        # Check logger was called
        mock_logger.info.assert_called_once()
    
    def test_load_inbox_no_file(self, mock_logger, mock_agent_config):
        """Test loading non-existent inbox file"""
        # Set up mock config with non-existent inbox file
        mock_agent_config.inbox_file = Path("/nonexistent/inbox.json")
        
        # Call load_inbox
        result = load_inbox(mock_logger, mock_agent_config)
        
        # Check result
        assert result == []
        
        # Check logger was not called
        mock_logger.info.assert_not_called()
        mock_logger.error.assert_not_called()
    
    def test_load_inbox_invalid_json(self, mock_logger, mock_agent_config, tmp_path):
        """Test loading inbox with invalid JSON"""
        # Create mock inbox file with invalid JSON
        inbox_file = tmp_path / "inbox.json"
        inbox_file.write_text("{invalid json")
        
        # Set up mock config
        mock_agent_config.inbox_file = inbox_file
        
        # Call load_inbox
        result = load_inbox(mock_logger, mock_agent_config)
        
        # Check result
        assert result == []
        
        # Check logger was called with error
        mock_logger.error.assert_called_once()
    
    def test_load_inbox_unexpected_format(self, mock_logger, mock_agent_config, tmp_path):
        """Test loading inbox with unexpected format"""
        # Create mock inbox file with unexpected format (string)
        inbox_file = tmp_path / "inbox.json"
        inbox_file.write_text('"string value"')
        
        # Set up mock config
        mock_agent_config.inbox_file = inbox_file
        
        # Call load_inbox
        result = load_inbox(mock_logger, mock_agent_config)
        
        # Check result
        assert result == []
        
        # Check logger was called with warning
        mock_logger.warning.assert_called_once()

class TestReadInputFile:
    def test_read_input_file_success(self, mock_logger, mock_agent_config, tmp_path):
        """Test successful input file reading"""
        # Create mock input file
        input_file = tmp_path / "task.txt"
        input_file.write_text("Test task")
        
        # Set up mock config
        mock_agent_config.input_file = input_file
        
        # Call read_input_file
        result = read_input_file(mock_logger, mock_agent_config)
        
        # Check result
        assert result == "Test task"
        
        # Check logger was not called
        mock_logger.error.assert_not_called()
    
    def test_read_input_file_no_file(self, mock_logger, mock_agent_config):
        """Test reading non-existent input file"""
        # Set up mock config with non-existent input file
        mock_agent_config.input_file = Path("/nonexistent/task.txt")
        
        # Call read_input_file
        result = read_input_file(mock_logger, mock_agent_config)
        
        # Check result
        assert result is None
        
        # Check logger was not called
        mock_logger.error.assert_not_called()
    
    def test_read_input_file_empty(self, mock_logger, mock_agent_config, tmp_path):
        """Test reading empty input file"""
        # Create empty input file
        input_file = tmp_path / "task.txt"
        input_file.write_text("")
        
        # Set up mock config
        mock_agent_config.input_file = input_file
        
        # Call read_input_file
        result = read_input_file(mock_logger, mock_agent_config)
        
        # Check result
        assert result is None
        
        # Check logger was not called
        mock_logger.error.assert_not_called()
    
    def test_read_input_file_error(self, mock_logger, mock_agent_config, tmp_path):
        """Test reading input file with error"""
        # Set up mock config
        mock_agent_config.input_file = tmp_path / "task.txt"
        
        # Mock file read to raise exception
        with patch('pathlib.Path.read_text', side_effect=Exception("Test error")):
            # Call read_input_file
            result = read_input_file(mock_logger, mock_agent_config)
        
        # Check result
        assert result is None
        
        # Check logger was called with error
        mock_logger.error.assert_called_once()

class TestCreateSeedInbox:
    def test_create_seed_inbox_success(self, mock_logger, mock_agent_config, tmp_path):
        """Test successful seed inbox creation"""
        # Set up mock config
        mock_agent_config.inbox_file = tmp_path / "inbox.json"
        mock_agent_config.agent_id = "Agent-2"
        
        # Mock datetime.now
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        with patch('dreamos.tools.agent2_bootstrap_runner.messaging.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.timezone = timezone
            
            # Call create_seed_inbox
            result = create_seed_inbox(mock_logger, mock_agent_config)
        
        # Check result
        assert result is True
        
        # Check that inbox file was created
        assert mock_agent_config.inbox_file.exists()
        
        # Check inbox file content
        inbox_data = json.loads(mock_agent_config.inbox_file.read_text())
        assert inbox_data["prompt_id"] == "SEED-Agent-2"
        assert "Agent-2" in inbox_data["prompt"]
        assert inbox_data["timestamp"] == "2023-01-01T12:00:00+00:00"
        assert inbox_data["type"] == "instruction"
        assert inbox_data["sender"] == "System"
        
        # Check logger was called
        mock_logger.info.assert_called_once()
    
    def test_create_seed_inbox_custom_prompt(self, mock_logger, mock_agent_config, tmp_path):
        """Test seed inbox creation with custom prompt"""
        # Set up mock config
        mock_agent_config.inbox_file = tmp_path / "inbox.json"
        mock_agent_config.agent_id = "Agent-2"
        
        # Custom prompt
        custom_prompt = "Custom test prompt"
        
        # Call create_seed_inbox
        result = create_seed_inbox(mock_logger, mock_agent_config, custom_prompt)
        
        # Check result
        assert result is True
        
        # Check that inbox file was created
        assert mock_agent_config.inbox_file.exists()
        
        # Check inbox file content
        inbox_data = json.loads(mock_agent_config.inbox_file.read_text())
        assert inbox_data["prompt"] == custom_prompt
        
        # Check logger was called
        mock_logger.info.assert_called_once()
    
    def test_create_seed_inbox_file_exists(self, mock_logger, mock_agent_config, tmp_path):
        """Test seed inbox creation when file already exists"""
        # Create existing inbox file
        inbox_file = tmp_path / "inbox.json"
        inbox_file.write_text('{"existing": "data"}')
        
        # Set up mock config
        mock_agent_config.inbox_file = inbox_file
        
        # Call create_seed_inbox
        result = create_seed_inbox(mock_logger, mock_agent_config)
        
        # Check result
        assert result is False
        
        # Check that inbox file was not modified
        assert json.loads(inbox_file.read_text()) == {"existing": "data"}
        
        # Check logger was not called
        mock_logger.info.assert_not_called()

class TestUpdateInboxWithPrompt:
    def test_update_inbox_dict_format(self, mock_logger, mock_agent_config, tmp_path):
        """Test updating inbox with dict format"""
        # Create existing inbox file with dict format
        inbox_file = tmp_path / "inbox.json"
        inbox_data = {"prompt_id": "test-123", "prompt": "Old prompt", "timestamp": "old-time"}
        inbox_file.write_text(json.dumps(inbox_data))
        
        # Set up mock config
        mock_agent_config.inbox_file = inbox_file
        
        # Custom prompt
        custom_prompt = "New prompt"
        
        # Mock datetime.now
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        with patch('dreamos.tools.agent2_bootstrap_runner.messaging.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.timezone = timezone
            
            # Call update_inbox_with_prompt
            result = update_inbox_with_prompt(mock_logger, mock_agent_config, custom_prompt)
        
        # Check result
        assert result is True
        
        # Check that inbox file was updated
        updated_data = json.loads(inbox_file.read_text())
        assert updated_data["prompt"] == custom_prompt
        assert updated_data["timestamp"] == "2023-01-01T12:00:00+00:00"
        assert updated_data["prompt_id"] == "test-123"  # Should keep original ID
        
        # Check logger was called
        mock_logger.info.assert_called_once()
    
    def test_update_inbox_list_format(self, mock_logger, mock_agent_config, tmp_path):
        """Test updating inbox with list format"""
        # Create existing inbox file with list format
        inbox_file = tmp_path / "inbox.json"
        inbox_data = [
            {"prompt_id": "test-123", "prompt": "Old prompt 1", "timestamp": "old-time"},
            {"prompt_id": "test-456", "prompt": "Old prompt 2", "timestamp": "old-time"}
        ]
        inbox_file.write_text(json.dumps(inbox_data))
        
        # Set up mock config
        mock_agent_config.inbox_file = inbox_file
        
        # Custom prompt
        custom_prompt = "New prompt"
        
        # Mock datetime.now
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        with patch('dreamos.tools.agent2_bootstrap_runner.messaging.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.timezone = timezone
            
            # Call update_inbox_with_prompt
            result = update_inbox_with_prompt(mock_logger, mock_agent_config, custom_prompt)
        
        # Check result
        assert result is True
        
        # Check that inbox file was updated (only first item should be updated)
        updated_data = json.loads(inbox_file.read_text())
        assert updated_data[0]["prompt"] == custom_prompt
        assert updated_data[0]["timestamp"] == "2023-01-01T12:00:00+00:00"
        assert updated_data[1]["prompt"] == "Old prompt 2"  # Second item unchanged
        
        # Check logger was called
        mock_logger.info.assert_called_once()
    
    def test_update_inbox_no_file(self, mock_logger, mock_agent_config):
        """Test updating non-existent inbox file"""
        # Set up mock config with non-existent inbox file
        mock_agent_config.inbox_file = Path("/nonexistent/inbox.json")
        
        # Call update_inbox_with_prompt
        result = update_inbox_with_prompt(mock_logger, mock_agent_config, "New prompt")
        
        # Check result
        assert result is False
        
        # Check logger was not called
        mock_logger.info.assert_not_called()
    
    def test_update_inbox_error(self, mock_logger, mock_agent_config, tmp_path):
        """Test updating inbox with error"""
        # Create existing inbox file
        inbox_file = tmp_path / "inbox.json"
        inbox_file.write_text('{"prompt": "Old prompt"}')
        
        # Set up mock config
        mock_agent_config.inbox_file = inbox_file
        
        # Mock file open to raise exception
        with patch('builtins.open', side_effect=Exception("Test error")):
            # Call update_inbox_with_prompt
            result = update_inbox_with_prompt(mock_logger, mock_agent_config, "New prompt")
        
        # Check result
        assert result is False
        
        # Check logger was called with error
        mock_logger.error.assert_called_once() 