"""
Tests for agent loop functionality
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dreamos.tools.agent2_bootstrap_runner.agent_loop import agent_loop
from dreamos.tools.agent2_bootstrap_runner.config import AgentConfig


class DummyInjector:
    """Mock injector for testing"""
    def __init__(self, success=True):
        self.success = success
        self.injected_prompts = []
    
    def inject(self, prompt):
        self.injected_prompts.append(prompt)
        return self.success

class DummyRetriever:
    """Mock retriever for testing"""
    def __init__(self, responses=None):
        self.responses = responses or ["Mocked Response"]
        self.call_count = 0
    
    def retrieve(self):
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        return None

@pytest.mark.asyncio
class TestAgentLoop:
    async def test_single_cycle_success(self, mock_logger, mock_agent_config, tmp_path):
        """Test successful single cycle execution"""
        # Set up test inbox
        inbox_file = tmp_path / "inbox.json"
        inbox_file.write_text('[{"prompt": "test prompt", "prompt_id": "test-123"}]')
        mock_agent_config.inbox_file = inbox_file
        mock_agent_config.archive_dir = tmp_path / "archive"
        mock_agent_config.archive_dir.mkdir(parents=True)
        
        # Set up test components
        injector = DummyInjector()
        retriever = DummyRetriever()
        
        # Run single cycle
        await agent_loop(
            mock_agent_config,
            mock_logger,
            once=True,
            no_delay=True,
            injector=injector,
            retriever=retriever
        )
        
        # Verify prompt was injected
        assert len(injector.injected_prompts) == 1
        assert injector.injected_prompts[0] == "test prompt"
        
        # Verify inbox was archived
        assert not inbox_file.exists()
        assert len(list(mock_agent_config.archive_dir.iterdir())) == 1
    
    async def test_multiple_cycles(self, mock_logger, mock_agent_config, tmp_path):
        """Test multiple cycle execution"""
        # Set up test inbox with multiple prompts
        inbox_file = tmp_path / "inbox.json"
        inbox_file.write_text('[{"prompt": "prompt 1"}, {"prompt": "prompt 2"}]')
        mock_agent_config.inbox_file = inbox_file
        mock_agent_config.archive_dir = tmp_path / "archive"
        mock_agent_config.archive_dir.mkdir(parents=True)
        
        # Set up test components
        injector = DummyInjector()
        retriever = DummyRetriever(responses=["Response 1", "Response 2"])
        
        # Mock sleep to avoid actual delays
        with patch('asyncio.sleep', return_value=None):
            # Run multiple cycles
            await agent_loop(
                mock_agent_config,
                mock_logger,
                once=False,  # Run until stopped
                no_delay=True,
                injector=injector,
                retriever=retriever
            )
        
        # Verify all prompts were injected
        assert len(injector.injected_prompts) == 2
        assert injector.injected_prompts == ["prompt 1", "prompt 2"]
    
    async def test_injection_failure(self, mock_logger, mock_agent_config, tmp_path):
        """Test handling of injection failure"""
        # Set up test inbox
        inbox_file = tmp_path / "inbox.json"
        inbox_file.write_text('[{"prompt": "test prompt"}]')
        mock_agent_config.inbox_file = inbox_file
        
        # Set up test components with failing injector
        injector = DummyInjector(success=False)
        retriever = DummyRetriever()
        
        # Run single cycle
        await agent_loop(
            mock_agent_config,
            mock_logger,
            once=True,
            no_delay=True,
            injector=injector,
            retriever=retriever
        )
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        
        # Verify inbox was not archived (preserved for retry)
        assert inbox_file.exists()
    
    async def test_empty_inbox(self, mock_logger, mock_agent_config, tmp_path):
        """Test handling of empty inbox"""
        # Set up empty inbox
        inbox_file = tmp_path / "inbox.json"
        inbox_file.write_text('[]')
        mock_agent_config.inbox_file = inbox_file
        
        # Set up test components
        injector = DummyInjector()
        retriever = DummyRetriever()
        
        # Run single cycle
        await agent_loop(
            mock_agent_config,
            mock_logger,
            once=True,
            no_delay=True,
            injector=injector,
            retriever=retriever
        )
        
        # Verify no prompts were injected
        assert len(injector.injected_prompts) == 0
        
        # Verify inbox was archived
        assert not inbox_file.exists()
    
    async def test_no_response(self, mock_logger, mock_agent_config, tmp_path):
        """Test handling of no response from retriever"""
        # Set up test inbox
        inbox_file = tmp_path / "inbox.json"
        inbox_file.write_text('[{"prompt": "test prompt"}]')
        mock_agent_config.inbox_file = inbox_file
        
        # Set up test components with no response
        injector = DummyInjector()
        retriever = DummyRetriever(responses=[None])
        
        # Run single cycle
        await agent_loop(
            mock_agent_config,
            mock_logger,
            once=True,
            no_delay=True,
            injector=injector,
            retriever=retriever
        )
        
        # Verify warning was logged
        mock_logger.warning.assert_called_once()
    
    async def test_exception_handling(self, mock_logger, mock_agent_config, tmp_path):
        """Test handling of unexpected exceptions"""
        # Set up test inbox
        inbox_file = tmp_path / "inbox.json"
        inbox_file.write_text('[{"prompt": "test prompt"}]')
        mock_agent_config.inbox_file = inbox_file
        
        # Set up test components that raise exception
        injector = MagicMock()
        injector.inject.side_effect = Exception("Test error")
        retriever = DummyRetriever()
        
        # Run single cycle
        await agent_loop(
            mock_agent_config,
            mock_logger,
            once=True,
            no_delay=True,
            injector=injector,
            retriever=retriever
        )
        
        # Verify error was logged
        mock_logger.error.assert_called_once() 