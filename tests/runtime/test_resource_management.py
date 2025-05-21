"""
Tests for runtime resource management functionality.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json
import os
from pathlib import Path
import asyncio
from datetime import datetime, timedelta
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
    config.resource_limits = {
        "cpu_percent": 80,
        "memory_percent": 70,
        "disk_percent": 85,
        "max_agents": 10
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
    """Create a mock process for resource monitoring."""
    process = MagicMock(spec=psutil.Process)
    process.cpu_percent.return_value = 50
    process.memory_percent.return_value = 60
    return process

def test_resource_limits_initialization(mock_config, mock_pbm, temp_runtime):
    """Test that runtime initializes resource limits correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Verify resource limits
    assert runtime.resource_limits == mock_config.resource_limits
    assert runtime.resource_usage == {}
    assert runtime.active_agents == []

def test_cpu_usage_monitoring(mock_config, mock_pbm, temp_runtime, mock_process):
    """Test that runtime monitors CPU usage correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock process monitoring
    with patch("psutil.Process", return_value=mock_process):
        # Monitor CPU usage
        cpu_usage = runtime._monitor_cpu_usage()
        
        # Verify CPU usage
        assert cpu_usage == 50
        assert runtime.resource_usage["cpu_percent"] == 50
        
        # Verify metrics were updated
        metrics_path = os.path.join(temp_runtime, "metrics", "performance.json")
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
            assert metrics["cpu_usage"] == 50

def test_memory_usage_monitoring(mock_config, mock_pbm, temp_runtime, mock_process):
    """Test that runtime monitors memory usage correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock process monitoring
    with patch("psutil.Process", return_value=mock_process):
        # Monitor memory usage
        memory_usage = runtime._monitor_memory_usage()
        
        # Verify memory usage
        assert memory_usage == 60
        assert runtime.resource_usage["memory_percent"] == 60
        
        # Verify metrics were updated
        metrics_path = os.path.join(temp_runtime, "metrics", "performance.json")
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
            assert metrics["memory_usage"] == 60

def test_disk_usage_monitoring(mock_config, mock_pbm, temp_runtime):
    """Test that runtime monitors disk usage correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock disk usage
    with patch("psutil.disk_usage", return_value=MagicMock(percent=75)):
        # Monitor disk usage
        disk_usage = runtime._monitor_disk_usage()
        
        # Verify disk usage
        assert disk_usage == 75
        assert runtime.resource_usage["disk_percent"] == 75
        
        # Verify metrics were updated
        metrics_path = os.path.join(temp_runtime, "metrics", "performance.json")
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
            assert metrics["disk_usage"] == 75

def test_resource_limit_enforcement(mock_config, mock_pbm, temp_runtime, mock_process):
    """Test that runtime enforces resource limits correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock high resource usage
    mock_process.cpu_percent.return_value = 90
    mock_process.memory_percent.return_value = 80
    
    with patch("psutil.Process", return_value=mock_process):
        # Check resource limits
        with pytest.raises(RuntimeError) as exc_info:
            runtime._check_resource_limits()
        
        assert "Resource limits exceeded" in str(exc_info.value)
        assert runtime.error_count == 1

def test_agent_resource_allocation(mock_config, mock_pbm, temp_runtime):
    """Test that runtime allocates resources to agents correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Add test agent
    test_agent = {"id": "agent1", "resources": {"cpu": 10, "memory": 20}}
    runtime.active_agents.append(test_agent)
    
    # Verify resource allocation
    assert runtime.resource_usage["agent_count"] == 1
    assert runtime.resource_usage["total_cpu"] == 10
    assert runtime.resource_usage["total_memory"] == 20
    
    # Verify metrics were updated
    metrics_path = os.path.join(temp_runtime, "metrics", "performance.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert metrics["active_agents"] == 1
        assert metrics["agent_cpu_usage"] == 10
        assert metrics["agent_memory_usage"] == 20

def test_resource_cleanup(mock_config, mock_pbm, temp_runtime):
    """Test that runtime cleans up resources correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Add test agents
    test_agents = [
        {"id": "agent1", "resources": {"cpu": 10, "memory": 20}},
        {"id": "agent2", "resources": {"cpu": 15, "memory": 25}}
    ]
    runtime.active_agents.extend(test_agents)
    
    # Clean up resources
    runtime._cleanup_resources()
    
    # Verify resources were cleaned up
    assert runtime.active_agents == []
    assert runtime.resource_usage["agent_count"] == 0
    assert runtime.resource_usage["total_cpu"] == 0
    assert runtime.resource_usage["total_memory"] == 0
    
    # Verify metrics were updated
    metrics_path = os.path.join(temp_runtime, "metrics", "performance.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert metrics["active_agents"] == 0
        assert metrics["agent_cpu_usage"] == 0
        assert metrics["agent_memory_usage"] == 0

@pytest.mark.asyncio
async def test_resource_monitoring_loop(mock_config, mock_pbm, temp_runtime, mock_process):
    """Test that runtime monitoring loop works correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock process monitoring
    with patch("psutil.Process", return_value=mock_process):
        # Start monitoring
        monitor_task = asyncio.create_task(runtime._monitor_resources())
        
        # Wait for a few monitoring cycles
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        # Verify metrics were updated
        metrics_path = os.path.join(temp_runtime, "metrics", "performance.json")
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
            assert "cpu_usage" in metrics
            assert "memory_usage" in metrics
            assert "disk_usage" in metrics 