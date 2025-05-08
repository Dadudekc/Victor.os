# src/dreamos/integrations/discord_bot.py
import logging
import os
import asyncio

# Requires: pip install discord.py
try:
    import discord
    from discord.ext import commands
    DISCORD_PY_AVAILABLE = True
    logger = logging.getLogger(__name__) # Define logger early
    logger.info("discord.py library found.")
except ImportError:
    DISCORD_PY_AVAILABLE = False
    # Define logger even if import fails for consistent logging
    logger = logging.getLogger(__name__)
    logger.warning("discord.py library not installed. DiscordBot cannot run.")
    # Define dummy classes if import fails
    class commands:
        class Bot:
             def __init__(self, command_prefix, intents): pass
             async def start(self, token): pass
             async def close(self): pass
             def is_closed(self): return True
             # Add dummy tree for attribute access
             class tree:
                 @staticmethod
                 def command(**kwargs):
                     def decorator(func): return func
                     return decorator
             # Add dummy event decorator
             @staticmethod
             def event(func): return func
             # Add dummy command decorator
             @staticmethod
             def command(**kwargs):
                     def decorator(func): return func
                     return decorator

    class discord:
        class Intents:
             @staticmethod
             def default(): return None
        class Interaction: pass # Add dummy Interaction for type hint below
        class LoginFailure(Exception): pass

# Placeholder for config access
# from dreamos.core.config import AppConfig
class AppConfig: # Placeholder
    def __init__(self):
         self.discord_bot_token = os.environ.get("DISCORD_BOT_TOKEN")
         self.discord_command_prefix = os.environ.get("DISCORD_COMMAND_PREFIX", "!")

class DiscordBot:
    """Handles Discord bot connection and basic command interaction."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.token = self.config.discord_bot_token
        self.prefix = self.config.discord_command_prefix

        if not DISCORD_PY_AVAILABLE:
            logger.error("Cannot initialize DiscordBot: discord.py library not installed.")
            self.bot = None
            return

        if not self.token:
            logger.error("Cannot initialize DiscordBot: DISCORD_BOT_TOKEN not found in config/environment.")
            self.bot = None
            return

        intents = discord.Intents.default()
        intents.message_content = True # Enable message content intent if needed for prefix commands
        # intents.guilds = True # Often needed
        # intents.members = True # May need for user info

        self.bot = commands.Bot(command_prefix=self.prefix, intents=intents)
        self._register_events()
        self._register_commands()
        logger.info(f"DiscordBot initialized with prefix '{self.prefix}'.")

    def _register_events(self):
        """Register Discord event handlers."""
        @self.bot.event
        async def on_ready():
            # Ensure self.bot.user is available before logging
            if self.bot and self.bot.user:
                 logger.info(f"Discord bot logged in as {self.bot.user}")
                 print(f"Bot {self.bot.user} is ready.") # Print for visibility if run directly
            else:
                 logger.error("Bot object or user not available in on_ready.")

        @self.bot.event
        async def on_command_error(ctx, error):
            logger.error(f"Discord command error in command '{ctx.command}': {error}", exc_info=True)
            try:
                 await ctx.send(f"An error occurred executing that command: {type(error).__name__}") # Inform user
            except Exception as send_e:
                 logger.error(f"Failed to send error message to Discord context: {send_e}")

    def _register_commands(self):
        """Register basic Discord commands."""
        @self.bot.command(name='ping')
        async def ping(ctx):
            """Responds with Pong! and bot latency.""" # Docstring added
            latency = self.bot.latency * 1000 # Convert to ms
            logger.info(f"Received ping command from {ctx.author}. Latency: {latency:.2f}ms")
            await ctx.send(f'Pong! Latency: {latency:.2f}ms')

        # Placeholder for command injection - requires TaskNexus/PBM access
        @self.bot.command(name='addtask')
        async def add_task(ctx, *, description: str):
            """Adds a task to the DreamOS backlog (Placeholder)."""
            logger.info(f"Received addtask command from {ctx.author}: {description}")
            # TODO: Implement actual task injection logic
            # - Needs access to TaskNexus or PBM/ShadowNexus
            # - Needs error handling & confirmation
            # - Needs task ID generation
            # Example: success = task_nexus.add_task({...})
            await ctx.send(f"Received request to add task: '{description[:100]}...' (Implementation Pending)")

        # Example using newer slash commands (requires syncing)
        # Note: Slash commands often preferred for discoverability & permissions
        @self.bot.tree.command(name="hello", description="Says hello!")
        async def hello(interaction: discord.Interaction):
             """Says hello!"""
             logger.info(f"Received hello slash command from {interaction.user}")
             # Ensure interaction is responded to quickly
             await interaction.response.send_message(f"Hello, {interaction.user.mention}!")


    async def run_bot(self):
        """Connects and runs the bot indefinitely until stopped."""
        if not self.bot:
            logger.error("Bot not initialized correctly. Cannot run.")
            return

        logger.info("Starting Discord bot...")
        try:
            # Consider syncing commands conditionally or on first run
            # if not hasattr(self.bot, '_synced_commands'):
            #     await self.bot.tree.sync()
            #     self.bot._synced_commands = True # Prevent re-syncing
            #     logger.info("Slash commands synced.")

            await self.bot.start(self.token)
        except discord.LoginFailure:
            logger.critical("Discord login failed: Invalid token provided. Check DISCORD_BOT_TOKEN.")
        except Exception as e:
            logger.critical(f"Critical error running Discord bot: {e}", exc_info=True)
        finally:
             logger.info("Initiating Discord bot shutdown sequence...")
             if self.bot and not self.bot.is_closed():
                  await self.bot.close()
             logger.info("Discord bot connection closed.")

# Example usage (requires DISCORD_BOT_TOKEN env var)
# async def main():
#      logging.basicConfig(level=logging.INFO)
#      cfg = AppConfig()
#      if not cfg.discord_bot_token:
#          print("Error: DISCORD_BOT_TOKEN environment variable not set.")
#          return
#      bot_instance = DiscordBot(cfg)
#      await bot_instance.run_bot()
#
# if __name__ == "__main__":
#      try:
#          asyncio.run(main())
#      except KeyboardInterrupt:
#          print("Bot stopped manually.") 