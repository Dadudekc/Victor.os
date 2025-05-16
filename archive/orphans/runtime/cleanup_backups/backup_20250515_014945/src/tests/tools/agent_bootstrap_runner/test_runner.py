"""Tests for the Universal Agent Bootstrap Runner."""

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dreamos.tools.agent_bootstrap_runner import AgentBootstrapRunner, AgentConfig


@pytest.fixture
def config():
    """Create a test configuration."""
    return AgentConfig(
        agent_id="Agent-2",
        prompt="Test prompt",
        heartbeat_sec=1,
        loop_delay_sec=1,
        response_wait_sec=1,
        retrieve_retries=1,
        retry_delay_sec=1,
        startup_delay_sec=0
    )

@pytest.fixture
def mock_runtime_dir(tmp_path):
    """Create a mock runtime directory structure."""
    # Create directories
    agent_dir = tmp_path / "runtime/agent_comms/agent_mailboxes/Agent-2"
    for subdir in ["inbox", "processed", "state", "archive"]:
        (agent_dir / subdir).mkdir(parents=True)
    
    # Create config files
    config_dir = tmp_path / "runtime/config"
    config_dir.mkdir(parents=True)
    
    coords = {"Agent-2": {"x": 100, "y": 200}}
    copy_coords = {"agent_02": [300, 400]}
    
    (config_dir / "cursor_agent_coords.json").write_text(json.dumps(coords))
    (config_dir / "cursor_agent_copy_coords.json").write_text(json.dumps(copy_coords))
    
    # Create devlog directory
    devlog_dir = tmp_path / "runtime/devlog/agents"
    devlog_dir.mkdir(parents=True)
    
    return tmp_path

@pytest.mark.asyncio
async def test_agent_bootstrap_runner_initialization(config, mock_runtime_dir):
    """Test runner initialization."""
    with patch("dreamos.tools.agent_bootstrap_runner.runner.Path") as mock_path:
        mock_path.return_value = mock_runtime_dir
        runner = AgentBootstrapRunner(config)
        
        assert runner.config == config
        assert runner.agent_bus is not None
        assert runner.injector is not None
        assert runner.retriever is not None

@pytest.mark.asyncio
async def test_validate_setup_success(config, mock_runtime_dir):
    """Test successful setup validation."""
    with patch("dreamos.tools.agent_bootstrap_runner.runner.Path") as mock_path:
        mock_path.return_value = mock_runtime_dir
        runner = AgentBootstrapRunner(config)
        await runner.validate_setup()

@pytest.mark.asyncio
async def test_validate_setup_missing_coords(config, mock_runtime_dir):
    """Test validation fails with missing coordinate files."""
    # Remove coordinate files
    (mock_runtime_dir / "runtime/config/cursor_agent_coords.json").unlink()
    
    with patch("dreamos.tools.agent_bootstrap_runner.runner.Path") as mock_path:
        mock_path.return_value = mock_runtime_dir
        runner = AgentBootstrapRunner(config)
        
        with pytest.raises(RuntimeError, match="Missing coordinate files"):
            await runner.validate_setup()

@pytest.mark.asyncio
async def test_load_prompt_direct(config, mock_runtime_dir):
    """Test loading prompt directly from config."""
    with patch("dreamos.tools.agent_bootstrap_runner.runner.Path") as mock_path:
        mock_path.return_value = mock_runtime_dir
        runner = AgentBootstrapRunner(config)
        prompt = await runner.load_prompt()
        assert prompt == "Test prompt"

@pytest.mark.asyncio
async def test_load_prompt_from_file(config, mock_runtime_dir):
    """Test loading prompt from file."""
    # Create prompt file
    prompt_dir = mock_runtime_dir / "runtime/prompts"
    prompt_dir.mkdir(parents=True)
    prompt_file = prompt_dir / "agent-2.txt"
    prompt_file.write_text("File prompt")
    
    config.prompt = None  # Clear direct prompt
    
    with patch("dreamos.tools.agent_bootstrap_runner.runner.Path") as mock_path:
        mock_path.return_value = mock_runtime_dir
        runner = AgentBootstrapRunner(config)
        prompt = await runner.load_prompt()
        assert prompt == "File prompt"

@pytest.mark.asyncio
async def test_run_cycle_success(config, mock_runtime_dir):
    """Test successful run cycle."""
    with patch("dreamos.tools.agent_bootstrap_runner.runner.Path") as mock_path, \
         patch("dreamos.tools.agent_bootstrap_runner.runner.CursorInjector") as mock_injector, \
         patch("dreamos.tools.agent_bootstrap_runner.runner.ResponseRetriever") as mock_retriever, \
         patch("dreamos.tools.agent_bootstrap_runner.runner.AgentBus") as mock_bus:
        
        mock_path.return_value = mock_runtime_dir
        mock_injector.return_value.inject_text = AsyncMock()
        mock_retriever.return_value.get_response = AsyncMock(return_value="Test response")
        mock_bus.return_value.publish = AsyncMock()
        
        runner = AgentBootstrapRunner(config)
        await runner.run_cycle()
        
        # Verify interactions
        mock_injector.return_value.inject_text.assert_called_once_with("Test prompt")
        mock_retriever.return_value.get_response.assert_called_once_with(
            wait_time=1,
            retries=1,
            retry_delay=1
        )
        mock_bus.return_value.publish.assert_called_once()

@pytest.mark.asyncio
async def test_run_cycle_error(config, mock_runtime_dir):
    """Test run cycle with error."""
    with patch("dreamos.tools.agent_bootstrap_runner.runner.Path") as mock_path, \
         patch("dreamos.tools.agent_bootstrap_runner.runner.CursorInjector") as mock_injector, \
         patch("dreamos.tools.agent_bootstrap_runner.runner.AgentBus") as mock_bus:
        
        mock_path.return_value = mock_runtime_dir
        mock_injector.return_value.inject_text = AsyncMock(side_effect=Exception("Test error"))
        mock_bus.return_value.publish = AsyncMock()
        
        runner = AgentBootstrapRunner(config)
        await runner.run_cycle()
        
        # Verify error event published
        mock_bus.return_value.publish.assert_called_once_with(
            "agent.error",
            {
                "agent_id": "Agent-2",
                "error_type": "Exception",
                "error_message": "Test error",
                "timestamp": mock_bus.return_value.publish.call_args[0][1]["timestamp"]
            }
        )

@pytest.mark.asyncio
async def test_run_once(config, mock_runtime_dir):
    """Test running once and exiting."""
    with patch("dreamos.tools.agent_bootstrap_runner.runner.Path") as mock_path, \
         patch.object(AgentBootstrapRunner, "run_cycle") as mock_run_cycle, \
         patch.object(AgentBootstrapRunner, "validate_setup") as mock_validate:
        
        mock_path.return_value = mock_runtime_dir
        mock_run_cycle.return_value = AsyncMock()
        mock_validate.return_value = AsyncMock()
        
        runner = AgentBootstrapRunner(config)
        await runner.run(run_once=True)
        
        mock_validate.assert_called_once()
        mock_run_cycle.assert_called_once()

@pytest.mark.asyncio
async def test_run_continuous(config, mock_runtime_dir):
    """Test running continuously until interrupted."""
    with patch("dreamos.tools.agent_bootstrap_runner.runner.Path") as mock_path, \
         patch.object(AgentBootstrapRunner, "run_cycle") as mock_run_cycle, \
         patch.object(AgentBootstrapRunner, "validate_setup") as mock_validate, \
         patch("asyncio.sleep", side_effect=[None, KeyboardInterrupt]):
        
        mock_path.return_value = mock_runtime_dir
        mock_run_cycle.return_value = AsyncMock()
        mock_validate.return_value = AsyncMock()
        
        runner = AgentBootstrapRunner(config)
        await runner.run()
        
        mock_validate.assert_called_once()
        assert mock_run_cycle.call_count == 1  # One successful cycle before KeyboardInterrupt 