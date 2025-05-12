import pytest
import logging
from unittest.mock import AsyncMock, patch, MagicMock
from basicbot.discord_notifier import DiscordNotifier

# Fixture: Mock environment variables
@pytest.fixture
def mock_env():
    with patch.dict("os.environ", {"DISCORD_BOT_TOKEN": "mock_token", "DISCORD_CHANNEL_ID": "123456789"}):
        yield

# Fixture: Create a DiscordNotifier instance with the mocked environment and logger
@pytest.fixture
def notifier(mock_env):
    with patch("basicbot.discord_notifier.setup_logging") as mock_setup:
        dummy_logger = logging.getLogger("dummy")
        dummy_logger.setLevel(logging.DEBUG)
        mock_setup.return_value = dummy_logger
        bot = DiscordNotifier()
        # Override TOKEN and CHANNEL_ID for consistency
        bot.TOKEN = "mock_token"
        bot.CHANNEL_ID = 123456789
        return bot

### TEST: Initialization ###
@patch("basicbot.discord_notifier.config.get_env", side_effect=lambda key, cast_type=None: 
       "mock_token" if key == "DISCORD_BOT_TOKEN" else 123456789)
def test_notifier_initialization(mock_config):
    bot = DiscordNotifier()
    assert bot.TOKEN == "mock_token"
    assert bot.CHANNEL_ID == 123456789

### TEST: Missing Credentials ###
@patch("basicbot.discord_notifier.config.get_env", side_effect=lambda key, cast_type=None: None)
def test_notifier_missing_credentials(mock_config):
    with pytest.raises(ValueError, match="Missing DISCORD_BOT_TOKEN or DISCORD_CHANNEL_ID"):
        DiscordNotifier()

### TEST: Bot Startup ###
@patch("basicbot.discord_notifier.discord.Client")
def test_bot_starts(mock_discord_client, notifier):
    mock_client_instance = mock_discord_client.return_value
    notifier.client = mock_client_instance

    with patch.object(mock_client_instance, "run", return_value=None) as mock_run:
        notifier.run()
        mock_run.assert_called_once_with("mock_token")

### TEST: Sending Message Successfully ###
@pytest.mark.asyncio
@patch("basicbot.discord_notifier.discord.Client")
async def test_send_message(mock_discord_client, notifier):
    # Use a standard MagicMock for the client instance.
    mock_client_instance = MagicMock()
    # Override wait_until_ready with an AsyncMock that resolves immediately.
    mock_client_instance.wait_until_ready = AsyncMock(return_value=None)
    
    # Create a mock channel and override its send method with an async function.
    mock_channel = MagicMock()
    async def fake_send(message):
        return None
    mock_channel.send = AsyncMock(side_effect=fake_send)
    
    # Configure get_channel to return the mock channel.
    mock_client_instance.get_channel.return_value = mock_channel
    notifier.client = mock_client_instance

    await notifier.send_message("Test Message")

    mock_client_instance.get_channel.assert_called_once_with(notifier.CHANNEL_ID)
    mock_channel.send.assert_awaited_once_with("Test Message")

### TEST: Handling Missing Channel ###
@pytest.mark.asyncio
@patch("basicbot.discord_notifier.discord.Client")
async def test_send_message_no_channel(mock_discord_client, notifier):
    mock_client_instance = MagicMock()
    mock_client_instance.wait_until_ready = AsyncMock(return_value=None)
    # Simulate missing channel by returning None.
    mock_client_instance.get_channel.return_value = None
    notifier.client = mock_client_instance

    # This should complete without raising an exception.
    await notifier.send_message("Test Message")
    mock_client_instance.get_channel.assert_called_once_with(notifier.CHANNEL_ID)
