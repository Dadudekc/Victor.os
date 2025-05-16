"""
Tests for the agent bootstrap runner main module
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from dreamos.tools.agent_bootstrap_runner.__main__ import main, main_async
from dreamos.tools.agent_bootstrap_runner.config import AgentConfig


@pytest.fixture
def mock_config():
    """Create a mock agent configuration"""
    return MagicMock(spec=AgentConfig)


@pytest.fixture
def mock_bus():
    """Create a mock agent bus"""

    class MockBus:
        def __init__(self):
            self.published_events = []
            self.closed = False

        async def publish(self, topic: str, data: dict):
            self.published_events.append((topic, data))

        async def close(self):
            self.closed = True

    return MockBus()


@pytest.fixture
def mock_logger():
    """Create a mock logger"""
    return MagicMock()


@pytest.fixture
def mock_ui_interactor():
    """Create a mock UI interactor"""
    interactor = MagicMock()
    interactor.initialize.return_value = True
    return interactor


@pytest.mark.asyncio
class TestMainAsync:
    """Tests for main_async function"""

    async def test_successful_run(
        self, mock_config, mock_bus, mock_logger, mock_ui_interactor, monkeypatch
    ):
        """Test successful execution of main_async"""
        # Mock dependencies
        monkeypatch.setattr(
            "dreamos.tools.agent_bootstrap_runner.__main__.AgentConfig",
            lambda *args: mock_config,
        )
        monkeypatch.setattr(
            "dreamos.tools.agent_bootstrap_runner.__main__.AgentBus", lambda: mock_bus
        )
        monkeypatch.setattr(
            "dreamos.tools.agent_bootstrap_runner.__main__.setup_logging",
            lambda *args: (mock_logger, "INFO"),
        )
        monkeypatch.setattr(
            "dreamos.tools.agent_bootstrap_runner.__main__.AgentUIInteractor",
            lambda *args: mock_ui_interactor,
        )

        # Mock agent_loop
        mock_agent_loop = AsyncMock()
        monkeypatch.setattr(
            "dreamos.tools.agent_bootstrap_runner.__main__.agent_loop", mock_agent_loop
        )

        # Run main_async
        await main_async()

        # Verify agent_loop was called
        mock_agent_loop.assert_called_once()
        assert mock_bus.closed

    async def test_ui_interactor_failure(
        self, mock_config, mock_bus, mock_logger, mock_ui_interactor, monkeypatch
    ):
        """Test handling of UI interactor initialization failure"""
        # Mock dependencies
        monkeypatch.setattr(
            "dreamos.tools.agent_bootstrap_runner.__main__.AgentConfig",
            lambda *args: mock_config,
        )
        monkeypatch.setattr(
            "dreamos.tools.agent_bootstrap_runner.__main__.AgentBus", lambda: mock_bus
        )
        monkeypatch.setattr(
            "dreamos.tools.agent_bootstrap_runner.__main__.setup_logging",
            lambda *args: (mock_logger, "INFO"),
        )

        # Mock failing UI interactor
        mock_ui_interactor.initialize.return_value = False
        monkeypatch.setattr(
            "dreamos.tools.agent_bootstrap_runner.__main__.AgentUIInteractor",
            lambda *args: mock_ui_interactor,
        )

        # Run main_async and check for exit
        with pytest.raises(SystemExit) as exc_info:
            await main_async()
        assert exc_info.value.code == 1

    async def test_list_prompts(self, monkeypatch):
        """Test --list-prompts functionality"""
        # Mock dependencies
        mock_list_prompts = MagicMock()
        monkeypatch.setattr(
            "dreamos.tools.agent_bootstrap_runner.__main__.list_available_prompts",
            mock_list_prompts,
        )
        monkeypatch.setattr(
            "dreamos.tools.agent_bootstrap_runner.__main__.parse_args",
            lambda: {"list_prompts": True, "prompt_dir": "test/prompts"},
        )

        # Run main_async and check for exit
        with pytest.raises(SystemExit) as exc_info:
            await main_async()
        assert exc_info.value.code == 0
        mock_list_prompts.assert_called_once_with("test/prompts")


class TestMain:
    """Tests for main function"""

    def test_successful_run(self, monkeypatch):
        """Test successful execution of main"""
        # Mock main_async
        mock_main_async = AsyncMock()
        monkeypatch.setattr(
            "dreamos.tools.agent_bootstrap_runner.__main__.main_async", mock_main_async
        )

        # Run main
        main()

        # Verify main_async was called
        mock_main_async.assert_called_once()

    def test_keyboard_interrupt(self, monkeypatch):
        """Test handling of keyboard interrupt"""
        # Mock main_async to raise KeyboardInterrupt
        mock_main_async = AsyncMock(side_effect=KeyboardInterrupt)
        monkeypatch.setattr(
            "dreamos.tools.agent_bootstrap_runner.__main__.main_async", mock_main_async
        )

        # Run main and check for clean exit
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_general_exception(self, monkeypatch):
        """Test handling of general exceptions"""
        # Mock main_async to raise an exception
        mock_main_async = AsyncMock(side_effect=Exception("Test error"))
        monkeypatch.setattr(
            "dreamos.tools.agent_bootstrap_runner.__main__.main_async", mock_main_async
        )

        # Run main and check for error exit
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
