"""
Tests for the config module
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from dreamos.tools.agent2_bootstrap_runner.config import (
    AGENT_CHARTERS,
    AGENT_ID,
    AGENT_TRAITS,
    AgentConfig,
    create_directories,
    parse_args,
)


class TestAgentConfig:
    def test_default_initialization(self):
        """Test initialization with default values"""
        config = AgentConfig()
        assert config.agent_id == AGENT_ID
        assert config.agent_id_for_retriever == f"agent_{AGENT_ID.split('-')[1].zfill(2)}"
        assert config.traits == AGENT_TRAITS.get(AGENT_ID)
        assert config.charter == AGENT_CHARTERS.get(AGENT_ID)
    
    def test_custom_agent_id(self):
        """Test initialization with custom agent ID"""
        agent_id = "Agent-5"
        config = AgentConfig(agent_id=agent_id)
        assert config.agent_id == agent_id
        assert config.agent_id_for_retriever == "agent_05"
        assert config.traits == AGENT_TRAITS.get(agent_id)
        assert config.charter == AGENT_CHARTERS.get(agent_id)
    
    def test_invalid_agent_id_handling(self):
        """Test handling of invalid agent ID"""
        agent_id = "CustomAgent"
        config = AgentConfig(agent_id=agent_id)
        assert config.agent_id == agent_id
        assert config.agent_id_for_retriever == "agent_0"  # Default if no hyphen
        assert config.traits == "Versatile, Adaptive, Reliable, Focused"  # Default traits
        assert config.charter == "GENERAL OPERATIONS"  # Default charter
    
    def test_path_construction(self, mock_project_root):
        """Test path construction with mocked project root"""
        with patch('dreamos.tools.agent2_bootstrap_runner.config.PROJECT_ROOT', mock_project_root):
            config = AgentConfig(agent_id="Agent-3")
            
            # Check base paths
            assert config.base_runtime == mock_project_root / "runtime/agent_comms/agent_mailboxes/Agent-3"
            assert config.inbox_file == config.base_runtime / "inbox.json"
            assert config.archive_dir == config.base_runtime / "archive"
            assert config.devlog_path == mock_project_root / "runtime/devlog/agents/agent-3.log"
            
            # Check new directory paths
            assert config.inbox_dir == config.base_runtime / "inbox"
            assert config.processed_dir == config.base_runtime / "processed"
            assert config.state_dir == config.base_runtime / "state"
            assert config.state_file == config.state_dir / "agent_state.json"
            
            # Check coordinate paths
            assert config.coords_file == mock_project_root / "runtime/config/cursor_agent_coords.json"
            assert config.copy_coords_file == mock_project_root / "runtime/config/cursor_agent_copy_coords.json"
            
            # Check protocol paths
            assert config.protocol_dir == mock_project_root / "runtime/governance/protocols"
            assert config.inbox_loop_protocol == config.protocol_dir / "INBOX_LOOP_PROTOCOL.md"

class TestCreateDirectories:
    def test_directory_creation(self, mock_agent_config, tmp_path):
        """Test directory creation with mock config"""
        # Override paths to use tmp_path
        mock_agent_config.base_runtime = tmp_path / "base"
        mock_agent_config.archive_dir = tmp_path / "archive"
        mock_agent_config.inbox_dir = tmp_path / "inbox"
        mock_agent_config.processed_dir = tmp_path / "processed"
        mock_agent_config.state_dir = tmp_path / "state"
        mock_agent_config.devlog_path = tmp_path / "devlog/agent.log"
        mock_agent_config.protocol_dir = tmp_path / "protocols"
        mock_agent_config.state_file = mock_agent_config.state_dir / "agent_state.json"
        
        # Call create_directories
        with patch('logging.info') as mock_log:
            create_directories(mock_agent_config)
            
            # Check directories were created
            assert mock_agent_config.base_runtime.exists()
            assert mock_agent_config.archive_dir.exists()
            assert mock_agent_config.inbox_dir.exists()
            assert mock_agent_config.processed_dir.exists()
            assert mock_agent_config.state_dir.exists()
            assert mock_agent_config.devlog_path.parent.exists()
            assert mock_agent_config.protocol_dir.exists()
            
            # Check state file was created
            assert mock_agent_config.state_file.exists()
            
            # Check logging was called
            mock_log.assert_called()

class TestParseArgs:
    def test_default_args(self):
        """Test parsing with default arguments"""
        with patch('sys.argv', ['script.py']):
            args = parse_args()
            assert args['agent'] == AGENT_ID
            assert not args['once']
            assert not args['no_delay']
            assert args['prompt'] is None
            assert args['prompt_file'] is None
    
    def test_custom_args(self):
        """Test parsing with custom arguments"""
        test_args = [
            'script.py',
            '--agent', 'Agent-7',
            '--once',
            '--no-delay',
            '--prompt', 'Test prompt',
            '--prompt-dir', 'custom/prompts'
        ]
        
        with patch('sys.argv', test_args):
            args = parse_args()
            assert args['agent'] == 'Agent-7'
            assert args['once']
            assert args['no_delay']
            assert args['prompt'] == 'Test prompt'
            assert args['prompt_dir'] == 'custom/prompts' 