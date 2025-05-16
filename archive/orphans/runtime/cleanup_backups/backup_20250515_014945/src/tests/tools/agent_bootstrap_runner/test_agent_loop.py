"""
Tests for the agent bootstrap runner's main loop
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dreamos.tools.agent_bootstrap_runner.agent_loop import (
    AgentLoop,
    AgentLoopError,
    AgentStateManager,
    MessageProcessor,
)
from dreamos.tools.agent_bootstrap_runner.config import AgentConfig


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
            
        async def close(self):
            pass
            
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

@pytest.fixture
def mock_ui_interactor():
    """Create a mock UI interactor"""
    class MockUIInteractor:
        def __init__(self):
            self.injected_prompts = []
            self.responses = ["Test response"]
            
        def initialize(self):
            return True
            
        async def inject_prompt(self, bus, prompt):
            self.injected_prompts.append(prompt)
            return True
            
        async def retrieve_response(self, bus):
            return self.responses.pop(0) if self.responses else None
            
    return MockUIInteractor()

class TestAgentStateManager:
    """Tests for AgentStateManager"""
    
    def test_initialization(self, mock_config):
        """Test state manager initialization"""
        state_mgr = AgentStateManager(mock_config)
        
        # Check default state
        assert state_mgr.state["cycle_count"] == 0
        assert state_mgr.state["current_task"] == "initializing"
        assert state_mgr.state["messages_processed"] == 0
        
    def test_state_persistence(self, mock_config):
        """Test state saving and loading"""
        state_mgr = AgentStateManager(mock_config)
        
        # Update and save state
        state_mgr.update_state(
            cycle_count=1,
            current_task="test_task"
        )
        
        # Create new manager and check state loaded
        new_mgr = AgentStateManager(mock_config)
        assert new_mgr.state["cycle_count"] == 1
        assert new_mgr.state["current_task"] == "test_task"
        
    def test_performance_metrics(self, mock_config):
        """Test performance metrics tracking"""
        state_mgr = AgentStateManager(mock_config)
        
        # Record some processing times
        state_mgr.update_state(process_time_ms=100)
        state_mgr.update_state(process_time_ms=200)
        
        metrics = state_mgr.state["performance_metrics"]
        assert metrics["total_messages"] == 2
        assert 100 <= metrics["avg_process_time_ms"] <= 200

class TestMessageProcessor:
    """Tests for MessageProcessor"""
    
    async def test_process_valid_message(self, mock_config, tmp_path):
        """Test processing a valid message"""
        state_mgr = AgentStateManager(mock_config)
        processor = MessageProcessor(mock_config, state_mgr)
        
        # Create test message
        message = tmp_path / "test_message.md"
        message.write_text("# Test Message\nContent")
        
        # Process message
        success = await processor.process_message(message)
        assert success
        
        # Check message was archived
        archived = list(mock_config.processed_dir.glob("*.md"))
        assert len(archived) == 1
        assert archived[0].read_text() == "# Test Message\nContent"
        
    async def test_process_invalid_message(self, mock_config, tmp_path):
        """Test processing an invalid message"""
        state_mgr = AgentStateManager(mock_config)
        processor = MessageProcessor(mock_config, state_mgr)
        
        # Create invalid message (empty)
        message = tmp_path / "invalid.md"
        message.write_text("")
        
        # Process message
        success = await processor.process_message(message)
        assert not success
        
        # Check error was recorded
        assert state_mgr.state["last_error"] is not None

class TestAgentLoop:
    """Tests for AgentLoop"""
    
    async def test_basic_loop_cycle(
        self, mock_config, mock_bus, mock_logger, mock_ui_interactor
    ):
        """Test one cycle of the agent loop"""
        loop = AgentLoop(mock_bus, mock_logger, mock_ui_interactor, mock_config)
        
        # Create test message
        message = mock_config.inbox_dir / "test.md"
        message.parent.mkdir(parents=True, exist_ok=True)
        message.write_text("# Test Message")
        
        # Run one cycle
        await loop.run(run_once=True)
        
        # Check message was processed
        assert not message.exists()
        assert len(list(mock_config.processed_dir.glob("*.md"))) == 1
        
    async def test_error_recovery(
        self, mock_config, mock_bus, mock_logger, mock_ui_interactor
    ):
        """Test error recovery mechanism"""
        loop = AgentLoop(mock_bus, mock_logger, mock_ui_interactor, mock_config)
        
        # Create message that will cause error
        message = mock_config.inbox_dir / "error.md"
        message.parent.mkdir(parents=True, exist_ok=True)
        message.write_text("{{invalid}}")
        
        # Run loop
        await loop.run(run_once=True)
        
        # Check error was logged and recovery attempted
        assert any("ERROR" in log for log in mock_logger.logs)
        assert loop.state_manager.state["recovery_attempts"] > 0
        
    async def test_legacy_inbox_handling(
        self, mock_config, mock_bus, mock_logger, mock_ui_interactor
    ):
        """Test handling of legacy inbox.json"""
        loop = AgentLoop(mock_bus, mock_logger, mock_ui_interactor, mock_config)
        
        # Create legacy inbox
        inbox_data = {
            "messages": [
                {"id": "test-1", "prompt": "Test prompt"}
            ]
        }
        mock_config.inbox_file.parent.mkdir(parents=True, exist_ok=True)
        mock_config.inbox_file.write_text(json.dumps(inbox_data))
        
        # Run loop
        await loop.run(run_once=True)
        
        # Check inbox was processed and archived
        assert not mock_config.inbox_file.exists()
        assert len(list(mock_config.archive_dir.glob("inbox_*.json"))) == 1 