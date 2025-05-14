"""
Tests for Agent Identity and Awareness Module
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

from dreamos.agents.utils.agent_identity import AgentIdentity, AgentAwareness

@pytest.fixture
def sample_config():
    return {
        "agent_prefixes": {
            "Agent-1": "⚙️ Engineer",
            "Agent-2": "🛡️ Escalation Watch",
            "Agent-3": "📦 Task Router",
            "Agent-4": "🔬 Validator",
            "Agent-5": "🎯 Captain",
            "Agent-6": "🧠 Reflection",
            "Agent-7": "📡 Bridge Ops",
            "Agent-8": "🕊️ Lorekeeper"
        }
    }

@pytest.fixture
def temp_config_dir(tmp_path):
    config_dir = tmp_path / "runtime" / "config"
    config_dir.mkdir(parents=True)
    return config_dir

@pytest.fixture
def temp_log_dir(tmp_path):
    log_dir = tmp_path / "runtime" / "logs" / "awareness"
    log_dir.mkdir(parents=True)
    return log_dir

def test_agent_identity_creation():
    """Test creating an agent identity."""
    identity = AgentIdentity("Agent-1", "⚙️ Engineer", "System engineering and optimization")
    
    assert identity.agent_id == "Agent-1"
    assert identity.role == "⚙️ Engineer"
    assert identity.purpose == "System engineering and optimization"
    assert identity.awareness_level == 0.0
    assert identity.last_confirmation is None

def test_agent_identity_to_dict():
    """Test converting identity to dictionary."""
    identity = AgentIdentity("Agent-1", "⚙️ Engineer", "System engineering and optimization")
    identity.last_confirmation = "2024-03-12T00:00:00"
    identity.awareness_level = 0.5
    
    identity_dict = identity.to_dict()
    
    assert identity_dict["agent_id"] == "Agent-1"
    assert identity_dict["role"] == "⚙️ Engineer"
    assert identity_dict["purpose"] == "System engineering and optimization"
    assert identity_dict["last_confirmation"] == "2024-03-12T00:00:00"
    assert identity_dict["awareness_level"] == 0.5

def test_agent_awareness_initialization(sample_config, temp_config_dir):
    """Test initializing agent awareness from config."""
    awareness = AgentAwareness()
    awareness.config_path = temp_config_dir / "agent_identity.json"
    
    assert awareness.initialize_from_config(sample_config)
    assert len(awareness.identities) == 8
    
    # Verify config file was created
    assert awareness.config_path.exists()
    
    # Verify config content
    with open(awareness.config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    assert "agents" in config_data
    assert len(config_data["agents"]) == 8
    assert "Agent-1" in config_data["agents"]
    assert config_data["agents"]["Agent-1"]["role"] == "⚙️ Engineer"

def test_identity_confirmation(sample_config, temp_config_dir, temp_log_dir):
    """Test confirming agent identity."""
    awareness = AgentAwareness()
    awareness.config_path = temp_config_dir / "agent_identity.json"
    awareness.log_path = temp_log_dir
    
    assert awareness.initialize_from_config(sample_config)
    assert awareness.confirm_identity("Agent-1")
    
    # Verify awareness level increased
    assert awareness.get_awareness_level("Agent-1") == 0.1
    
    # Verify log file was created
    log_file = temp_log_dir / "Agent-1_awareness.log"
    assert log_file.exists()
    
    # Verify log content
    with open(log_file, 'r', encoding='utf-8') as f:
        log_entry = json.loads(f.readline())
    
    assert log_entry["agent_id"] == "Agent-1"
    assert log_entry["role"] == "⚙️ Engineer"
    assert log_entry["awareness_level"] == 0.1
    assert log_entry["event"] == "identity_confirmation"

def test_identity_validation(sample_config, temp_config_dir):
    """Test identity validation."""
    awareness = AgentAwareness()
    awareness.config_path = temp_config_dir / "agent_identity.json"
    
    assert awareness.initialize_from_config(sample_config)
    assert awareness.validate_identity("Agent-1")
    assert not awareness.validate_identity("Unknown-Agent")

def test_get_identity_prefix(sample_config, temp_config_dir):
    """Test getting identity prefix."""
    awareness = AgentAwareness()
    awareness.config_path = temp_config_dir / "agent_identity.json"
    
    assert awareness.initialize_from_config(sample_config)
    assert awareness.get_identity_prefix("Agent-1") == "⚙️ Engineer Agent-1"
    assert awareness.get_identity_prefix("Unknown-Agent") == "Unknown Unknown-Agent"

def test_awareness_level_increase(sample_config, temp_config_dir):
    """Test awareness level increase with multiple confirmations."""
    awareness = AgentAwareness()
    awareness.config_path = temp_config_dir / "agent_identity.json"
    
    assert awareness.initialize_from_config(sample_config)
    
    # Confirm identity multiple times
    for _ in range(5):
        assert awareness.confirm_identity("Agent-1")
    
    # Verify awareness level increased but capped at 1.0
    assert awareness.get_awareness_level("Agent-1") == 0.5 