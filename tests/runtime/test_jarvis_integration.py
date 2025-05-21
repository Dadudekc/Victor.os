"""
Tests for Jarvis integration functionality.
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
from dreamos.core.jarvis import JarvisClient

@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = MagicMock(spec=AppConfig)
    config.runtime_id = "test-runtime"
    config.runtime_path = "runtime"
    config.episode_path = "episodes/episode-launch-final-lock.yaml"
    config.jarvis = {
        "api_url": "http://localhost:8000",
        "api_key": "test-key",
        "sync_interval": 5.0,
        "max_retries": 3
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
def mock_jarvis():
    """Create a mock Jarvis client."""
    jarvis = MagicMock(spec=JarvisClient)
    jarvis.sync_state = AsyncMock(return_value=True)
    jarvis.get_metrics = AsyncMock(return_value={})
    jarvis.update_metrics = AsyncMock(return_value=True)
    jarvis.report_error = AsyncMock(return_value=True)
    return jarvis

@pytest.fixture
def temp_runtime(tmp_path):
    """Create a temporary runtime directory."""
    runtime_path = tmp_path / "runtime"
    runtime_path.mkdir(parents=True)
    return runtime_path

def test_jarvis_initialization(mock_config, mock_pbm, temp_runtime, mock_jarvis):
    """Test that runtime initializes Jarvis integration correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    runtime.jarvis = mock_jarvis
    
    # Verify Jarvis initialization
    assert runtime.jarvis_config == mock_config.jarvis
    assert runtime.jarvis_sync_interval == mock_config.jarvis["sync_interval"]
    assert runtime.jarvis_retry_count == 0

@pytest.mark.asyncio
async def test_jarvis_state_sync(mock_config, mock_pbm, temp_runtime, mock_jarvis):
    """Test that runtime syncs state with Jarvis correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    runtime.jarvis = mock_jarvis
    
    # Mock runtime state
    runtime.state = {
        "status": "running",
        "active_agents": 5,
        "current_task": "test_task"
    }
    
    # Sync state with Jarvis
    await runtime._sync_jarvis_state()
    
    # Verify state was synced
    mock_jarvis.sync_state.assert_called_once_with(runtime.state)
    
    # Verify metrics were updated
    metrics_path = os.path.join(temp_runtime, "metrics", "jarvis_sync.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "last_sync" in metrics
        assert "sync_success" in metrics

@pytest.mark.asyncio
async def test_jarvis_metrics_sync(mock_config, mock_pbm, temp_runtime, mock_jarvis):
    """Test that runtime syncs metrics with Jarvis correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    runtime.jarvis = mock_jarvis
    
    # Mock runtime metrics
    runtime.metrics = {
        "cpu_usage": 50,
        "memory_usage": 60,
        "active_agents": 5
    }
    
    # Sync metrics with Jarvis
    await runtime._sync_jarvis_metrics()
    
    # Verify metrics were synced
    mock_jarvis.update_metrics.assert_called_once_with(runtime.metrics)
    
    # Verify metrics were updated
    metrics_path = os.path.join(temp_runtime, "metrics", "jarvis_sync.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "last_metrics_sync" in metrics
        assert "metrics_sync_success" in metrics

@pytest.mark.asyncio
async def test_jarvis_error_reporting(mock_config, mock_pbm, temp_runtime, mock_jarvis):
    """Test that runtime reports errors to Jarvis correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    runtime.jarvis = mock_jarvis
    
    # Mock error
    error = Exception("Test error")
    
    # Report error to Jarvis
    await runtime._report_jarvis_error(error)
    
    # Verify error was reported
    mock_jarvis.report_error.assert_called_once_with(
        error=str(error),
        runtime_id=runtime.runtime_id,
        timestamp=ANY
    )
    
    # Verify error was logged
    error_path = os.path.join(temp_runtime, "logs", "jarvis_errors.log")
    with open(error_path, "r") as f:
        error_log = f.read()
        assert "Test error" in error_log

@pytest.mark.asyncio
async def test_jarvis_sync_retry(mock_config, mock_pbm, temp_runtime, mock_jarvis):
    """Test that runtime retries Jarvis sync on failure."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    runtime.jarvis = mock_jarvis
    
    # Mock sync failure then success
    mock_jarvis.sync_state.side_effect = [
        Exception("Sync failed"),
        Exception("Sync failed"),
        True
    ]
    
    # Attempt sync with retry
    await runtime._sync_jarvis_with_retry()
    
    # Verify retries were attempted
    assert mock_jarvis.sync_state.call_count == 3
    assert runtime.jarvis_retry_count == 2
    
    # Verify metrics were updated
    metrics_path = os.path.join(temp_runtime, "metrics", "jarvis_sync.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "sync_retries" in metrics
        assert metrics["sync_retries"] == 2

@pytest.mark.asyncio
async def test_jarvis_sync_loop(mock_config, mock_pbm, temp_runtime, mock_jarvis):
    """Test that runtime Jarvis sync loop works correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    runtime.jarvis = mock_jarvis
    
    # Start sync loop
    sync_task = asyncio.create_task(runtime._monitor_jarvis_sync())
    
    # Wait for a few sync cycles
    await asyncio.sleep(0.1)
    
    # Stop sync loop
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass
    
    # Verify sync was attempted
    assert mock_jarvis.sync_state.call_count > 0
    
    # Verify metrics were updated
    metrics_path = os.path.join(temp_runtime, "metrics", "jarvis_sync.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "last_sync" in metrics
        assert "sync_success" in metrics

def test_jarvis_metrics_collection(mock_config, mock_pbm, temp_runtime, mock_jarvis):
    """Test that runtime collects Jarvis metrics correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    runtime.jarvis = mock_jarvis
    
    # Mock Jarvis metrics
    mock_jarvis.get_metrics.return_value = {
        "system_health": 95,
        "active_tasks": 10,
        "completed_tasks": 100
    }
    
    # Collect metrics
    metrics = runtime._collect_jarvis_metrics()
    
    # Verify metrics were collected
    assert metrics == mock_jarvis.get_metrics.return_value
    
    # Verify metrics were saved
    metrics_path = os.path.join(temp_runtime, "metrics", "jarvis_metrics.json")
    with open(metrics_path, "r") as f:
        saved_metrics = json.load(f)
        assert saved_metrics == metrics

def test_jarvis_health_check(mock_config, mock_pbm, temp_runtime, mock_jarvis):
    """Test that runtime performs Jarvis health check correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    runtime.jarvis = mock_jarvis
    
    # Mock Jarvis health metrics
    mock_jarvis.get_metrics.return_value = {
        "system_health": 95,
        "active_tasks": 10,
        "completed_tasks": 100
    }
    
    # Perform health check
    health_status = runtime._check_jarvis_health()
    
    # Verify health check
    assert health_status["healthy"]
    assert health_status["system_health"] == 95
    assert health_status["active_tasks"] == 10
    
    # Verify health check was logged
    health_path = os.path.join(temp_runtime, "logs", "jarvis_health.log")
    with open(health_path, "r") as f:
        health_log = f.read()
        assert "System health: 95" in health_log
        assert "Active tasks: 10" in health_log

def test_jarvis_integration_report(mock_config, mock_pbm, temp_runtime, mock_jarvis):
    """Test that runtime generates Jarvis integration report correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    runtime.jarvis = mock_jarvis
    
    # Add sample sync history
    runtime.jarvis_sync_history.extend([
        {
            "timestamp": datetime.now() - timedelta(minutes=5),
            "success": True,
            "duration": 0.1
        },
        {
            "timestamp": datetime.now() - timedelta(minutes=4),
            "success": False,
            "error": "Sync failed"
        },
        {
            "timestamp": datetime.now() - timedelta(minutes=3),
            "success": True,
            "duration": 0.2
        }
    ])
    
    # Generate report
    report = runtime._generate_jarvis_report()
    
    # Verify report contents
    assert "summary" in report
    assert "sync_success_rate" in report["summary"]
    assert "average_sync_duration" in report["summary"]
    assert "error_count" in report["summary"]
    
    # Verify report was saved
    report_path = os.path.join(temp_runtime, "reports", "jarvis_integration_report.json")
    with open(report_path, "r") as f:
        saved_report = json.load(f)
        assert saved_report == report 