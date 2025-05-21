"""
Tests for runtime load testing scenarios.
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
    config.load_testing = {
        "scenarios": {
            "normal_load": {
                "agent_count": 10,
                "message_rate": 100,
                "duration": 300
            },
            "high_load": {
                "agent_count": 50,
                "message_rate": 500,
                "duration": 300
            },
            "peak_load": {
                "agent_count": 100,
                "message_rate": 1000,
                "duration": 300
            }
        },
        "metrics": {
            "response_time_threshold": 1.0,
            "error_rate_threshold": 0.05,
            "resource_usage_threshold": 0.8
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

def test_load_scenario_initialization(mock_config, mock_pbm, temp_runtime):
    """Test that runtime initializes load testing scenarios correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Verify load testing initialization
    assert runtime.load_testing == mock_config.load_testing
    assert runtime.active_scenario is None
    assert runtime.scenario_metrics == {}
    assert runtime.scenario_history == []

def test_normal_load_scenario(mock_config, mock_pbm, temp_runtime):
    """Test that runtime handles normal load scenario correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Get normal load scenario
    scenario = runtime.load_testing["scenarios"]["normal_load"]
    
    # Run scenario
    runtime._run_load_scenario("normal_load", scenario)
    
    # Verify scenario metrics
    assert runtime.scenario_metrics["agent_count"] == scenario["agent_count"]
    assert runtime.scenario_metrics["message_count"] > 0
    assert runtime.scenario_metrics["duration"] == scenario["duration"]
    
    # Verify metrics were saved
    metrics_path = os.path.join(temp_runtime, "metrics", "load_testing.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "normal_load" in metrics
        assert metrics["normal_load"]["agent_count"] == scenario["agent_count"]

def test_high_load_scenario(mock_config, mock_pbm, temp_runtime):
    """Test that runtime handles high load scenario correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Get high load scenario
    scenario = runtime.load_testing["scenarios"]["high_load"]
    
    # Run scenario
    runtime._run_load_scenario("high_load", scenario)
    
    # Verify scenario metrics
    assert runtime.scenario_metrics["agent_count"] == scenario["agent_count"]
    assert runtime.scenario_metrics["message_count"] > 0
    assert runtime.scenario_metrics["duration"] == scenario["duration"]
    
    # Verify metrics were saved
    metrics_path = os.path.join(temp_runtime, "metrics", "load_testing.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "high_load" in metrics
        assert metrics["high_load"]["agent_count"] == scenario["agent_count"]

def test_peak_load_scenario(mock_config, mock_pbm, temp_runtime):
    """Test that runtime handles peak load scenario correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Get peak load scenario
    scenario = runtime.load_testing["scenarios"]["peak_load"]
    
    # Run scenario
    runtime._run_load_scenario("peak_load", scenario)
    
    # Verify scenario metrics
    assert runtime.scenario_metrics["agent_count"] == scenario["agent_count"]
    assert runtime.scenario_metrics["message_count"] > 0
    assert runtime.scenario_metrics["duration"] == scenario["duration"]
    
    # Verify metrics were saved
    metrics_path = os.path.join(temp_runtime, "metrics", "load_testing.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "peak_load" in metrics
        assert metrics["peak_load"]["agent_count"] == scenario["agent_count"]

def test_load_scenario_metrics(mock_config, mock_pbm, temp_runtime):
    """Test that runtime collects load scenario metrics correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Run normal load scenario
    scenario = runtime.load_testing["scenarios"]["normal_load"]
    runtime._run_load_scenario("normal_load", scenario)
    
    # Verify metrics collection
    metrics = runtime._collect_scenario_metrics()
    assert "response_times" in metrics
    assert "error_rates" in metrics
    assert "resource_usage" in metrics
    assert "message_rates" in metrics
    
    # Verify metrics were saved
    metrics_path = os.path.join(temp_runtime, "metrics", "load_testing.json")
    with open(metrics_path, "r") as f:
        saved_metrics = json.load(f)
        assert saved_metrics["normal_load"] == metrics

def test_load_scenario_thresholds(mock_config, mock_pbm, temp_runtime):
    """Test that runtime checks load scenario thresholds correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Mock high metrics
    runtime.scenario_metrics = {
        "response_time": 1.5,
        "error_rate": 0.1,
        "resource_usage": 0.9
    }
    
    # Check thresholds
    violations = runtime._check_scenario_thresholds()
    
    # Verify threshold violations
    assert "response_time" in violations
    assert "error_rate" in violations
    assert "resource_usage" in violations
    
    # Verify alerts were generated
    assert len(runtime.scenario_alerts) > 0
    assert any("Response time" in alert["message"] for alert in runtime.scenario_alerts)
    assert any("Error rate" in alert["message"] for alert in runtime.scenario_alerts)
    assert any("Resource usage" in alert["message"] for alert in runtime.scenario_alerts)

@pytest.mark.asyncio
async def test_load_scenario_execution(mock_config, mock_pbm, temp_runtime):
    """Test that runtime executes load scenarios correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Start scenario execution
    execution_task = asyncio.create_task(runtime._execute_load_scenarios())
    
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
    metrics_path = os.path.join(temp_runtime, "metrics", "load_testing.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        assert "timestamp" in metrics
        assert "scenarios" in metrics

def test_load_scenario_report(mock_config, mock_pbm, temp_runtime):
    """Test that runtime generates load scenario reports correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Add sample scenario history
    runtime.scenario_history.extend([
        {
            "timestamp": datetime.now() - timedelta(minutes=5),
            "scenario": "normal_load",
            "metrics": {
                "response_time": 0.5,
                "error_rate": 0.02,
                "resource_usage": 0.6
            }
        },
        {
            "timestamp": datetime.now() - timedelta(minutes=4),
            "scenario": "high_load",
            "metrics": {
                "response_time": 0.8,
                "error_rate": 0.03,
                "resource_usage": 0.7
            }
        },
        {
            "timestamp": datetime.now() - timedelta(minutes=3),
            "scenario": "peak_load",
            "metrics": {
                "response_time": 1.2,
                "error_rate": 0.04,
                "resource_usage": 0.8
            }
        }
    ])
    
    # Generate report
    report = runtime._generate_load_report()
    
    # Verify report contents
    assert "summary" in report
    assert "scenario_metrics" in report
    assert "threshold_violations" in report
    assert "recommendations" in report
    
    # Verify report was saved
    report_path = os.path.join(temp_runtime, "reports", "load_testing_report.json")
    with open(report_path, "r") as f:
        saved_report = json.load(f)
        assert saved_report == report

def test_load_scenario_recommendations(mock_config, mock_pbm, temp_runtime):
    """Test that runtime generates load scenario recommendations correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Add sample scenario metrics
    runtime.scenario_metrics = {
        "normal_load": {
            "response_time": 0.5,
            "error_rate": 0.02,
            "resource_usage": 0.6
        },
        "high_load": {
            "response_time": 0.8,
            "error_rate": 0.03,
            "resource_usage": 0.7
        },
        "peak_load": {
            "response_time": 1.2,
            "error_rate": 0.04,
            "resource_usage": 0.8
        }
    }
    
    # Generate recommendations
    recommendations = runtime._generate_load_recommendations()
    
    # Verify recommendations
    assert len(recommendations) > 0
    assert any("Response time" in rec for rec in recommendations)
    assert any("Error rate" in rec for rec in recommendations)
    assert any("Resource usage" in rec for rec in recommendations)
    assert any("Scaling" in rec for rec in recommendations) 