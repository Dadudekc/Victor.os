import json
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from ..modules.voice_commands import VoiceCommandHandler


@pytest.fixture
def test_env(tmp_path):
    """Setup test environment"""
    # Create test directories
    inbox_base = tmp_path / "mailbox"
    inbox_base.mkdir()

    # Create test agent inbox
    agent_inbox = inbox_base / "Agent-1" / "inbox.json"
    agent_inbox.parent.mkdir()
    agent_inbox.write_text("[]")

    # Create test audio file
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    return {
        "inbox_base": inbox_base,
        "model_path": Path("models/whisper/base.pt"),
        "audio_dir": audio_dir,
    }


@pytest.fixture
def voice_handler(test_env):
    """Create voice handler instance"""
    return VoiceCommandHandler(test_env["inbox_base"], test_env["model_path"])


@pytest.fixture
def mock_audio():
    """Create mock audio data"""
    fs = 16000
    duration = 1
    t = np.linspace(0, duration, int(fs * duration))
    return np.sin(2 * np.pi * 440 * t)


def test_voice_handler_initialization(voice_handler):
    """Test voice handler initialization"""
    assert voice_handler.inbox_base.exists()
    assert voice_handler.audio_file.parent.exists()


@pytest.mark.asyncio
async def test_record_audio(voice_handler, mock_audio):
    """Test audio recording with proper stream mocking"""
    from unittest.mock import MagicMock, PropertyMock

    with (
        patch("sounddevice.rec") as mock_rec,
        patch("sounddevice.wait") as mock_wait,
        patch("soundfile.write") as mock_write,
        patch("sounddevice.get_stream") as mock_get_stream,
    ):
        mock_rec.return_value = mock_audio
        # Mock stream with .active property using PropertyMock
        mock_stream = MagicMock()
        active_sequence = [True, False]
        prop = PropertyMock(side_effect=lambda: active_sequence.pop(0))
        type(mock_stream).active = prop
        mock_get_stream.return_value = mock_stream
        await voice_handler.record_audio(seconds=1)
        mock_rec.assert_called_once()
        mock_wait.assert_called_once()
        mock_write.assert_called_once()


@pytest.mark.asyncio
async def test_transcribe(voice_handler):
    """Test transcription"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        # Create test transcription file
        txt_file = voice_handler.audio_file.with_suffix(".txt")
        txt_file.write_text("agent 1: scan the logs")

        transcript = await voice_handler.transcribe()
        assert transcript == "agent 1: scan the logs"


def test_command_template_validation():
    """Test command template validation"""
    # Test with valid templates
    handler = VoiceCommandHandler(
        inbox_base=Path("test_inbox"), model_path=Path("test_model")
    )
    assert (
        handler.command_templates["scan"]["pattern"]
        == r"scan\s+(.+)(?:\s+and\s+escalate)?"
    )

    # Test with invalid non-greedy pattern
    with pytest.raises(ValueError, match="Non-greedy pattern"):
        handler.command_templates["scan"][
            "pattern"
        ] = r"scan\s+(.+?)(?:\s+and\s+escalate)?"
        handler._validate_command_templates()

    # Test with invalid pattern that doesn't match basic input
    with pytest.raises(ValueError, match="does not match basic input"):
        handler.command_templates["scan"]["pattern"] = r"invalid\s+pattern"
        handler._validate_command_templates()


def test_parse_agent_command():
    """Test agent command parsing with various formats"""
    handler = VoiceCommandHandler(
        inbox_base=Path("test_inbox"), model_path=Path("test_model")
    )

    # Test basic command
    agent_id, command = handler.parse_agent_command("agent 1: scan the logs")
    assert agent_id == "Agent-1"
    assert command == "Scan the logs and report findings"

    # Test command with additional context
    agent_id, command = handler.parse_agent_command(
        "agent 2: scan the logs and escalate"
    )
    assert agent_id == "Agent-2"
    assert command == "Scan the logs and escalate and report findings"

    # Test command with special characters
    agent_id, command = handler.parse_agent_command("agent 3: scan /path/to/logs/*.log")
    assert agent_id == "Agent-3"
    assert command == "Scan /path/to/logs/*.log and report findings"

    # Test invalid command
    agent_id, command = handler.parse_agent_command("invalid command")
    assert agent_id is None
    assert command is None


@pytest.mark.asyncio
async def test_inject_to_inbox(voice_handler):
    """Test command injection with standardized message format"""
    agent_id = "Agent-1"
    command = "test command"

    await voice_handler.inject_to_inbox(agent_id, command)

    # Verify command was added to inbox
    inbox_path = voice_handler.inbox_base / agent_id / "inbox.json"
    messages = json.loads(inbox_path.read_text())

    assert len(messages) == 1
    message = messages[0]
    assert message["type"] == "COMMAND"
    assert message["sender_agent_id"] == "voice_command"
    assert message["recipient_agent_id"] == agent_id
    assert "message_id" in message
    assert "timestamp_utc" in message
    assert "subject" in message
    assert message["body"]["command"] == command
    assert message["body"]["source"] == "voice_input"
    assert message["priority"] == "MEDIUM"


def test_validate_mailbox_message(voice_handler):
    """Test mailbox message validation"""
    # Valid message
    valid_msg = {
        "message_id": "test-123",
        "sender_agent_id": "Agent-1",
        "recipient_agent_id": "Agent-2",
        "timestamp_utc": "2024-03-20T12:00:00Z",
        "subject": "Test Message",
        "type": "INFO",
        "body": {"content": "test"},
    }
    assert voice_handler._validate_mailbox_message(valid_msg) is True

    # Invalid message (missing fields)
    invalid_msg = {"message_id": "test-123", "type": "INFO"}
    assert voice_handler._validate_mailbox_message(invalid_msg) is False


def test_convert_legacy_message(voice_handler):
    """Test legacy message conversion"""
    legacy_msg = {
        "id": "legacy-123",
        "type": "voice_command",
        "content": "test command",
        "timestamp": 1710936000,
        "status": "pending",
    }

    converted = voice_handler._convert_legacy_message(legacy_msg)
    assert converted["message_id"] == "legacy-123"
    assert converted["type"] == "VOICE_COMMAND"
    assert converted["body"]["content"] == "test command"
    assert converted["body"]["original_format"] == "legacy"
    assert "timestamp_utc" in converted
    assert converted["priority"] == "MEDIUM"


def test_command_history(voice_handler):
    """Test command history tracking"""
    # Add some commands
    voice_handler._add_to_history("Agent-1", "command 1")
    voice_handler._add_to_history("Agent-1", "command 2")
    voice_handler._add_to_history("Agent-2", "command 3")

    # Check history
    history_1 = voice_handler.get_command_history("Agent-1")
    assert len(history_1) == 2
    assert history_1[0]["command"] == "command 1"
    assert history_1[1]["command"] == "command 2"

    history_2 = voice_handler.get_command_history("Agent-2")
    assert len(history_2) == 1
    assert history_2[0]["command"] == "command 3"


@pytest.mark.asyncio
async def test_full_pipeline(voice_handler, mock_audio):
    """Test full voice command pipeline"""
    with (
        patch("sounddevice.rec") as mock_rec,
        patch("sounddevice.wait"),
        patch("soundfile.write"),
        patch("subprocess.run") as mock_run,
    ):

        # Setup mocks
        mock_rec.return_value = mock_audio
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        # Create test transcription
        txt_file = voice_handler.audio_file.with_suffix(".txt")
        txt_file.write_text("agent 1: scan the logs")

        # Create inbox directory and file
        inbox_dir = voice_handler.inbox_base / "Agent-1"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        inbox_path = inbox_dir / "inbox.json"
        inbox_path.write_text("[]")  # Initialize empty inbox

        # Run pipeline
        await voice_handler.process_voice_command()

        # Verify command was added to inbox
        messages = json.loads(inbox_path.read_text())
        assert len(messages) == 1
        assert messages[0]["recipient_agent_id"] == "Agent-1"
        assert messages[0]["type"] == "COMMAND"
        assert "scan" in messages[0]["body"]["command"].lower()
