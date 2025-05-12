"""
Tests for the ValidationEngine class.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from dreamos.core.validation.validation_engine import ValidationEngine, ValidationResult
from dreamos.core.ethos.validator import EthosValidator
from dreamos.core.coordination.event_bus import AgentBus

@pytest.fixture
def mock_config():
    """Create a mock ConfigManager."""
    config = Mock()
    return config

@pytest.fixture
def mock_ethos_validator():
    """Create a mock EthosValidator."""
    validator = Mock(spec=EthosValidator)
    return validator

@pytest.fixture
def mock_event_bus():
    """Create a mock AgentBus."""
    bus = Mock(spec=AgentBus)
    bus.emit = AsyncMock()
    return bus

@pytest.fixture
def validation_engine(mock_config, mock_ethos_validator, mock_event_bus):
    """Create a ValidationEngine instance with mocked dependencies."""
    with patch('dreamos.core.validation.validation_engine.EthosValidator', return_value=mock_ethos_validator), \
         patch('dreamos.core.validation.validation_engine.AgentBus.get_instance', return_value=mock_event_bus):
        engine = ValidationEngine(config=mock_config)
        return engine

@pytest.mark.asyncio
async def test_validate_task_success(validation_engine, mock_ethos_validator):
    """Test successful task validation."""
    # Setup
    task_data = {
        "task_id": "test_task",
        "type": "test_type",
        "data": {"key": "value"}
    }
    
    mock_ethos_validator.validate_task.return_value = ValidationResult(
        is_valid=True,
        issues=[],
        warnings=[],
        context={},
        timestamp=datetime.now()
    )
    
    # Execute
    result = await validation_engine.validate_task(task_data)
    
    # Verify
    assert result.is_valid
    assert len(result.issues) == 0
    assert len(result.warnings) == 0
    mock_ethos_validator.validate_task.assert_called_once_with(task_data)

@pytest.mark.asyncio
async def test_validate_task_failure(validation_engine, mock_ethos_validator, mock_event_bus):
    """Test failed task validation."""
    # Setup
    task_data = {
        "task_id": "test_task",
        "type": "test_type",
        "data": {"key": "value"}
    }
    
    mock_ethos_validator.validate_task.return_value = ValidationResult(
        is_valid=False,
        issues=["Invalid task data"],
        warnings=["Consider fixing task data"],
        context={"error": "test_error"},
        timestamp=datetime.now()
    )
    
    # Execute
    result = await validation_engine.validate_task(task_data)
    
    # Verify
    assert not result.is_valid
    assert len(result.issues) == 1
    assert len(result.warnings) == 1
    mock_ethos_validator.validate_task.assert_called_once_with(task_data)
    mock_event_bus.emit.assert_called_once()

@pytest.mark.asyncio
async def test_validate_agent_improvement_success(validation_engine):
    """Test successful agent improvement validation."""
    # Setup
    agent_id = "test_agent"
    improvement_data = {
        "type": "performance",
        "metrics": {
            "accuracy": 0.95,
            "speed": "2x faster"
        },
        "demonstration": {
            "before": {"accuracy": 0.85},
            "after": {"accuracy": 0.95}
        }
    }
    
    # Execute
    result = await validation_engine.validate_agent_improvement(agent_id, improvement_data)
    
    # Verify
    assert result.is_valid
    assert len(result.issues) == 0
    assert len(result.warnings) == 0
    assert result.context["agent_id"] == agent_id
    assert result.context["improvement_type"] == "performance"

@pytest.mark.asyncio
async def test_validate_agent_improvement_failure(validation_engine):
    """Test failed agent improvement validation."""
    # Setup
    agent_id = "test_agent"
    improvement_data = {
        "type": "performance",
        # Missing metrics and demonstration
    }
    
    # Execute
    result = await validation_engine.validate_agent_improvement(agent_id, improvement_data)
    
    # Verify
    assert not result.is_valid
    assert len(result.issues) == 2
    assert "No improvement metrics provided" in result.issues
    assert "No demonstration of improvement provided" in result.issues

@pytest.mark.asyncio
async def test_validate_system_state(validation_engine):
    """Test system state validation."""
    # Execute
    result = await validation_engine.validate_system_state()
    
    # Verify
    assert result.is_valid
    assert len(result.issues) == 0
    assert len(result.warnings) == 0
    assert isinstance(result.timestamp, datetime) 