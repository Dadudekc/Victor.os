# src/dreamos/integrations/discord_bot.py
import asyncio
import datetime
import json
import logging
import time
from pathlib import Path

from dreamos_ai_organizer.core.state import StateDB

from dreamos.automation.cursor_orchestrator import (
    CursorOrchestrator,  # Added for agent interaction
)

# Import project-specific components
from dreamos.core.config import AppConfig  # Use actual AppConfig
from dreamos.core.errors.exceptions import DreamOSError  # Use project errors

# ADDED: Import file_io
from dreamos.utils import file_io

# from dreamos.utils.gui_utils import copy_text_from_agent # No longer needed here

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

# Project Components
from dreamos.automation.cursor_orchestrator import CursorOrchestrator

# Assuming File IO utilities are available (replace with actual import if needed)
# from dreamos.utils.file_io import write_text_to_file, ensure_directory_exists


# REMOVED Placeholder for file utils as file_io is now imported
# def write_text_to_file(path: Path, content: str):
#     logger.info(f"[Placeholder] Writing {len(content)} chars to {path}")
#     path.parent.mkdir(parents=True, exist_ok=True)
#     path.write_text(content, encoding="utf-8")
#
# def ensure_directory_exists(path: Path):
#     logger.info(f"[Placeholder] Ensuring directory {path} exists.")
#     path.mkdir(parents=True, exist_ok=True)


class DiscordBot:
    """Handles Discord bot connection and command interaction with DreamOS."""

    def __init__(
        self,
        config: AppConfig,
        orchestrator_ref: CursorOrchestrator,
        state_db_ref: StateDB | None = None,
    ):
        global orchestrator  # Set the global orchestrator reference
        orchestrator = orchestrator_ref
        self.config = config
        self.token = self.config.discord_bot_token
        self.prefix = self.config.discord_command_prefix
        self.state_db = state_db_ref

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
                await ctx.send(f"⚙️ Sending prompt to `{agent_id}` via inbox file...")
                # --- Write prompt to Agent's Inbox File ---
                inbox_dir = (
                    Path(self.config.paths.agent_comms_dir)
                    / "agent_mailboxes"
                    / agent_id
                    / "inbox"
                )
                # Use a consistent naming scheme, perhaps including timestamp or prompt ID?
                # For simplicity, using a fixed name - agent logic MUST handle reading & deleting this.
                inbox_file_name = f"discord_prompt_{ctx.message.id}.md"
                inbox_file_path = inbox_dir / inbox_file_name

                try:
                    # MODIFIED: Use file_io.ensure_directory
                    if not file_io.ensure_directory(inbox_dir):
                        logger.error(
                            f"Failed to create inbox directory {inbox_dir} for {agent_id}"
                        )
                        await ctx.send(
                            f"Error: Could not prepare agent inbox for {agent_id}."
                        )
                        return

                    # MODIFIED: Use file_io.write_text_file_atomic (or write_text_file if non-atomic is acceptable)
                    # Assuming atomic write is preferred for robustness.
                    if not file_io.write_text_file_atomic(inbox_file_path, prompt):
                        logger.error(
                            f"Failed to write prompt to inbox file {inbox_file_path} using file_io."
                        )
                        await ctx.send(
                            f"Error: Could not write prompt to agent {agent_id}'s inbox."
                        )
                        return

                    logger.info(f"Prompt written to inbox file: {inbox_file_path}")
                    success = True  # Assume write success if no exception from file_io
                except Exception as write_e:
                    logger.error(
                        f"Unexpected error during prompt inbox write operation for {inbox_file_path}: {write_e}",
                        exc_info=True,
                    )
                    await ctx.send(
                        f"❌ Error delivering prompt to agent `{agent_id}` inbox: {write_e}"
                    )
                    success = False

                if success:
                    logger.info(f"Prompt delivered to inbox for {agent_id}.")
                    # Send initial confirmation, then start monitoring
                    initial_response_msg = await ctx.send(
                        f"✅ Prompt delivered to `{agent_id}`'s inbox. Awaiting response..."
                    )
                    # TODO: Potentially push status to devlog

                    # --- Implement Outbox Monitoring Logic ---
                    try:
                        response_text = await self._monitor_agent_outbox(
                            agent_id,
                            str(
                                ctx.message.id
                            ),  # Original prompt message ID for correlation
                            timeout_seconds=self.config.agent_response_timeout_seconds,  # e.g., 60 seconds from config
                        )
                        if response_text is not None:
                            logger.info(
                                f"Received response from {agent_id} outbox for prompt {ctx.message.id}"
                            )
                            # Truncate if too long for Discord
                            max_len = 1900  # Discord limit is 2000, leave some room
                            response_display = (
                                (response_text[:max_len] + "...")
                                if len(response_text) > max_len
                                else response_text
                            )
                            await initial_response_msg.edit(
                                content=f"🧠 Response from `{agent_id}` ({ctx.author.mention}):"
                            )  # Update original message
                            await ctx.send(
                                f"```\n{response_display}\n```"
                            )  # Send response in a new message for better formatting
                        else:
                            logger.warning(
                                f"Timed out waiting for response from {agent_id} for prompt {ctx.message.id}"
                            )
                            await initial_response_msg.edit(
                                content=f"⚠️ Timed out waiting for response from `{agent_id}` ({ctx.author.mention})."
                            )
                    except Exception as mon_e:
                        logger.error(
                            f"Error during outbox monitoring for {agent_id}, prompt {ctx.message.id}: {mon_e}",
                            exc_info=True,
                        )
                        await initial_response_msg.edit(
                            content=f"❌ Error occurred while waiting for `{agent_id}`'s response ({ctx.author.mention})."
                        )

                else:
                    # Handle cases where inject_prompt returns False or None indicating failure
                    # Failure already handled by the write exception block above
                    pass

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

        # --- START OF ALIASES FOR AGENT COMMANDS ---
        for i in range(1, 9):
            agent_id_str = f"Agent-{i}"

            @self.bot.command(
                name=f"agent{i}",
                help=f"Sends a prompt to {agent_id_str} (e.g., !agent{i} <prompt>).",
            )
            async def _agent_specific_prompt(
                ctx, *, prompt: str, agent_id=agent_id_str
            ):  # Capture agent_id in closure
                # This effectively calls the main agent_prompt logic
                await agent_prompt(ctx, agent_id=agent_id, prompt=prompt)

        # --- END OF ALIASES FOR AGENT COMMANDS ---

        # NEW COMMAND: compile_log
        @self.bot.command(
            name="compile_log",
            help="Retrieve recent devlog entries. Usage: !compile_log [limit=10] [agent=Agent-X]",
        )
        async def compile_log_command(ctx, limit: int = 10, agent: str | None = None):
            if self.state_db is None:
                await ctx.send(
                    "⚠️ Internal Error: Database connection not available for bot."
                )
                logger.error("StateDB not available for !compile_log command.")
                return

            try:
                if not 1 <= limit <= 50:  # Max 50 entries to prevent spam/long messages
                    await ctx.send("⚠️ Limit must be between 1 and 50.")
                    return

                logs = self.state_db.fetch_devlog_entries(limit=limit, agent_name=agent)

                if not logs:
                    message = "📭 No recent devlog entries found"
                    if agent:
                        message += f" for **{agent}**"
                    message += "."
                    await ctx.send(message)
                    return

                response_lines = ["**📒 Recent Devlog Entries:**"]
                if agent:
                    response_lines[0] += f" (Filtered by **{agent}**)"

                for entry in logs:
                    ts_raw = entry.get("timestamp")
                    ts_formatted = str(ts_raw)  # Fallback
                    if ts_raw:
                        try:
                            ts_formatted = datetime.datetime.fromtimestamp(
                                ts_raw
                            ).strftime("%Y-%m-%d %H:%M:%S UTC")
                        except (TypeError, ValueError) as ts_err:
                            logger.warning(
                                f"Could not format timestamp '{ts_raw}': {ts_err}"
                            )

                    agent_name_val = entry.get("agent_name", "N/A")
                    event_type_val = entry.get("event_type", "N/A")
                    status_val = entry.get("status", "N/A")  # .get for safety
                    details_str = entry.get("details_json", "{}")

                    details_display = details_str  # Default to raw JSON string
                    try:
                        details_obj = json.loads(details_str)
                        if isinstance(details_obj, dict) and "message" in details_obj:
                            details_display = str(details_obj["message"])
                        elif isinstance(
                            details_obj, str
                        ):  # If details_json was just a simple string
                            details_display = details_obj
                        # Otherwise, details_display remains the raw details_str (JSON)
                    except json.JSONDecodeError:
                        # If not valid JSON, details_display remains the original string
                        pass

                    # Truncate for display
                    details_display_short = (
                        (details_display[:150] + "...")
                        if len(details_display) > 150
                        else details_display
                    )

                    log_line = (
                        f"\\n🕰️ `{ts_formatted}` 👤 **{agent_name_val}**\\n"
                        f"🔹 {event_type_val} ({status_val}): _{details_display_short}_"
                    )
                    response_lines.append(log_line)

                full_response = "\\n".join(response_lines)

                if len(full_response) > 1950:  # Discord limit is 2000, play safe
                    await ctx.send(full_response[:1950] + "... (truncated)")
                else:
                    await ctx.send(full_response)

            except Exception as e:
                logger.error(
                    f"Error processing !compile_log command: {e}", exc_info=True
                )
                await ctx.send(
                    f"💥 Error fetching/formatting devlog entries: {type(e).__name__} - Please check logs."
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
                    key=lambda x: (
                        int(x.split("-")[1])
                        if x.startswith("Agent-") and x.split("-")[1].isdigit()
                        else float("inf")
                    ),
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

    async def _monitor_agent_outbox(
        self, agent_id: str, original_prompt_id: str, timeout_seconds: int = 60
    ) -> str | None:
        """Monitors the agent's outbox for a response JSON file."""
        outbox_dir = Path(self.config.paths.bridge_outbox_dir)  # Get from AppConfig
        # bridge_outbox_dir should be like: runtime/bridge_outbox/
        # Expected filename pattern: <agent_id>_response_<timestamp>_<original_prompt_id>.json
        # Example: Agent-1_response_20231027_123456_789_123456789012345678.json

        start_time = time.time()
        poll_interval = 2  # seconds

        logger.debug(
            f"Starting to monitor outbox for {agent_id}, prompt_id {original_prompt_id} in {outbox_dir}"
        )

        while time.time() - start_time < timeout_seconds:
            # Glob for any timestamp, but specific agent and prompt ID
            # Ensure bridge_outbox_dir is defined in config.paths
            if (
                not hasattr(self.config.paths, "bridge_outbox_dir")
                or not self.config.paths.bridge_outbox_dir
            ):
                logger.error("bridge_outbox_dir not configured in AppConfig.paths")
                return None  # Cannot monitor without path

            # Construct glob pattern carefully
            # Files are like: Agent-1_response_20240310_001025_909529_1217503043227123712.json
            file_pattern = f"{agent_id}_response_*_{original_prompt_id}.json"
            logger.debug(f"Polling with pattern: {outbox_dir / file_pattern}")

            potential_files = list(outbox_dir.glob(file_pattern))

            if potential_files:
                # Prefer the newest file if multiple somehow match (e.g. by timestamp in name)
                response_file_path = max(
                    potential_files, key=lambda f: f.stat().st_mtime
                )
                logger.info(
                    f"Found response file for {agent_id}, prompt {original_prompt_id}: {response_file_path.name}"
                )
                try:
                    with open(response_file_path, "r", encoding="utf-8") as f:
                        response_data = json.load(f)

                    # TODO: Archive/delete the processed response file from outbox
                    # E.g., move_file_placeholder(response_file_path, outbox_dir / "processed")
                    # For now, just log it
                    logger.info(
                        f"Successfully read and parsed {response_file_path.name}. Would archive now."
                    )

                    return response_data.get(
                        "response"
                    )  # Extract the actual response text
                except json.JSONDecodeError as json_e:
                    logger.error(
                        f"Invalid JSON in response file {response_file_path.name}: {json_e}"
                    )
                    # Optionally, move corrupted file to an error directory
                    return f"Error: Agent response was not valid JSON: {json_e}"  # Return error as response
                except Exception as read_e:
                    logger.error(
                        f"Error reading response file {response_file_path.name}: {read_e}"
                    )
                    return f"Error: Could not read agent response file: {read_e}"  # Return error as response

            await asyncio.sleep(poll_interval)  # Wait before polling again

        logger.warning(
            f"Timeout reached waiting for response from {agent_id} for prompt {original_prompt_id}"
        )
        return None  # Timeout


# Example usage (requires DISCORD_BOT_TOKEN env var)
async def main():
    logging.basicConfig(level=logging.INFO)
    cfg = AppConfig()
    orch = CursorOrchestrator(cfg)  # Assuming orchestrator needs config

    # ADDED: Instantiate StateDB
    # Ensure the path to ai_state.db is correct for your project structure.
    # This was previously dreamos_ai_organizer/ai_state.db
    # TODO: Confirm correct DB path and StateDB import path if issues arise.
    db_path = cfg.paths.project_root / "dreamos_ai_organizer" / "ai_state.db"
    try:
        state_db = StateDB(path=str(db_path))  # StateDB expects path as string
        logger.info(f"StateDB initialized with path: {db_path}")
    except Exception as e:
        logger.error(f"Failed to initialize StateDB at {db_path}: {e}", exc_info=True)
        state_db = None  # Ensure bot can start, but compile_log will fail gracefully

    if not cfg.discord_bot_token:
        print("Error: DISCORD_BOT_TOKEN environment variable not set.")
        logger.error("Error: DISCORD_BOT_TOKEN environment variable not set.")
        return

    # MODIFIED: Pass state_db to DiscordBot constructor
    bot_instance = DiscordBot(cfg, orchestrator_ref=orch, state_db_ref=state_db)
    await bot_instance.run_bot()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped manually.")
