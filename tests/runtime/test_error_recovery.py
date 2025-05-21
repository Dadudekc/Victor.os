"""
Tests for runtime error recovery functionality.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json
import os
from pathlib import Path
import asyncio
from datetime import datetime, timedelta
import time

from dreamos.runtime.runtime_manager import RuntimeManager
from dreamos.core.config import AppConfig
from dreamos.core.project_board import ProjectBoardManager

@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = MagicMock(spec=AppConfig)
    config.runtime_id = "test-runtime"
    config.runtime_path = "runtime"
    config.episode_path = "episodes/episode-launch-final-lock.yaml"
    config.error_recovery = {
        "max_retries": 3,
        "retry_delay": 1.0,
        "circuit_breaker": {
            "failure_threshold": 5,
            "reset_timeout": 60
        }
    }
    return config

@pytest.fixture
def mock_pbm():
    """Create a mock project board manager."""
    pbm = MagicMock(spec=ProjectBoardManager)
    pbm.list_working_tasks = MagicMock(return_value=[])
    pbm.claim_task = MagicMock(return_value=True)
    return pbm

@pytest.fixture
def temp_runtime(tmp_path):
    """Create a temporary runtime directory."""
    runtime_path = tmp_path / "runtime"
    runtime_path.mkdir(parents=True)
    return runtime_path

def test_error_recovery_initialization(mock_config, mock_pbm, temp_runtime):
    """Test that runtime initializes error recovery correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Verify error recovery initialization
    assert runtime.error_recovery == mock_config.error_recovery
    assert runtime.retry_counts == {}
    assert runtime.circuit_breaker_states == {}
    assert runtime.error_history == []

def test_retry_mechanism(mock_config, mock_pbm, temp_runtime):
    """Test that runtime retry mechanism works correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock failing operation
    operation = "test_operation"
    error = Exception("Test error")
    
    # Simulate retries
    for _ in range(3):
        try:
            runtime._handle_retry(operation, error)
        except Exception as e:
            assert str(e) == "Max retries exceeded"
    
    # Verify retry counts
    assert runtime.retry_counts[operation] == 3
    assert len(runtime.error_history) == 3
    
    # Verify error was logged
    error_path = os.path.join(temp_runtime, "logs", "errors.log")
    with open(error_path, "r") as f:
        error_log = f.read()
        assert "Test error" in error_log
        assert "test_operation" in error_log

def test_circuit_breaker(mock_config, mock_pbm, temp_runtime):
    """Test that runtime circuit breaker works correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock failing operation
    operation = "test_operation"
    error = Exception("Test error")
    
    # Simulate failures to trigger circuit breaker
    for _ in range(5):
        runtime._handle_circuit_breaker(operation, error)
    
    # Verify circuit breaker state
    assert runtime.circuit_breaker_states[operation]["open"]
    assert runtime.circuit_breaker_states[operation]["failure_count"] == 5
    
    # Try operation when circuit is open
    with pytest.raises(Exception) as exc_info:
        runtime._check_circuit_breaker(operation)
    assert "Circuit breaker is open" in str(exc_info.value)
    
    # Wait for reset timeout
    runtime.circuit_breaker_states[operation]["last_failure_time"] = (
        datetime.now() - timedelta(seconds=61)
    )
    
    # Verify circuit breaker reset
    runtime._check_circuit_breaker(operation)
    assert not runtime.circuit_breaker_states[operation]["open"]
    assert runtime.circuit_breaker_states[operation]["failure_count"] == 0

def test_error_recovery_strategy(mock_config, mock_pbm, temp_runtime):
    """Test that runtime error recovery strategy works correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock failing operation
    operation = "test_operation"
    error = Exception("Test error")
    
    # Test retry strategy
    with pytest.raises(Exception) as exc_info:
        runtime._recover_from_error(operation, error, "retry")
    assert "Max retries exceeded" in str(exc_info.value)
    
    # Test circuit breaker strategy
    with pytest.raises(Exception) as exc_info:
        runtime._recover_from_error(operation, error, "circuit_breaker")
    assert "Circuit breaker is open" in str(exc_info.value)
    
    # Test fallback strategy
    fallback_result = runtime._recover_from_error(operation, error, "fallback")
    assert fallback_result == "fallback_value"
    
    # Verify error was logged
    error_path = os.path.join(temp_runtime, "logs", "errors.log")
    with open(error_path, "r") as f:
        error_log = f.read()
        assert "Test error" in error_log
        assert "test_operation" in error_log

def test_error_handling_chain(mock_config, mock_pbm, temp_runtime):
    """Test that runtime error handling chain works correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock failing operation
    operation = "test_operation"
    error = Exception("Test error")
    
    # Test error handling chain
    result = runtime._handle_error(operation, error)
    
    # Verify error was handled
    assert result == "fallback_value"
    assert len(runtime.error_history) > 0
    
    # Verify error was logged
    error_path = os.path.join(temp_runtime, "logs", "errors.log")
    with open(error_path, "r") as f:
        error_log = f.read()
        assert "Test error" in error_log
        assert "test_operation" in error_log

def test_error_recovery_metrics(mock_config, mock_pbm, temp_runtime):
    """Test that runtime tracks error recovery metrics correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock failing operation
    operation = "test_operation"
    error = Exception("Test error")
    
    # Simulate error recovery
    runtime._handle_error(operation, error)
    
    # Verify metrics were updated
    metrics_path = os.path.join(temp_runtime, "metrics", "error_recovery.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "error_counts" in metrics
        assert "recovery_success" in metrics
        assert "circuit_breaker_states" in metrics

@pytest.mark.asyncio
async def test_error_recovery_loop(mock_config, mock_pbm, temp_runtime):
    """Test that runtime error recovery loop works correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Start error recovery loop
    recovery_task = asyncio.create_task(runtime._monitor_error_recovery())
    
    # Wait for a few monitoring cycles
    await asyncio.sleep(0.1)
    
    # Stop monitoring
    recovery_task.cancel()
    try:
        await recovery_task
    except asyncio.CancelledError:
        pass
    
    # Verify metrics were collected
    metrics_path = os.path.join(temp_runtime, "metrics", "error_recovery.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "timestamp" in metrics
        assert "error_counts" in metrics
        assert "recovery_success" in metrics
        assert "circuit_breaker_states" in metrics

def test_error_recovery_report(mock_config, mock_pbm, temp_runtime):
    """Test that runtime generates error recovery reports correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Add sample error history
    runtime.error_history.extend([
        {
            "timestamp": datetime.now() - timedelta(minutes=5),
            "operation": "test_operation",
            "error": "Test error 1",
            "recovery_strategy": "retry",
            "success": True
        },
        {
            "timestamp": datetime.now() - timedelta(minutes=4),
            "operation": "test_operation",
            "error": "Test error 2",
            "recovery_strategy": "circuit_breaker",
            "success": False
        },
        {
            "timestamp": datetime.now() - timedelta(minutes=3),
            "operation": "test_operation",
            "error": "Test error 3",
            "recovery_strategy": "fallback",
            "success": True
        }
    ])
    
    # Generate report
    report = runtime._generate_error_recovery_report()
    
    # Verify report contents
    assert "summary" in report
    assert "test_operation" in report["summary"]
    assert "error_count" in report["summary"]["test_operation"]
    assert "recovery_success_rate" in report["summary"]["test_operation"]
    assert "circuit_breaker_states" in report["summary"]
    
    # Verify report was saved
    report_path = os.path.join(temp_runtime, "reports", "error_recovery_report.json")
    with open(report_path, "r") as f:
        saved_report = json.load(f)
        assert saved_report == report 