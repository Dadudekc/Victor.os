"""
Integration test suite for testing the integration between various components of the system.
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
from dreamos.agents.agent_manager import AgentManager
from dreamos.agents.agent import Agent
from dreamos.agents.mailbox import Mailbox
from dreamos.agents.state import AgentState
from dreamos.agents.metrics import AgentMetrics
from dreamos.agents.validation import AgentValidation
from dreamos.agents.improvement import AgentImprovement
from dreamos.agents.documentation import AgentDocumentation
from dreamos.agents.leaderboard import AgentLeaderboard
from dreamos.agents.jarvis import JarvisIntegration
from dreamos.agents.health import AgentHealth
from dreamos.agents.load import AgentLoad
from dreamos.agents.chaos import AgentChaos

@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = MagicMock(spec=AppConfig)
    config.runtime_id = "test-runtime"
    config.runtime_path = "runtime"
    config.episode_path = "episodes/episode-launch-final-lock.yaml"
    config.agent_config = {
        "agent_id": "test-agent",
        "agent_type": "test",
        "agent_version": "1.0.0",
        "agent_description": "Test agent",
        "agent_author": "Test Author",
        "agent_contact": "test@example.com",
        "agent_license": "MIT",
        "agent_repository": "https://github.com/test/agent",
        "agent_documentation": "https://test/agent/docs",
        "agent_support": "https://test/agent/support",
        "agent_metrics": {
            "response_time_threshold": 1.0,
            "error_rate_threshold": 0.05,
            "availability_threshold": 0.95
        },
        "agent_validation": {
            "required_components": [
                "tests",
                "documentation",
                "implementation",
                "demonstration"
            ],
            "validation_status": "pending",
            "validation_metrics": {}
        },
        "agent_improvement": {
            "improvement_status": "pending",
            "improvement_metrics": {}
        },
        "agent_documentation": {
            "documentation_status": "pending",
            "documentation_metrics": {}
        },
        "agent_leaderboard": {
            "leaderboard_status": "pending",
            "leaderboard_metrics": {}
        },
        "agent_jarvis": {
            "jarvis_status": "pending",
            "jarvis_metrics": {}
        },
        "agent_health": {
            "health_status": "pending",
            "health_metrics": {}
        },
        "agent_load": {
            "load_status": "pending",
            "load_metrics": {}
        },
        "agent_chaos": {
            "chaos_status": "pending",
            "chaos_metrics": {}
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

@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    agent = MagicMock(spec=Agent)
    agent.agent_id = "test-agent"
    agent.agent_type = "test"
    agent.agent_version = "1.0.0"
    agent.agent_description = "Test agent"
    agent.agent_author = "Test Author"
    agent.agent_contact = "test@example.com"
    agent.agent_license = "MIT"
    agent.agent_repository = "https://github.com/test/agent"
    agent.agent_documentation = "https://test/agent/docs"
    agent.agent_support = "https://test/agent/support"
    agent.mailbox = MagicMock(spec=Mailbox)
    agent.state = MagicMock(spec=AgentState)
    agent.metrics = MagicMock(spec=AgentMetrics)
    agent.validation = MagicMock(spec=AgentValidation)
    agent.improvement = MagicMock(spec=AgentImprovement)
    agent.documentation = MagicMock(spec=AgentDocumentation)
    agent.leaderboard = MagicMock(spec=AgentLeaderboard)
    agent.jarvis = MagicMock(spec=JarvisIntegration)
    agent.health = MagicMock(spec=AgentHealth)
    agent.load = MagicMock(spec=AgentLoad)
    agent.chaos = MagicMock(spec=AgentChaos)
    return agent

@pytest.fixture
def mock_agent_manager(mock_agent):
    """Create a mock agent manager."""
    agent_manager = MagicMock(spec=AgentManager)
    agent_manager.agents = {"test-agent": mock_agent}
    return agent_manager

def test_runtime_agent_integration(mock_config, mock_pbm, temp_runtime, mock_agent_manager):
    """Test that runtime integrates with agent manager correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent manager
    runtime.agent_manager = mock_agent_manager
    
    # Verify agent manager integration
    assert runtime.agent_manager == mock_agent_manager
    assert "test-agent" in runtime.agent_manager.agents
    assert runtime.agent_manager.agents["test-agent"] == mock_agent_manager.agents["test-agent"]

def test_agent_mailbox_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with mailbox correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Verify mailbox integration
    assert runtime.agent.mailbox == mock_agent.mailbox
    assert runtime.agent.mailbox.inbox == mock_agent.mailbox.inbox
    assert runtime.agent.mailbox.outbox == mock_agent.mailbox.outbox

def test_agent_state_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with state correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Verify state integration
    assert runtime.agent.state == mock_agent.state
    assert runtime.agent.state.status == mock_agent.state.status
    assert runtime.agent.state.metrics == mock_agent.state.metrics

def test_agent_metrics_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with metrics correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Verify metrics integration
    assert runtime.agent.metrics == mock_agent.metrics
    assert runtime.agent.metrics.response_time == mock_agent.metrics.response_time
    assert runtime.agent.metrics.error_rate == mock_agent.metrics.error_rate
    assert runtime.agent.metrics.availability == mock_agent.metrics.availability

def test_agent_validation_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with validation correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Verify validation integration
    assert runtime.agent.validation == mock_agent.validation
    assert runtime.agent.validation.status == mock_agent.validation.status
    assert runtime.agent.validation.metrics == mock_agent.validation.metrics

def test_agent_improvement_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with improvement correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Verify improvement integration
    assert runtime.agent.improvement == mock_agent.improvement
    assert runtime.agent.improvement.status == mock_agent.improvement.status
    assert runtime.agent.improvement.metrics == mock_agent.improvement.metrics

def test_agent_documentation_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with documentation correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Verify documentation integration
    assert runtime.agent.documentation == mock_agent.documentation
    assert runtime.agent.documentation.status == mock_agent.documentation.status
    assert runtime.agent.documentation.metrics == mock_agent.documentation.metrics

def test_agent_leaderboard_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with leaderboard correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Verify leaderboard integration
    assert runtime.agent.leaderboard == mock_agent.leaderboard
    assert runtime.agent.leaderboard.status == mock_agent.leaderboard.status
    assert runtime.agent.leaderboard.metrics == mock_agent.leaderboard.metrics

def test_agent_jarvis_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with jarvis correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Verify jarvis integration
    assert runtime.agent.jarvis == mock_agent.jarvis
    assert runtime.agent.jarvis.status == mock_agent.jarvis.status
    assert runtime.agent.jarvis.metrics == mock_agent.jarvis.metrics

def test_agent_health_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with health correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Verify health integration
    assert runtime.agent.health == mock_agent.health
    assert runtime.agent.health.status == mock_agent.health.status
    assert runtime.agent.health.metrics == mock_agent.health.metrics

def test_agent_load_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with load correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Verify load integration
    assert runtime.agent.load == mock_agent.load
    assert runtime.agent.load.status == mock_agent.load.status
    assert runtime.agent.load.metrics == mock_agent.load.metrics

def test_agent_chaos_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with chaos correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Verify chaos integration
    assert runtime.agent.chaos == mock_agent.chaos
    assert runtime.agent.chaos.status == mock_agent.chaos.status
    assert runtime.agent.chaos.metrics == mock_agent.chaos.metrics

def test_agent_communication_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with communication correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Send message
    message = {
        "type": "test",
        "content": "Test message",
        "timestamp": datetime.now().isoformat()
    }
    runtime.agent.mailbox.send_message(message)
    
    # Verify message was sent
    assert len(runtime.agent.mailbox.outbox) == 1
    assert runtime.agent.mailbox.outbox[0] == message
    
    # Receive message
    received_message = runtime.agent.mailbox.receive_message()
    
    # Verify message was received
    assert received_message == message
    assert len(runtime.agent.mailbox.inbox) == 1
    assert runtime.agent.mailbox.inbox[0] == message

def test_agent_state_transition_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with state transition correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Update state
    runtime.agent.state.update_state("active")
    
    # Verify state was updated
    assert runtime.agent.state.status == "active"
    
    # Update metrics
    runtime.agent.state.update_metrics({
        "response_time": 0.5,
        "error_rate": 0.02,
        "availability": 0.98
    })
    
    # Verify metrics were updated
    assert runtime.agent.state.metrics["response_time"] == 0.5
    assert runtime.agent.state.metrics["error_rate"] == 0.02
    assert runtime.agent.state.metrics["availability"] == 0.98

def test_agent_metrics_collection_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with metrics collection correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Collect metrics
    metrics = runtime.agent.metrics.collect_metrics()
    
    # Verify metrics were collected
    assert "response_time" in metrics
    assert "error_rate" in metrics
    assert "availability" in metrics
    
    # Update metrics
    runtime.agent.metrics.update_metrics(metrics)
    
    # Verify metrics were updated
    assert runtime.agent.metrics.response_time == metrics["response_time"]
    assert runtime.agent.metrics.error_rate == metrics["error_rate"]
    assert runtime.agent.metrics.availability == metrics["availability"]

def test_agent_validation_workflow_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with validation workflow correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Start validation
    runtime.agent.validation.start_validation()
    
    # Verify validation was started
    assert runtime.agent.validation.status == "in_progress"
    
    # Update validation metrics
    runtime.agent.validation.update_metrics({
        "tests_passed": 10,
        "tests_failed": 0,
        "coverage": 0.95
    })
    
    # Verify validation metrics were updated
    assert runtime.agent.validation.metrics["tests_passed"] == 10
    assert runtime.agent.validation.metrics["tests_failed"] == 0
    assert runtime.agent.validation.metrics["coverage"] == 0.95
    
    # Complete validation
    runtime.agent.validation.complete_validation()
    
    # Verify validation was completed
    assert runtime.agent.validation.status == "completed"

def test_agent_improvement_workflow_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with improvement workflow correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Start improvement
    runtime.agent.improvement.start_improvement()
    
    # Verify improvement was started
    assert runtime.agent.improvement.status == "in_progress"
    
    # Update improvement metrics
    runtime.agent.improvement.update_metrics({
        "improvements_made": 5,
        "improvements_pending": 0,
        "improvement_score": 0.9
    })
    
    # Verify improvement metrics were updated
    assert runtime.agent.improvement.metrics["improvements_made"] == 5
    assert runtime.agent.improvement.metrics["improvements_pending"] == 0
    assert runtime.agent.improvement.metrics["improvement_score"] == 0.9
    
    # Complete improvement
    runtime.agent.improvement.complete_improvement()
    
    # Verify improvement was completed
    assert runtime.agent.improvement.status == "completed"

def test_agent_documentation_workflow_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with documentation workflow correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Start documentation
    runtime.agent.documentation.start_documentation()
    
    # Verify documentation was started
    assert runtime.agent.documentation.status == "in_progress"
    
    # Update documentation metrics
    runtime.agent.documentation.update_metrics({
        "docs_updated": 10,
        "docs_pending": 0,
        "doc_coverage": 0.95
    })
    
    # Verify documentation metrics were updated
    assert runtime.agent.documentation.metrics["docs_updated"] == 10
    assert runtime.agent.documentation.metrics["docs_pending"] == 0
    assert runtime.agent.documentation.metrics["doc_coverage"] == 0.95
    
    # Complete documentation
    runtime.agent.documentation.complete_documentation()
    
    # Verify documentation was completed
    assert runtime.agent.documentation.status == "completed"

def test_agent_leaderboard_workflow_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with leaderboard workflow correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Start leaderboard
    runtime.agent.leaderboard.start_leaderboard()
    
    # Verify leaderboard was started
    assert runtime.agent.leaderboard.status == "in_progress"
    
    # Update leaderboard metrics
    runtime.agent.leaderboard.update_metrics({
        "rank": 1,
        "score": 100,
        "improvements": 10
    })
    
    # Verify leaderboard metrics were updated
    assert runtime.agent.leaderboard.metrics["rank"] == 1
    assert runtime.agent.leaderboard.metrics["score"] == 100
    assert runtime.agent.leaderboard.metrics["improvements"] == 10
    
    # Complete leaderboard
    runtime.agent.leaderboard.complete_leaderboard()
    
    # Verify leaderboard was completed
    assert runtime.agent.leaderboard.status == "completed"

def test_agent_jarvis_workflow_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with jarvis workflow correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Start jarvis
    runtime.agent.jarvis.start_jarvis()
    
    # Verify jarvis was started
    assert runtime.agent.jarvis.status == "in_progress"
    
    # Update jarvis metrics
    runtime.agent.jarvis.update_metrics({
        "sync_status": "synced",
        "sync_time": 0.5,
        "sync_errors": 0
    })
    
    # Verify jarvis metrics were updated
    assert runtime.agent.jarvis.metrics["sync_status"] == "synced"
    assert runtime.agent.jarvis.metrics["sync_time"] == 0.5
    assert runtime.agent.jarvis.metrics["sync_errors"] == 0
    
    # Complete jarvis
    runtime.agent.jarvis.complete_jarvis()
    
    # Verify jarvis was completed
    assert runtime.agent.jarvis.status == "completed"

def test_agent_health_workflow_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with health workflow correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Start health
    runtime.agent.health.start_health()
    
    # Verify health was started
    assert runtime.agent.health.status == "in_progress"
    
    # Update health metrics
    runtime.agent.health.update_metrics({
        "health_status": "healthy",
        "health_score": 0.95,
        "health_issues": 0
    })
    
    # Verify health metrics were updated
    assert runtime.agent.health.metrics["health_status"] == "healthy"
    assert runtime.agent.health.metrics["health_score"] == 0.95
    assert runtime.agent.health.metrics["health_issues"] == 0
    
    # Complete health
    runtime.agent.health.complete_health()
    
    # Verify health was completed
    assert runtime.agent.health.status == "completed"

def test_agent_load_workflow_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with load workflow correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Start load
    runtime.agent.load.start_load()
    
    # Verify load was started
    assert runtime.agent.load.status == "in_progress"
    
    # Update load metrics
    runtime.agent.load.update_metrics({
        "load_status": "normal",
        "load_score": 0.8,
        "load_issues": 0
    })
    
    # Verify load metrics were updated
    assert runtime.agent.load.metrics["load_status"] == "normal"
    assert runtime.agent.load.metrics["load_score"] == 0.8
    assert runtime.agent.load.metrics["load_issues"] == 0
    
    # Complete load
    runtime.agent.load.complete_load()
    
    # Verify load was completed
    assert runtime.agent.load.status == "completed"

def test_agent_chaos_workflow_integration(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent integrates with chaos workflow correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Start chaos
    runtime.agent.chaos.start_chaos()
    
    # Verify chaos was started
    assert runtime.agent.chaos.status == "in_progress"
    
    # Update chaos metrics
    runtime.agent.chaos.update_metrics({
        "chaos_status": "stable",
        "chaos_score": 0.9,
        "chaos_issues": 0
    })
    
    # Verify chaos metrics were updated
    assert runtime.agent.chaos.metrics["chaos_status"] == "stable"
    assert runtime.agent.chaos.metrics["chaos_score"] == 0.9
    assert runtime.agent.chaos.metrics["chaos_issues"] == 0
    
    # Complete chaos
    runtime.agent.chaos.complete_chaos()
    
    # Verify chaos was completed
    assert runtime.agent.chaos.status == "completed"

def test_agent_integration_report(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent generates integration report correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Generate report
    report = runtime.agent.generate_integration_report()
    
    # Verify report contents
    assert "summary" in report
    assert "agent_metrics" in report
    assert "integration_metrics" in report
    assert "recommendations" in report
    
    # Verify report was saved
    report_path = os.path.join(temp_runtime, "reports", "integration_report.json")
    with open(report_path, "r") as f:
        saved_report = json.load(f)
        assert saved_report == report

def test_agent_integration_recommendations(mock_config, mock_pbm, temp_runtime, mock_agent):
    """Test that agent generates integration recommendations correctly."""
    # Create runtime instance
    runtime = RuntimeManager(mock_config, mock_pbm)
    
    # Set agent
    runtime.agent = mock_agent
    
    # Generate recommendations
    recommendations = runtime.agent.generate_integration_recommendations()
    
    # Verify recommendations
    assert len(recommendations) > 0
    assert any("Integration" in rec for rec in recommendations)
    assert any("Metrics" in rec for rec in recommendations)
    assert any("Workflow" in rec for rec in recommendations)
    assert any("Performance" in rec for rec in recommendations) 