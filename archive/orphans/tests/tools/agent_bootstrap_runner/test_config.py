"""
Tests for the agent bootstrap runner configuration
"""

import pytest

from dreamos.tools.agent_bootstrap_runner.config import (
    AGENT_CHARTERS,
    AGENT_TRAITS,
    AgentConfig,
    parse_args,
    validate_agent_id,
)


def test_validate_agent_id():
    """Test agent ID validation"""
    assert validate_agent_id("Agent-1") is True
    assert validate_agent_id("Agent-8") is True
    assert validate_agent_id("Agent-0") is False  # Agent-0 is not valid
    assert validate_agent_id("Agent-9") is False
    assert validate_agent_id("agent-1") is False
    assert validate_agent_id("Agent1") is False
    assert validate_agent_id("") is False
    assert validate_agent_id("Agent-") is False
    assert validate_agent_id("-1") is False


def test_agent_config_initialization():
    """Test AgentConfig initialization"""
    config = AgentConfig("Agent-2")

    # Check basic attributes
    assert config.agent_id == "Agent-2"
    assert config.agent_num == "2"
    assert config.traits == AGENT_TRAITS["Agent-2"]
    assert config.charter == AGENT_CHARTERS["Agent-2"]

    # Check path construction
    assert "agent_comms/agent_mailboxes/Agent-2" in str(config.base_runtime)
    assert config.inbox_file.name == "inbox.json"
    assert config.state_file.name == "agent_state.json"

    # Check agent ID for retriever
    assert config.agent_id_for_retriever == "agent_02"


def test_agent_config_with_env_vars(monkeypatch):
    """Test AgentConfig with environment variables"""
    # Set environment variables
    monkeypatch.setenv("AGENT_HEARTBEAT_SEC", "60")
    monkeypatch.setenv("AGENT_LOOP_DELAY_SEC", "10")
    monkeypatch.setenv("AGENT_LOG_LEVEL", "DEBUG")

    config = AgentConfig("Agent-3")

    # Check that env vars were applied
    assert config.heartbeat_sec == 60
    assert config.loop_delay_sec == 10
    assert config.log_level == "DEBUG"


def test_agent_config_invalid_id():
    """Test AgentConfig with invalid agent ID"""
    with pytest.raises(ValueError, match="Invalid agent ID"):
        AgentConfig("Agent-9")


def test_parse_args():
    """Test command line argument parsing"""
    # Test with minimal args
    args = parse_args(["--agent", "Agent-4"])
    assert args["agent"] == "Agent-4"
    assert not args["once"]
    assert not args["no_delay"]

    # Test with all args
    args = parse_args(
        [
            "--agent",
            "Agent-5",
            "--once",
            "--no-delay",
            "--prompt",
            "Test prompt",
            "--prompt-file",
            "test.md",
            "--prompt-dir",
            "custom/prompts",
        ]
    )
    assert args["agent"] == "Agent-5"
    assert args["once"]
    assert args["no_delay"]
    assert args["prompt"] == "Test prompt"
    assert args["prompt_file"] == "test.md"
    assert args["prompt_dir"] == "custom/prompts"


def test_agent_config_directories(tmp_path):
    """Test directory creation and structure"""
    # Create a temporary runtime directory
    runtime_dir = tmp_path / "runtime"

    # Initialize config with custom runtime path
    config = AgentConfig("Agent-6", runtime_base=runtime_dir)

    # Check directory structure
    assert config.base_runtime.exists()
    assert config.inbox_dir.exists()
    assert config.processed_dir.exists()
    assert config.state_dir.exists()
    assert config.archive_dir.exists()


def test_agent_config_performance_limits():
    """Test performance limit configurations"""
    config = AgentConfig("Agent-7")

    # Check default limits
    assert config.max_file_size_bytes == 10 * 1024 * 1024  # 10 MB
    assert config.max_lines_per_edit == 600
    assert config.max_search_depth == 10
    assert config.max_recovery_attempts == 3
