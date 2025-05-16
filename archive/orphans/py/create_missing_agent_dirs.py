#!/usr/bin/env python3
"""
Script to create missing directories in Agent mailboxes.

This script ensures all Agent directories have the expected structure:
- inbox
- outbox
- processed
- state
- workspace
"""

import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('create_missing_agent_dirs')

# Path configuration
MAILBOXES_DIR = Path('runtime/agent_comms/agent_mailboxes')
EXPECTED_DIRS = ['inbox', 'outbox', 'processed', 'state', 'workspace']

def create_missing_directories():
    """Create missing directories in Agent mailboxes."""
    agent_dirs = [d for d in MAILBOXES_DIR.iterdir() if d.is_dir() and d.name.startswith('Agent-')]
    
    if not agent_dirs:
        logger.error("No Agent directories found")
        return False
    
    logger.info(f"Found {len(agent_dirs)} Agent directories")
    
    for agent_dir in agent_dirs:
        for expected_dir in EXPECTED_DIRS:
            dir_path = agent_dir / expected_dir
            if not dir_path.exists():
                logger.info(f"Creating missing directory: {dir_path}")
                dir_path.mkdir(exist_ok=True)
    
    logger.info("✅ All missing directories created")
    return True

def main():
    """Main function to create missing directories."""
    logger.info("Starting creation of missing directories in Agent mailboxes")
    
    if create_missing_directories():
        logger.info("✅ All Agent directories now have the expected structure")
        return 0
    else:
        logger.error("❌ Failed to create missing directories")
        return 1

if __name__ == "__main__":
    exit(main()) 