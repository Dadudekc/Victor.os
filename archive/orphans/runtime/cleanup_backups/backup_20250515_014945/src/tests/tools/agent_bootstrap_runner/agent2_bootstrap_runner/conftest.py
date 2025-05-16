"""
Pytest configuration for agent_bootstrap_runner tests
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

# Import the modules we need to test
from dreamos.tools.agent_bootstrap_runner.config import AgentConfig
from dreamos.tools.agent_bootstrap_runner.logging_setup import setup_logging


@pytest.fixture
def agent_id(request):
    """Fixture to provide agent ID for tests.
    Can be overridden by marking test with @pytest.mark.agent_id("Agent-N")
    """
    marker = request.node.get_closest_marker("agent_id")
    return marker.args[0] if marker else "Agent-0"

@pytest.fixture
def mock_project_root(tmp_path):
    """Create a temporary project root with necessary subdirectories"""
    def create_agent_dirs(agent_id):
        # Create agent directories
        agent_dir = tmp_path / "runtime" / "agent_comms" / "agent_mailboxes" / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        inbox_dir = agent_dir / "inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        
        archive_dir = agent_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        processed_dir = agent_dir / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        state_dir = agent_dir / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
    
    # Create directories for all agents
    for i in range(9):
        create_agent_dirs(f"Agent-{i}")
    
    # Create devlog directory
    devlog_dir = tmp_path / "runtime" / "devlog" / "agents"
    devlog_dir.mkdir(parents=True, exist_ok=True)
    
    # Create protocol directory
    protocol_dir = tmp_path / "runtime" / "governance" / "protocols"
    protocol_dir.mkdir(parents=True, exist_ok=True)
    
    # Create config directory with mock coordinate files
    config_dir = tmp_path / "runtime" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Create mock coordinate files with entries for all agents
    coords_data = {f"Agent-{i}": {"x": 100 + i*50, "y": 200 + i*50} for i in range(9)}
    coords_file = config_dir / "cursor_agent_coords.json"
    coords_file.write_text(json.dumps(coords_data))
    
    copy_coords_data = {f"agent_{str(i).zfill(2)}": [300 + i*50, 400 + i*50] for i in range(9)}
    copy_coords_file = config_dir / "cursor_agent_copy_coords.json"
    copy_coords_file.write_text(json.dumps(copy_coords_data))
    
    return tmp_path

@pytest.fixture
def mock_agent_config(mock_project_root, agent_id):
    """Create a mock agent config with the temp project root"""
    with patch('dreamos.tools.agent_bootstrap_runner.config.PROJECT_ROOT', mock_project_root):
        config = AgentConfig(agent_id=agent_id)
        return config

@pytest.fixture
def mock_logger():
    """Create a mock logger for testing"""
    return MagicMock()

@pytest.fixture
def mock_agent_bus():
    """Create a mock AgentBus for testing"""
    mock_bus = MagicMock()
    mock_bus.publish = MagicMock()
    mock_bus.flush = MagicMock()
    return mock_bus 