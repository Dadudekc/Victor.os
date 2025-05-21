"""
Cleanup Directive Broadcaster
Broadcasts the SWARM-CLEANUP-DIRECTIVE-ALPHA to all agents every 5 minutes.
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
import time
import os

# Configure logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scripts/cleanup_broadcast.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
running = True

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    running = False

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

CLEANUP_DIRECTIVE = {
    "id": "SWARM-CLEANUP-DIRECTIVE-ALPHA",
    "timestamp": datetime.utcnow().isoformat(),
    "sender": "System",
    "type": "cleanup_directive",
    "content": {
        "objective": "Pivot focus to immediate cleanup and reorganization. Prioritize removing deprecated code, tidying up documentation, and cleaning agent mailboxes.",
        "actions": [
            "Identify and delete obsolete files",
            "Consolidate scattered documents",
            "Validate agent directories",
            "Commit and log all changes"
        ],
        "status": "pending_agent_confirmation"
    },
    "priority": "high",
    "status": "unread"
}

async def ensure_mailbox_structure(inbox_data):
    """Ensure mailbox has proper structure."""
    if "messages" not in inbox_data:
        inbox_data["messages"] = []
    if "metadata" not in inbox_data:
        inbox_data["metadata"] = {
            "last_checked": datetime.utcnow().isoformat(),
            "message_count": 0,
            "unread_count": 0,
            "last_cleanup": datetime.utcnow().isoformat()
        }
    return inbox_data

async def broadcast_directive():
    """Broadcast cleanup directive to all agent mailboxes."""
    try:
        # Get all agent mailboxes
        mailboxes_dir = Path("runtime/agent_mailboxes")
        if not mailboxes_dir.exists():
            logger.error("Agent mailboxes directory not found")
            return

        # Update timestamp
        CLEANUP_DIRECTIVE["timestamp"] = datetime.utcnow().isoformat()

        # Broadcast to each agent
        for agent_dir in mailboxes_dir.iterdir():
            if not agent_dir.is_dir():
                continue

            inbox_path = agent_dir / "inbox.json"
            try:
                if not inbox_path.exists():
                    # Create inbox if it doesn't exist
                    inbox_data = await ensure_mailbox_structure({})
                else:
                    # Read existing inbox
                    with open(inbox_path) as f:
                        inbox_data = await ensure_mailbox_structure(json.load(f))

                # Add directive to messages
                inbox_data["messages"].append(CLEANUP_DIRECTIVE)
                
                # Update metadata
                inbox_data["metadata"].update({
                    "last_checked": datetime.utcnow().isoformat(),
                    "message_count": len(inbox_data["messages"]),
                    "unread_count": sum(1 for msg in inbox_data["messages"] if msg["status"] == "unread")
                })

                # Write updated inbox
                with open(inbox_path, 'w') as f:
                    json.dump(inbox_data, f, indent=4)

                logger.info(f"Broadcast cleanup directive to {agent_dir.name}")

            except Exception as e:
                logger.error(f"Error processing mailbox for {agent_dir.name}: {e}", exc_info=True)
                continue

    except Exception as e:
        logger.error(f"Error broadcasting directive: {e}", exc_info=True)

async def main():
    """Main loop to broadcast directive every 5 minutes."""
    logger.info(f"Starting cleanup directive broadcaster (PID: {os.getpid()})")
    
    while running:
        try:
            await broadcast_directive()
            logger.info("Waiting 5 minutes before next broadcast...")
            
            # Check running flag every second for 5 minutes
            for _ in range(300):
                if not running:
                    break
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            if running:
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    logger.info("Cleanup directive broadcaster shutting down gracefully...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1) 