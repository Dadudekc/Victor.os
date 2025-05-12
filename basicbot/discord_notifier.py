import discord
import asyncio
from basicbot.config import config  # ✅ Import centralized config
from basicbot.logger import setup_logging  # ✅ Import our custom logger

class DiscordNotifier:
    def __init__(self):
        """Initialize Discord bot with intents and token from config."""
        self.TOKEN = config.get_env("DISCORD_BOT_TOKEN")
        self.CHANNEL_ID = config.get_env("DISCORD_CHANNEL_ID", cast_type=int)

        # ✅ Initialize custom logger
        self.logger = setup_logging("discord_notifier")

        if not self.TOKEN or not self.CHANNEL_ID:
            self.logger.error("❌ Missing DISCORD_BOT_TOKEN or DISCORD_CHANNEL_ID in environment variables.")
            raise ValueError("Missing DISCORD_BOT_TOKEN or DISCORD_CHANNEL_ID")

        intents = discord.Intents.default()
        self.client = discord.Client(intents=intents)

    async def send_message(self, message: str):
        """Sends a message to the configured Discord channel."""
        await self.client.wait_until_ready()
        channel = self.client.get_channel(self.CHANNEL_ID)

        if channel:
            await channel.send(message)
            self.logger.info(f"✅ Sent message to channel {self.CHANNEL_ID}: {message}")
        else:
            self.logger.error("❌ Discord Channel not found! Check your CHANNEL_ID.")

    def run(self):
        """Starts the Discord bot."""
        @self.client.event
        async def on_ready():
            self.logger.info(f"✅ Logged in as {self.client.user}")

        try:
            self.client.run(self.TOKEN)
        except Exception as e:
            self.logger.error(f"❌ Discord bot encountered an error: {e}")

# ✅ Example usage
if __name__ == "__main__":
    notifier = DiscordNotifier()
    
    # Run the bot in a separate thread to allow async operations
    loop = asyncio.get_event_loop()
    loop.create_task(notifier.send_message("🚀 Trading bot is now live!"))
    notifier.run()
