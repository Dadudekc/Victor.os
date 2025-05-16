"""Tests for the Universal Agent Bootstrap Runner."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.tools.agent_bootstrap_runner import AgentConfig, AgentLoop


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
        startup_delay_sec=0,
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


@pytest.fixture
def mock_bus():
    """Create a mock AgentBus."""
    return AsyncMock(spec=AgentBus)


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def mock_ui_interactor():
    """Create a mock UI interactor."""
    interactor = MagicMock()
    interactor.initialize.return_value = True
    return interactor


@pytest.mark.asyncio
async def test_agent_loop_initialization(
    config, mock_bus, mock_logger, mock_ui_interactor
):
    """Test loop initialization."""
    agent_loop = AgentLoop(
        bus=mock_bus,
        logger=mock_logger,
        ui_interactor=mock_ui_interactor,
        config=config,
    )

    assert agent_loop.config == config
    assert agent_loop.bus == mock_bus
    assert agent_loop.logger == mock_logger
    assert agent_loop.ui_interactor == mock_ui_interactor
    assert agent_loop.state_manager is not None
    assert agent_loop.message_processor is not None


@pytest.mark.asyncio
async def test_process_inbox_success(
    config, mock_bus, mock_logger, mock_ui_interactor, mock_runtime_dir
):
    """Test successful inbox processing."""
    with patch("dreamos.tools.agent_bootstrap_runner.agent_loop.Path") as mock_path:
        mock_path.return_value = mock_runtime_dir

        # Create a test message file
        inbox_dir = (
            mock_runtime_dir / "runtime/agent_comms/agent_mailboxes/Agent-2/inbox"
        )
        message_file = inbox_dir / "test_message.json"
        message_content = {
            "prompt": "Test message",
            "prompt_id": "test-1",
            "timestamp": "2024-03-20T12:00:00Z",
            "type": "instruction",
        }
        message_file.write_text(json.dumps(message_content))

        agent_loop = AgentLoop(
            bus=mock_bus,
            logger=mock_logger,
            ui_interactor=mock_ui_interactor,
            config=config,
        )

        await agent_loop._process_inbox()

        # Verify message was processed and archived
        assert not message_file.exists()
        archived_file = (
            mock_runtime_dir
            / "runtime/agent_comms/agent_mailboxes/Agent-2/processed/test_message.json"
        )
        assert archived_file.exists()


@pytest.mark.asyncio
async def test_handle_legacy_inbox(
    config, mock_bus, mock_logger, mock_ui_interactor, mock_runtime_dir
):
    """Test handling of legacy inbox.json."""
    with patch("dreamos.tools.agent_bootstrap_runner.agent_loop.Path") as mock_path:
        mock_path.return_value = mock_runtime_dir

        # Create a legacy inbox.json
        inbox_file = (
            mock_runtime_dir / "runtime/agent_comms/agent_mailboxes/Agent-2/inbox.json"
        )
        legacy_content = {
            "prompt": "Legacy message",
            "prompt_id": "legacy-1",
            "timestamp": "2024-03-20T12:00:00Z",
            "type": "instruction",
        }
        inbox_file.write_text(json.dumps(legacy_content))

        agent_loop = AgentLoop(
            bus=mock_bus,
            logger=mock_logger,
            ui_interactor=mock_ui_interactor,
            config=config,
        )

        await agent_loop._handle_legacy_inbox()

        # Verify inbox.json was archived
        assert not inbox_file.exists()
        archive_files = list(
            (
                mock_runtime_dir / "runtime/agent_comms/agent_mailboxes/Agent-2/archive"
            ).glob("inbox.*.json")
        )
        assert len(archive_files) == 1


@pytest.mark.asyncio
async def test_run_once(config, mock_bus, mock_logger, mock_ui_interactor):
    """Test running once and exiting."""
    agent_loop = AgentLoop(
        bus=mock_bus,
        logger=mock_logger,
        ui_interactor=mock_ui_interactor,
        config=config,
    )

    with (
        patch.object(agent_loop, "_process_inbox") as mock_process_inbox,
        patch.object(agent_loop, "_handle_legacy_inbox") as mock_handle_legacy,
    ):

        await agent_loop.run(run_once=True)

        mock_process_inbox.assert_called_once()
        mock_handle_legacy.assert_called_once()


@pytest.mark.asyncio
async def test_run_continuous(config, mock_bus, mock_logger, mock_ui_interactor):
    """Test running continuously until interrupted."""
    agent_loop = AgentLoop(
        bus=mock_bus,
        logger=mock_logger,
        ui_interactor=mock_ui_interactor,
        config=config,
    )

    with (
        patch.object(agent_loop, "_process_inbox") as mock_process_inbox,
        patch.object(agent_loop, "_handle_legacy_inbox") as mock_handle_legacy,
        patch("asyncio.sleep", side_effect=[None, KeyboardInterrupt]),
    ):

        await agent_loop.run()

        assert (
            mock_process_inbox.call_count == 1
        )  # One successful cycle before KeyboardInterrupt
        assert mock_handle_legacy.call_count == 1
