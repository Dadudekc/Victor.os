"""
Command-line interface for sending direct messages to agents.
"""

import argparse
import logging
from agent_messenger import AgentMessenger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Send a direct message to another agent")
    parser.add_argument("target_agent", help="Target agent ID (e.g., Agent-1)")
    parser.add_argument("message", help="Message to send")
    parser.add_argument("--dry-run", action="store_true", help="Simulate sending without actually sending")
    
    args = parser.parse_args()
    
    try:
        messenger = AgentMessenger()
        
        # Validate target agent
        if not messenger.validate_coordinates(args.target_agent):
            logger.error(f"❌ Invalid target agent: {args.target_agent}")
            logger.info("Available agents:")
            for agent in messenger.get_available_agents():
                logger.info(f"  - {agent}")
            return 1
            
        # Send message
        success = messenger.send_message(args.target_agent, args.message, args.dry_run)
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 