"""
Tests for the agent bootstrap runner UI interaction
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from dreamos.tools.agent_bootstrap_runner.config import AgentConfig
from dreamos.tools.agent_bootstrap_runner.ui_interaction import (
    AgentUIInteractor,
    RetryableError,
    UIInteractionError,
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

class TestAgentUIInteractor:
    """Tests for AgentUIInteractor"""
    
    def test_initialization(self, mock_config, mock_logger):
        """Test UI interactor initialization"""
        interactor = AgentUIInteractor(mock_logger, mock_config)
        
        # Test successful initialization
        assert interactor.initialize()
        
        # Check coordinate files were loaded
        assert interactor.coords is not None
        assert interactor.copy_coords is not None
        
    def test_initialization_missing_files(self, mock_config, mock_logger, monkeypatch):
        """Test initialization with missing coordinate files"""
        # Mock coordinate file paths to non-existent files
        monkeypatch.setattr(mock_config, "coords_file", Path("/nonexistent/coords.json"))
        monkeypatch.setattr(mock_config, "copy_coords_file", Path("/nonexistent/copy.json"))
        
        interactor = AgentUIInteractor(mock_logger, mock_config)
        assert not interactor.initialize()
        
        # Check error was logged
        assert any("ERROR" in log for log in mock_logger.logs)
        
    async def test_inject_prompt_success(self, mock_config, mock_logger, mock_bus):
        """Test successful prompt injection"""
        interactor = AgentUIInteractor(mock_logger, mock_config)
        interactor.initialize()
        
        # Mock the injection method
        interactor._inject_to_cursor = AsyncMock(return_value=True)
        
        # Test injection
        success = await interactor.inject_prompt(mock_bus, "Test prompt")
        assert success
        
        # Verify event was published
        assert any(
            event[0] == "agent.inject.ok"
            for event in mock_bus.published_events
        )
        
    async def test_inject_prompt_failure(self, mock_config, mock_logger, mock_bus):
        """Test failed prompt injection"""
        interactor = AgentUIInteractor(mock_logger, mock_config)
        interactor.initialize()
        
        # Mock injection failure
        interactor._inject_to_cursor = AsyncMock(return_value=False)
        
        # Test injection
        success = await interactor.inject_prompt(mock_bus, "Test prompt")
        assert not success
        
        # Verify error event was published
        assert any(
            event[0] == "agent.inject.fail"
            for event in mock_bus.published_events
        )
        
    async def test_retrieve_response_success(self, mock_config, mock_logger, mock_bus):
        """Test successful response retrieval"""
        interactor = AgentUIInteractor(mock_logger, mock_config)
        interactor.initialize()
        
        # Mock successful retrieval
        expected_response = "Test response"
        interactor._retrieve_from_cursor = AsyncMock(return_value=expected_response)
        
        # Test retrieval
        response = await interactor.retrieve_response(mock_bus)
        assert response == expected_response
        
        # Verify event was published
        assert any(
            event[0] == "agent.retrieve.ok"
            for event in mock_bus.published_events
        )
        
    async def test_retrieve_response_retry(self, mock_config, mock_logger, mock_bus):
        """Test response retrieval with retries"""
        interactor = AgentUIInteractor(mock_logger, mock_config)
        interactor.initialize()
        
        # Mock retrieval that fails twice then succeeds
        retrieval_mock = AsyncMock()
        retrieval_mock.side_effect = [
            RetryableError("Retry 1"),
            RetryableError("Retry 2"),
            "Test response"
        ]
        interactor._retrieve_from_cursor = retrieval_mock
        
        # Test retrieval
        response = await interactor.retrieve_response(mock_bus)
        assert response == "Test response"
        
        # Verify retry count
        assert retrieval_mock.call_count == 3
        
    async def test_retrieve_response_max_retries(self, mock_config, mock_logger, mock_bus):
        """Test response retrieval hitting max retries"""
        interactor = AgentUIInteractor(mock_logger, mock_config)
        interactor.initialize()
        
        # Mock retrieval that always fails
        interactor._retrieve_from_cursor = AsyncMock(
            side_effect=RetryableError("Always fails")
        )
        
        # Test retrieval
        response = await interactor.retrieve_response(mock_bus)
        assert response is None
        
        # Verify error event was published
        assert any(
            event[0] == "agent.retrieve.fail"
            for event in mock_bus.published_events
        )
        
    def test_coordinate_validation(self, mock_config, mock_logger):
        """Test coordinate file validation"""
        interactor = AgentUIInteractor(mock_logger, mock_config)
        
        # Test valid coordinates
        valid_coords = {
            "agent_02": {"x": 100, "y": 200}
        }
        assert interactor._validate_coordinates(valid_coords)
        
        # Test invalid coordinates
        invalid_coords = {
            "agent_02": {"x": "invalid"}
        }
        assert not interactor._validate_coordinates(invalid_coords)
        
        # Test missing agent
        missing_agent = {
            "agent_01": {"x": 100, "y": 200}
        }
        assert not interactor._validate_coordinates(missing_agent) 