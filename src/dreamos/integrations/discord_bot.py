# src/dreamos/integrations/discord_bot.py
import logging

from dreamos.automation.cursor_orchestrator import (
    CursorOrchestrator,  # Added for agent interaction
)

# Import project-specific components
from dreamos.core.config import AppConfig  # Use actual AppConfig
from dreamos.core.errors.exceptions import DreamOSError  # Use project errors

# Global instance (or dependency injection needed)
# TODO: Determine how orchestrator instance is managed/passed
orchestrator: CursorOrchestrator | None = None

# Requires: pip install discord.py
try:
    import discord
    from discord.ext import commands

    DISCORD_PY_AVAILABLE = True
    logger = logging.getLogger(__name__)  # Define logger early
    logger.info("discord.py library found.")
except ImportError:
    DISCORD_PY_AVAILABLE = False
    # Define logger even if import fails for consistent logging
    logger = logging.getLogger(__name__)
    logger.warning("discord.py library not installed. DiscordBot cannot run.")

    # Define dummy classes if import fails
    class commands:
        class Bot:
            def __init__(self, command_prefix, intents):
                pass

            async def start(self, token):
                pass

            async def close(self):
                pass

            def is_closed(self):
                return True

            # Add dummy tree for attribute access
            class tree:
                @staticmethod
                def command(**kwargs):
                    def decorator(func):
                        return func

                    return decorator

            # Add dummy event decorator
            @staticmethod
            def event(func):
                return func

            # Add dummy command decorator
            @staticmethod
            def command(**kwargs):
                def decorator(func):
                    return func

                return decorator

    class discord:
        class Intents:
            @staticmethod
            def default():
                return None

        class Interaction:
            pass  # Add dummy Interaction for type hint below

        class LoginFailure(Exception):
            pass

# Placeholder for config access
# from dreamos.core.config import AppConfig
# (Placeholder AppConfig removed, using imported one)


class DiscordBot:
    """Handles Discord bot connection and command interaction with DreamOS."""

    def __init__(self, config: AppConfig, orchestrator_ref: CursorOrchestrator):
        global orchestrator  # Set the global orchestrator reference
        orchestrator = orchestrator_ref
        self.config = config
        self.token = self.config.discord_bot_token
        self.prefix = self.config.discord_command_prefix

        if not DISCORD_PY_AVAILABLE:
            logger.error(
                "Cannot initialize DiscordBot: discord.py library not installed."
            )
            self.bot = None
            return

        if not self.token:
            logger.error(
                "Cannot initialize DiscordBot: DISCORD_BOT_TOKEN not found in config/environment."
            )
            self.bot = None
            return

        intents = discord.Intents.default()
        intents.message_content = (
            True  # Enable message content intent if needed for prefix commands
        )
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
                print(
                    f"Bot {self.bot.user} is ready."
                )  # Print for visibility if run directly
            else:
                logger.error("Bot object or user not available in on_ready.")

        @self.bot.event
        async def on_command_error(ctx, error):
            logger.error(
                f"Discord command error in command '{ctx.command}': {error}",
                exc_info=True,
            )
            try:
                await ctx.send(
                    f"An error occurred executing that command: {type(error).__name__}"
                )  # Inform user
            except Exception as send_e:
                logger.error(
                    f"Failed to send error message to Discord context: {send_e}"
                )

    def _register_commands(self):
        """Register basic Discord commands."""

        @self.bot.command(name="ping")
        async def ping(ctx):
            """Responds with Pong! and bot latency."""  # Docstring added
            latency = self.bot.latency * 1000  # Convert to ms
            logger.info(
                f"Received ping command from {ctx.author}. Latency: {latency:.2f}ms"
            )
            await ctx.send(f"Pong! Latency: {latency:.2f}ms")

        @self.bot.command(
            name="agent",
            help="Sends a prompt to a specific agent (e.g., !agent Agent-1 <prompt>).",
        )
        async def agent_prompt(ctx, agent_id: str, *, prompt: str):
            """Injects the provided prompt into the specified agent's Cursor session."""
            # Basic validation for agent ID format
            valid_agent_ids = {f"Agent-{i}" for i in range(1, 9)}
            if agent_id not in valid_agent_ids:
                valid_ids_str = ", ".join(sorted(list(valid_agent_ids)))
                await ctx.send(
                    f"❌ Invalid agent ID '{agent_id}'. Valid IDs are: {valid_ids_str}."
                )
                return

            logger.info(
                f"Received !agent command from {ctx.author} for {agent_id}: '{prompt[:100]}...'"
            )

            if orchestrator is None:
                logger.error("Orchestrator not available for !agent command.")
                await ctx.send("Error: Agent orchestrator is not available.")
                return

            if not prompt:
                await ctx.send(
                    f"Error: Please provide a prompt after the agent ID. Usage: `{self.prefix}agent <Agent-ID> <your prompt>`"
                )
                return

            try:
                await ctx.send(f"⚙️ Sending prompt to `{agent_id}`...")
                # Actual call to orchestrator
                # Assuming orchestrator.inject_prompt exists and takes agent_id and prompt_text
                success = await orchestrator.inject_prompt(
                    agent_id=agent_id, prompt_text=prompt
                )

                if success:
                    logger.info(
                        f"Successfully injected prompt via orchestrator for !agent command to {agent_id}."
                    )
                    await ctx.send(f"✅ Prompt sent to `{agent_id}`.")
                    # TODO: Potentially push status to devlog
                else:
                    # Handle cases where inject_prompt returns False or None indicating failure
                    logger.warning(
                        f"Orchestrator reported failure injecting prompt for !agent command to {agent_id}."
                    )
                    await ctx.send(
                        f"⚠️ Failed to inject prompt into `{agent_id}` (Orchestrator reported failure)."
                    )

            except DreamOSError as e:  # Keep specific error handling
                logger.error(
                    f"DreamOS error handling !agent command for {agent_id}: {e}",
                    exc_info=True,
                )
                await ctx.send(f"❌ Error interacting with agent `{agent_id}`: {e}")
            except Exception as e:  # Keep generic fallback
                logger.critical(
                    f"Unexpected error handling !agent command for {agent_id}: {e}",
                    exc_info=True,
                )
                await ctx.send(
                    f"❌ An critical unexpected error occurred while sending prompt to `{agent_id}`: {e}"
                )

        # Placeholder for command injection - requires TaskNexus/PBM access
        @self.bot.command(name="addtask")
        async def add_task(ctx, *, description: str):
            """Adds a task to the DreamOS backlog (Placeholder)."""
            logger.info(f"Received addtask command from {ctx.author}: {description}")
            # TODO: Implement actual task injection logic
            # - Needs access to TaskNexus or PBM/ShadowNexus
            # - Needs error handling & confirmation
            # - Needs task ID generation
            # Example: success = task_nexus.add_task({...})
            await ctx.send(
                f"Received request to add task: '{description[:100]}...' (Implementation Pending)"
            )

        # Example using newer slash commands (requires syncing)
        # Note: Slash commands often preferred for discoverability & permissions
        @self.bot.tree.command(name="hello", description="Says hello!")
        async def hello(interaction: discord.Interaction):
            """Says hello!"""
            logger.info(f"Received hello slash command from {interaction.user}")
            # Ensure interaction is responded to quickly
            await interaction.response.send_message(
                f"Hello, {interaction.user.mention}!"
            )

        @self.bot.command(name="status")
        async def status_command(ctx):  # Renamed self to ctx as it's a command context
            """Returns the current status of all agents."""
            logger.info(f"Received !status command from {ctx.author}")
            try:
                # Attempt to get live status from orchestrator first
                status_data = None
                if orchestrator and hasattr(orchestrator, "agent_status"):
                    # Accessing potentially dynamic status - ensure it's dict-like
                    if callable(orchestrator.agent_status):
                        # Handle if agent_status is a method
                        try:
                            status_data = await orchestrator.agent_status()
                        except Exception as e:
                            logger.warning(
                                f"Error calling orchestrator.agent_status(): {e}",
                                exc_info=True,
                            )
                    elif isinstance(orchestrator.agent_status, dict):
                        # Handle if agent_status is a dictionary attribute
                        status_data = orchestrator.agent_status
                    else:
                        logger.warning(
                            f"Orchestrator agent_status attribute is not callable or a dict: {type(orchestrator.agent_status)}"
                        )

                if (
                    status_data is None
                ):  # Fallback to file if orchestrator status unavailable
                    logger.info(
                        "Orchestrator status unavailable, falling back to status file."
                    )
                    import json
                    from pathlib import Path

                    # TODO: Get status file path from config? Hardcoded for now.
                    status_file = (
                        Path(self.config.paths.runtime_dir)
                        / "status"
                        / "agent_status.json"
                    )
                    if not status_file.exists():
                        logger.warning(f"Agent status file not found at: {status_file}")
                        await ctx.send(
                            f"⚠️ Status file not found at `{status_file.relative_to(self.config.paths.project_root)}`. Orchestrator status also unavailable."
                        )
                        return
                    try:
                        with open(status_file, "r", encoding="utf-8") as f:
                            status_data = json.load(f)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode status file {status_file}: {e}")
                        await ctx.send("❌ Error reading status file: Invalid JSON.")
                        return
                    except OSError as e:
                        logger.error(f"Failed to read status file {status_file}: {e}")
                        await ctx.send(f"❌ Error reading status file: {e}")
                        return

                if (
                    not status_data
                ):  # Check if status_data is empty after trying both sources
                    await ctx.send(
                        "⚠️ No agent status information available from any source."
                    )
                    return

                lines = ["📡 **Agent Status**"]
                # Sort agents for consistent output, e.g., Agent-1, Agent-2...
                sorted_agent_ids = sorted(
                    status_data.keys(),
                    key=lambda x: int(x.split("-")[1])
                    if x.startswith("Agent-") and x.split("-")[1].isdigit()
                    else float("inf"),
                )
                for agent_id in sorted_agent_ids:
                    state = status_data.get(
                        agent_id, "UNKNOWN"
                    )  # Handle missing keys gracefully
                    emoji = {
                        "IDLE": "✅",
                        "BUSY": "⚙️",  # Added BUSY state
                        "THINKING": "🤔",  # Added THINKING state
                        "INJECTING": "🛠️",
                        "AWAITING_RESPONSE": "🟡",
                        "ERROR": "❌",
                        "OFFLINE": "⚫",  # Added OFFLINE state
                        "UNKNOWN": "❓",  # Added UNKNOWN state
                    }.get(
                        state.upper(), "❓"
                    )  # Use state.upper() for case-insensitivity
                    lines.append(f"{emoji} **{agent_id}**: `{state}`")

                await ctx.send("\n".join(lines))

            except Exception as e:
                logger.critical(
                    f"Unexpected error in !status command: {e}", exc_info=True
                )
                await ctx.send(
                    f"❌ An unexpected error occurred while retrieving status: `{str(e)}`"
                )

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
            logger.critical(
                "Discord login failed: Invalid token provided. Check DISCORD_BOT_TOKEN."
            )
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
#      orch = CursorOrchestrator(cfg) # Assuming orchestrator needs config
#      if not cfg.discord_bot_token:
#          print("Error: DISCORD_BOT_TOKEN environment variable not set.")
#          return
#      bot_instance = DiscordBot(cfg, orchestrator_ref=orch)
#      await bot_instance.run_bot()
#
# if __name__ == "__main__":
#      try:
#          asyncio.run(main())
#      except KeyboardInterrupt:
#          print("Bot stopped manually.")
