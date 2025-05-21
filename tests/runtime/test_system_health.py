"""
Tests for runtime system health monitoring functionality.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json
import os
from pathlib import Path
import asyncio
from datetime import datetime, timedelta
import time
import psutil

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
    config.health_monitoring = {
        "check_interval": 5.0,
        "alert_thresholds": {
            "cpu_percent": 80,
            "memory_percent": 70,
            "disk_percent": 85,
            "response_time": 1.0,
            "error_rate": 0.05
        },
        "retention_period": 3600
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

@pytest.fixture
def mock_process():
    """Create a mock process for system monitoring."""
    process = MagicMock(spec=psutil.Process)
    process.cpu_percent.return_value = 50
    process.memory_percent.return_value = 60
    return process

def test_health_monitoring_initialization(mock_config, mock_pbm, temp_runtime):
    """Test that runtime initializes health monitoring correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Verify health monitoring initialization
    assert runtime.health_monitoring == mock_config.health_monitoring
    assert runtime.health_metrics == {}
    assert runtime.health_alerts == []
    assert runtime.health_history == []

def test_system_metrics_collection(mock_config, mock_pbm, temp_runtime, mock_process):
    """Test that runtime collects system metrics correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock system metrics
    with patch("psutil.Process", return_value=mock_process), \
         patch("psutil.disk_usage", return_value=MagicMock(percent=75)):
        # Collect metrics
        metrics = runtime._collect_system_metrics()
        
        # Verify metrics
        assert metrics["cpu_percent"] == 50
        assert metrics["memory_percent"] == 60
        assert metrics["disk_percent"] == 75
        
        # Verify metrics were saved
        metrics_path = os.path.join(temp_runtime, "metrics", "system_health.json")
        with open(metrics_path, "r") as f:
            saved_metrics = json.load(f)
            assert saved_metrics == metrics

def test_health_check_thresholds(mock_config, mock_pbm, temp_runtime, mock_process):
    """Test that runtime checks health thresholds correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock high resource usage
    mock_process.cpu_percent.return_value = 90
    mock_process.memory_percent.return_value = 80
    
    with patch("psutil.Process", return_value=mock_process):
        # Check health
        health_status = runtime._check_health_thresholds()
        
        # Verify health status
        assert not health_status["healthy"]
        assert "cpu_percent" in health_status["violations"]
        assert "memory_percent" in health_status["violations"]
        
        # Verify alert was generated
        assert len(runtime.health_alerts) == 1
        assert "Resource usage exceeded" in runtime.health_alerts[0]["message"]

def test_health_alert_generation(mock_config, mock_pbm, temp_runtime):
    """Test that runtime generates health alerts correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Generate alert
    runtime._generate_health_alert("Test alert", {"metric": "value"})
    
    # Verify alert was generated
    assert len(runtime.health_alerts) == 1
    assert runtime.health_alerts[0]["message"] == "Test alert"
    assert runtime.health_alerts[0]["details"] == {"metric": "value"}
    
    # Verify alert was logged
    alert_path = os.path.join(temp_runtime, "logs", "health_alerts.log")
    with open(alert_path, "r") as f:
        alert_log = f.read()
        assert "Test alert" in alert_log

def test_health_metrics_retention(mock_config, mock_pbm, temp_runtime):
    """Test that runtime manages health metrics retention correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Add old metrics
    old_time = datetime.now() - timedelta(hours=2)
    runtime.health_history.append({
        "timestamp": old_time,
        "metrics": {"cpu_percent": 50}
    })
    
    # Add recent metrics
    recent_time = datetime.now() - timedelta(minutes=30)
    runtime.health_history.append({
        "timestamp": recent_time,
        "metrics": {"cpu_percent": 60}
    })
    
    # Clean up old metrics
    runtime._cleanup_health_metrics()
    
    # Verify only recent metrics remain
    assert len(runtime.health_history) == 1
    assert runtime.health_history[0]["metrics"]["cpu_percent"] == 60

@pytest.mark.asyncio
async def test_health_monitoring_loop(mock_config, mock_pbm, temp_runtime, mock_process):
    """Test that runtime health monitoring loop works correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock system metrics
    with patch("psutil.Process", return_value=mock_process):
        # Start monitoring
        monitor_task = asyncio.create_task(runtime._monitor_system_health())
        
        # Wait for a few monitoring cycles
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        # Verify metrics were collected
        assert len(runtime.health_history) > 0
        
        # Verify metrics file was updated
        metrics_path = os.path.join(temp_runtime, "metrics", "system_health.json")
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
            assert "timestamp" in metrics
            assert "cpu_percent" in metrics
            assert "memory_percent" in metrics
            assert "disk_percent" in metrics

def test_health_report_generation(mock_config, mock_pbm, temp_runtime):
    """Test that runtime generates health reports correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Add sample health history
    runtime.health_history.extend([
        {
            "timestamp": datetime.now() - timedelta(minutes=5),
            "metrics": {
                "cpu_percent": 50,
                "memory_percent": 60,
                "disk_percent": 70
            }
        },
        {
            "timestamp": datetime.now() - timedelta(minutes=4),
            "metrics": {
                "cpu_percent": 60,
                "memory_percent": 70,
                "disk_percent": 80
            }
        },
        {
            "timestamp": datetime.now() - timedelta(minutes=3),
            "metrics": {
                "cpu_percent": 70,
                "memory_percent": 80,
                "disk_percent": 90
            }
        }
    ])
    
    # Generate report
    report = runtime._generate_health_report()
    
    # Verify report contents
    assert "summary" in report
    assert "metrics_trends" in report
    assert "alerts" in report
    assert "recommendations" in report
    
    # Verify report was saved
    report_path = os.path.join(temp_runtime, "reports", "system_health_report.json")
    with open(report_path, "r") as f:
        saved_report = json.load(f)
        assert saved_report == report

def test_health_recommendations(mock_config, mock_pbm, temp_runtime):
    """Test that runtime generates health recommendations correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Add sample health metrics
    runtime.health_metrics = {
        "cpu_percent": 90,
        "memory_percent": 85,
        "disk_percent": 95,
        "response_time": 1.5,
        "error_rate": 0.1
    }
    
    # Generate recommendations
    recommendations = runtime._generate_health_recommendations()
    
    # Verify recommendations
    assert len(recommendations) > 0
    assert any("CPU usage" in rec for rec in recommendations)
    assert any("Memory usage" in rec for rec in recommendations)
    assert any("Disk usage" in rec for rec in recommendations)
    assert any("Response time" in rec for rec in recommendations)
    assert any("Error rate" in rec for rec in recommendations) 