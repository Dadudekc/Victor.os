"""
TBOW Tactics Discord Bot Example

This script demonstrates how to use the TBOW Tactics Discord integration.
It shows how to:
1. Initialize the Discord bot
2. Process commands
3. Send trade alerts
4. Update status
"""

import os
import logging
from dotenv import load_dotenv
from basicbot.tbow_tactics import TBOWTactics
from basicbot.tbow_discord import TBOWDiscord

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run the TBOW Discord bot."""
    try:
        # Get Discord token from environment
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise ValueError("DISCORD_TOKEN not found in environment variables")
        
        # Initialize TBOW Tactics
        tbow = TBOWTactics(
            symbol="SPY",  # Default symbol
            timeframe="1Min"
        )
        
        # Initialize Discord bot
        bot = TBOWDiscord(
            token=token,
            tbow_tactics=tbow,
            logger=logger
        )
        
        # Run the bot
        logger.info("Starting TBOW Discord bot...")
        bot.run_bot()
        
    except Exception as e:
        logger.error(f"Error running Discord bot: {e}")

if __name__ == "__main__":
    main() 