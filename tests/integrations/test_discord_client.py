import pytest

from dreamos.integrations.discord_client import DiscordClient


@pytest.fixture
def discord_client():
    # Minimal client for testing placeholders
    return DiscordClient(bot_token="dummy_token", webhook_url="dummy_url")


@pytest.mark.asyncio
async def test_discord_client_send_webhook_not_implemented(discord_client):
    with pytest.raises(
        NotImplementedError, match="Discord webhook sending not implemented."
    ):
        await discord_client.send_webhook_message(content="test webhook")


@pytest.mark.asyncio
async def test_discord_client_send_bot_not_implemented(discord_client):
    with pytest.raises(
        NotImplementedError, match="Discord bot message sending not implemented."
    ):
        await discord_client.send_bot_message(
            channel_id=123, content="test bot message"
        )
