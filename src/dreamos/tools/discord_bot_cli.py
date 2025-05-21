"""
CLI script to run the Dream.OS Discord bot.
"""

import asyncio
import logging
import sys

from dreamos.core.config import AppConfig
from dreamos.automation.cursor_orchestrator import CursorOrchestrator
from dreamos.tools.discord_bot import DiscordBot

logger = logging.getLogger(__name__)

async def main():
    """Main entry point for Discord bot CLI."""
    try:
        # Load configuration
        config = AppConfig()
        
        # Initialize orchestrator
        orchestrator = CursorOrchestrator(config)
        
        # Create and start bot
        bot = DiscordBot(config, orchestrator)
        await bot.start_bot()
        
    except Exception as e:
        logger.error(f"Error running Discord bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 