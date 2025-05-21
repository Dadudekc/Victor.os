"""
Tests for runtime chaos testing scenarios.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json
import os
from pathlib import Path
import asyncio
from datetime import datetime, timedelta
import time
import random

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
    config.chaos_testing = {
        "scenarios": {
            "network_latency": {
                "type": "network",
                "latency_ms": 1000,
                "duration": 300
            },
            "network_packet_loss": {
                "type": "network",
                "packet_loss_percent": 20,
                "duration": 300
            },
            "cpu_spike": {
                "type": "resource",
                "cpu_percent": 100,
                "duration": 60
            },
            "memory_leak": {
                "type": "resource",
                "memory_growth_mb": 100,
                "duration": 300
            },
            "disk_io": {
                "type": "resource",
                "io_operations": 1000,
                "duration": 300
            },
            "process_crash": {
                "type": "process",
                "crash_interval": 60,
                "duration": 300
            },
            "random_failures": {
                "type": "random",
                "failure_rate": 0.1,
                "duration": 300
            }
        },
        "metrics": {
            "recovery_time_threshold": 30,
            "error_rate_threshold": 0.1,
            "availability_threshold": 0.95
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

def test_chaos_scenario_initialization(mock_config, mock_pbm, temp_runtime):
    """Test that runtime initializes chaos testing scenarios correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Verify chaos testing initialization
    assert runtime.chaos_testing == mock_config.chaos_testing
    assert runtime.active_scenario is None
    assert runtime.scenario_metrics == {}
    assert runtime.scenario_history == []

def test_network_latency_scenario(mock_config, mock_pbm, temp_runtime):
    """Test that runtime handles network latency scenario correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Get network latency scenario
    scenario = runtime.chaos_testing["scenarios"]["network_latency"]
    
    # Run scenario
    runtime._run_chaos_scenario("network_latency", scenario)
    
    # Verify scenario metrics
    assert runtime.scenario_metrics["type"] == "network"
    assert runtime.scenario_metrics["latency_ms"] == scenario["latency_ms"]
    assert runtime.scenario_metrics["duration"] == scenario["duration"]
    
    # Verify metrics were saved
    metrics_path = os.path.join(temp_runtime, "metrics", "chaos_testing.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "network_latency" in metrics
        assert metrics["network_latency"]["latency_ms"] == scenario["latency_ms"]

def test_network_packet_loss_scenario(mock_config, mock_pbm, temp_runtime):
    """Test that runtime handles network packet loss scenario correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Get network packet loss scenario
    scenario = runtime.chaos_testing["scenarios"]["network_packet_loss"]
    
    # Run scenario
    runtime._run_chaos_scenario("network_packet_loss", scenario)
    
    # Verify scenario metrics
    assert runtime.scenario_metrics["type"] == "network"
    assert runtime.scenario_metrics["packet_loss_percent"] == scenario["packet_loss_percent"]
    assert runtime.scenario_metrics["duration"] == scenario["duration"]
    
    # Verify metrics were saved
    metrics_path = os.path.join(temp_runtime, "metrics", "chaos_testing.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "network_packet_loss" in metrics
        assert metrics["network_packet_loss"]["packet_loss_percent"] == scenario["packet_loss_percent"]

def test_cpu_spike_scenario(mock_config, mock_pbm, temp_runtime):
    """Test that runtime handles CPU spike scenario correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Get CPU spike scenario
    scenario = runtime.chaos_testing["scenarios"]["cpu_spike"]
    
    # Run scenario
    runtime._run_chaos_scenario("cpu_spike", scenario)
    
    # Verify scenario metrics
    assert runtime.scenario_metrics["type"] == "resource"
    assert runtime.scenario_metrics["cpu_percent"] == scenario["cpu_percent"]
    assert runtime.scenario_metrics["duration"] == scenario["duration"]
    
    # Verify metrics were saved
    metrics_path = os.path.join(temp_runtime, "metrics", "chaos_testing.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "cpu_spike" in metrics
        assert metrics["cpu_spike"]["cpu_percent"] == scenario["cpu_percent"]

def test_memory_leak_scenario(mock_config, mock_pbm, temp_runtime):
    """Test that runtime handles memory leak scenario correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Get memory leak scenario
    scenario = runtime.chaos_testing["scenarios"]["memory_leak"]
    
    # Run scenario
    runtime._run_chaos_scenario("memory_leak", scenario)
    
    # Verify scenario metrics
    assert runtime.scenario_metrics["type"] == "resource"
    assert runtime.scenario_metrics["memory_growth_mb"] == scenario["memory_growth_mb"]
    assert runtime.scenario_metrics["duration"] == scenario["duration"]
    
    # Verify metrics were saved
    metrics_path = os.path.join(temp_runtime, "metrics", "chaos_testing.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "memory_leak" in metrics
        assert metrics["memory_leak"]["memory_growth_mb"] == scenario["memory_growth_mb"]

def test_disk_io_scenario(mock_config, mock_pbm, temp_runtime):
    """Test that runtime handles disk I/O scenario correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Get disk I/O scenario
    scenario = runtime.chaos_testing["scenarios"]["disk_io"]
    
    # Run scenario
    runtime._run_chaos_scenario("disk_io", scenario)
    
    # Verify scenario metrics
    assert runtime.scenario_metrics["type"] == "resource"
    assert runtime.scenario_metrics["io_operations"] == scenario["io_operations"]
    assert runtime.scenario_metrics["duration"] == scenario["duration"]
    
    # Verify metrics were saved
    metrics_path = os.path.join(temp_runtime, "metrics", "chaos_testing.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "disk_io" in metrics
        assert metrics["disk_io"]["io_operations"] == scenario["io_operations"]

def test_process_crash_scenario(mock_config, mock_pbm, temp_runtime):
    """Test that runtime handles process crash scenario correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Get process crash scenario
    scenario = runtime.chaos_testing["scenarios"]["process_crash"]
    
    # Run scenario
    runtime._run_chaos_scenario("process_crash", scenario)
    
    # Verify scenario metrics
    assert runtime.scenario_metrics["type"] == "process"
    assert runtime.scenario_metrics["crash_interval"] == scenario["crash_interval"]
    assert runtime.scenario_metrics["duration"] == scenario["duration"]
    
    # Verify metrics were saved
    metrics_path = os.path.join(temp_runtime, "metrics", "chaos_testing.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "process_crash" in metrics
        assert metrics["process_crash"]["crash_interval"] == scenario["crash_interval"]

def test_random_failures_scenario(mock_config, mock_pbm, temp_runtime):
    """Test that runtime handles random failures scenario correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Get random failures scenario
    scenario = runtime.chaos_testing["scenarios"]["random_failures"]
    
    # Run scenario
    runtime._run_chaos_scenario("random_failures", scenario)
    
    # Verify scenario metrics
    assert runtime.scenario_metrics["type"] == "random"
    assert runtime.scenario_metrics["failure_rate"] == scenario["failure_rate"]
    assert runtime.scenario_metrics["duration"] == scenario["duration"]
    
    # Verify metrics were saved
    metrics_path = os.path.join(temp_runtime, "metrics", "chaos_testing.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "random_failures" in metrics
        assert metrics["random_failures"]["failure_rate"] == scenario["failure_rate"]

def test_chaos_scenario_metrics(mock_config, mock_pbm, temp_runtime):
    """Test that runtime collects chaos scenario metrics correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Run network latency scenario
    scenario = runtime.chaos_testing["scenarios"]["network_latency"]
    runtime._run_chaos_scenario("network_latency", scenario)
    
    # Verify metrics collection
    metrics = runtime._collect_scenario_metrics()
    assert "recovery_times" in metrics
    assert "error_rates" in metrics
    assert "availability" in metrics
    assert "impact_metrics" in metrics
    
    # Verify metrics were saved
    metrics_path = os.path.join(temp_runtime, "metrics", "chaos_testing.json")
    with open(metrics_path, "r") as f:
        saved_metrics = json.load(f)
        assert saved_metrics["network_latency"] == metrics

def test_chaos_scenario_thresholds(mock_config, mock_pbm, temp_runtime):
    """Test that runtime checks chaos scenario thresholds correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock high metrics
    runtime.scenario_metrics = {
        "recovery_time": 45,
        "error_rate": 0.15,
        "availability": 0.90
    }
    
    # Check thresholds
    violations = runtime._check_scenario_thresholds()
    
    # Verify threshold violations
    assert "recovery_time" in violations
    assert "error_rate" in violations
    assert "availability" in violations
    
    # Verify alerts were generated
    assert len(runtime.scenario_alerts) > 0
    assert any("Recovery time" in alert["message"] for alert in runtime.scenario_alerts)
    assert any("Error rate" in alert["message"] for alert in runtime.scenario_alerts)
    assert any("Availability" in alert["message"] for alert in runtime.scenario_alerts)

@pytest.mark.asyncio
async def test_chaos_scenario_execution(mock_config, mock_pbm, temp_runtime):
    """Test that runtime executes chaos scenarios correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Start scenario execution
    execution_task = asyncio.create_task(runtime._execute_chaos_scenarios())
    
    # Wait for a few scenarios
    await asyncio.sleep(0.1)
    
    # Stop execution
    execution_task.cancel()
    try:
        await execution_task
    except asyncio.CancelledError:
        pass
    
    # Verify scenarios were executed
    assert len(runtime.scenario_history) > 0
    
    # Verify metrics were collected
    metrics_path = os.path.join(temp_runtime, "metrics", "chaos_testing.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "timestamp" in metrics
        assert "scenarios" in metrics

def test_chaos_scenario_report(mock_config, mock_pbm, temp_runtime):
    """Test that runtime generates chaos scenario reports correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Add sample scenario history
    runtime.scenario_history.extend([
        {
            "timestamp": datetime.now() - timedelta(minutes=5),
            "scenario": "network_latency",
            "metrics": {
                "recovery_time": 25,
                "error_rate": 0.05,
                "availability": 0.98
            }
        },
        {
            "timestamp": datetime.now() - timedelta(minutes=4),
            "scenario": "cpu_spike",
            "metrics": {
                "recovery_time": 35,
                "error_rate": 0.08,
                "availability": 0.96
            }
        },
        {
            "timestamp": datetime.now() - timedelta(minutes=3),
            "scenario": "memory_leak",
            "metrics": {
                "recovery_time": 40,
                "error_rate": 0.12,
                "availability": 0.94
            }
        }
    ])
    
    # Generate report
    report = runtime._generate_chaos_report()
    
    # Verify report contents
    assert "summary" in report
    assert "scenario_metrics" in report
    assert "threshold_violations" in report
    assert "recommendations" in report
    
    # Verify report was saved
    report_path = os.path.join(temp_runtime, "reports", "chaos_testing_report.json")
    with open(report_path, "r") as f:
        saved_report = json.load(f)
        assert saved_report == report

def test_chaos_scenario_recommendations(mock_config, mock_pbm, temp_runtime):
    """Test that runtime generates chaos scenario recommendations correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Add sample scenario metrics
    runtime.scenario_metrics = {
        "network_latency": {
            "recovery_time": 25,
            "error_rate": 0.05,
            "availability": 0.98
        },
        "cpu_spike": {
            "recovery_time": 35,
            "error_rate": 0.08,
            "availability": 0.96
        },
        "memory_leak": {
            "recovery_time": 40,
            "error_rate": 0.12,
            "availability": 0.94
        }
    }
    
    # Generate recommendations
    recommendations = runtime._generate_chaos_recommendations()
    
    # Verify recommendations
    assert len(recommendations) > 0
    assert any("Recovery time" in rec for rec in recommendations)
    assert any("Error rate" in rec for rec in recommendations)
    assert any("Availability" in rec for rec in recommendations)
    assert any("Resilience" in rec for rec in recommendations) 