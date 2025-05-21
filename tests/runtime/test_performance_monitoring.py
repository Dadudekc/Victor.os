"""
Tests for runtime performance monitoring functionality.
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
    config.performance_metrics = {
        "sampling_interval": 1.0,
        "retention_period": 3600,
        "alert_thresholds": {
            "response_time": 1.0,
            "error_rate": 0.05,
            "resource_usage": 0.8
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

def test_performance_metrics_initialization(mock_config, mock_pbm, temp_runtime):
    """Test that runtime initializes performance metrics correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Verify performance metrics initialization
    assert runtime.performance_metrics == mock_config.performance_metrics
    assert runtime.metrics_history == []
    assert runtime.alert_thresholds == mock_config.performance_metrics["alert_thresholds"]

def test_response_time_tracking(mock_config, mock_pbm, temp_runtime):
    """Test that runtime tracks response times correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Simulate operation with timing
    with runtime._track_response_time("test_operation"):
        time.sleep(0.1)
    
    # Verify response time was recorded
    assert len(runtime.metrics_history) == 1
    assert runtime.metrics_history[0]["operation"] == "test_operation"
    assert runtime.metrics_history[0]["response_time"] >= 0.1
    
    # Verify metrics were updated
    metrics_path = os.path.join(temp_runtime, "metrics", "performance.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "response_times" in metrics
        assert metrics["response_times"]["test_operation"] >= 0.1

def test_error_rate_tracking(mock_config, mock_pbm, temp_runtime):
    """Test that runtime tracks error rates correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Simulate operations with errors
    for _ in range(10):
        try:
            if _ % 2 == 0:
                raise Exception("Test error")
        except Exception:
            runtime._track_error("test_operation")
    
    # Verify error rate was calculated
    error_rate = runtime._calculate_error_rate("test_operation")
    assert error_rate == 0.5  # 5 errors out of 10 operations
    
    # Verify metrics were updated
    metrics_path = os.path.join(temp_runtime, "metrics", "performance.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "error_rates" in metrics
        assert metrics["error_rates"]["test_operation"] == 0.5

def test_resource_usage_tracking(mock_config, mock_pbm, temp_runtime):
    """Test that runtime tracks resource usage correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock resource usage
    runtime.resource_usage = {
        "cpu_percent": 70,
        "memory_percent": 60,
        "disk_percent": 50
    }
    
    # Track resource usage
    runtime._track_resource_usage()
    
    # Verify resource usage was recorded
    assert len(runtime.metrics_history) == 1
    assert runtime.metrics_history[0]["resource_usage"] == runtime.resource_usage
    
    # Verify metrics were updated
    metrics_path = os.path.join(temp_runtime, "metrics", "performance.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "resource_usage" in metrics
        assert metrics["resource_usage"] == runtime.resource_usage

def test_performance_alert_generation(mock_config, mock_pbm, temp_runtime):
    """Test that runtime generates performance alerts correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Simulate high response time
    with runtime._track_response_time("test_operation"):
        time.sleep(1.5)  # Exceeds 1.0s threshold
    
    # Verify alert was generated
    assert len(runtime.alerts) == 1
    assert "response_time" in runtime.alerts[0]
    assert runtime.alerts[0]["operation"] == "test_operation"
    
    # Verify alert was logged
    alert_path = os.path.join(temp_runtime, "logs", "alerts.log")
    with open(alert_path, "r") as f:
        alert_log = f.read()
        assert "High response time" in alert_log
        assert "test_operation" in alert_log

def test_metrics_retention(mock_config, mock_pbm, temp_runtime):
    """Test that runtime manages metrics retention correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Add old metrics
    old_time = datetime.now() - timedelta(hours=2)
    runtime.metrics_history.append({
        "timestamp": old_time,
        "operation": "old_operation",
        "response_time": 0.5
    })
    
    # Add recent metrics
    recent_time = datetime.now() - timedelta(minutes=30)
    runtime.metrics_history.append({
        "timestamp": recent_time,
        "operation": "recent_operation",
        "response_time": 0.5
    })
    
    # Clean up old metrics
    runtime._cleanup_old_metrics()
    
    # Verify only recent metrics remain
    assert len(runtime.metrics_history) == 1
    assert runtime.metrics_history[0]["operation"] == "recent_operation"

@pytest.mark.asyncio
async def test_performance_monitoring_loop(mock_config, mock_pbm, temp_runtime):
    """Test that runtime monitoring loop works correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Start monitoring
    monitor_task = asyncio.create_task(runtime._monitor_performance())
    
    # Wait for a few monitoring cycles
    await asyncio.sleep(0.1)
    
    # Stop monitoring
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    
    # Verify metrics were collected
    assert len(runtime.metrics_history) > 0
    
    # Verify metrics file was updated
    metrics_path = os.path.join(temp_runtime, "metrics", "performance.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "timestamp" in metrics
        assert "response_times" in metrics
        assert "error_rates" in metrics
        assert "resource_usage" in metrics

def test_performance_report_generation(mock_config, mock_pbm, temp_runtime):
    """Test that runtime generates performance reports correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Add sample metrics
    runtime.metrics_history.extend([
        {
            "timestamp": datetime.now() - timedelta(minutes=5),
            "operation": "test_operation",
            "response_time": 0.5,
            "error": False
        },
        {
            "timestamp": datetime.now() - timedelta(minutes=4),
            "operation": "test_operation",
            "response_time": 0.6,
            "error": True
        },
        {
            "timestamp": datetime.now() - timedelta(minutes=3),
            "operation": "test_operation",
            "response_time": 0.7,
            "error": False
        }
    ])
    
    # Generate report
    report = runtime._generate_performance_report()
    
    # Verify report contents
    assert "summary" in report
    assert "test_operation" in report["summary"]
    assert "average_response_time" in report["summary"]["test_operation"]
    assert "error_rate" in report["summary"]["test_operation"]
    assert "resource_usage" in report["summary"]
    
    # Verify report was saved
    report_path = os.path.join(temp_runtime, "reports", "performance_report.json")
    with open(report_path, "r") as f:
        saved_report = json.load(f)
        assert saved_report == report 