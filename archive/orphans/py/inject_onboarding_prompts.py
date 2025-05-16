#!/usr/bin/env python
"""
Onboarding Prompt Injection Tool for Dream.OS

This script reads onboarding prompt files from agent inboxes
and prepares them for delivery to the agents via the appropriate channels.

Usage:
    python inject_onboarding_prompts.py
"""

import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("prompt_injector")

# Constants
AGENT_COUNT = 8
MAILBOX_BASE = Path("runtime/agent_comms/agent_mailboxes")

def verify_environment():
    """Verify that directories exist and are accessible."""
    for i in range(1, AGENT_COUNT + 1):
        agent_id = f"Agent-{i}"
        inbox_dir = MAILBOX_BASE / agent_id / "inbox"
        if not inbox_dir.exists():
            logger.error(f"Inbox directory missing for {agent_id}: {inbox_dir}")
            inbox_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created inbox directory for {agent_id}")
    return True

def process_onboarding_prompts():
    """Process all onboarding prompts in agent inboxes."""
    processed_count = 0
    
    for i in range(1, AGENT_COUNT + 1):
        agent_id = f"Agent-{i}"
        
        # Log the start of processing for this agent
        logger.info(f"Processing onboarding for {agent_id}...")
        
        # Define paths
        inbox_dir = MAILBOX_BASE / agent_id / "inbox"
        onboarding_path = inbox_dir / "onboarding_prompt.md"
        
        # Check if onboarding prompt exists
        if not onboarding_path.exists():
            logger.warning(f"No onboarding prompt found for {agent_id}")
            continue
        
        # Read the prompt content
        prompt_content = onboarding_path.read_text(encoding="utf-8")
        
        # Create a timestamped version of the prompt
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_path = inbox_dir / f"onboarding_prompt_{timestamp}.md"
        
        # Copy the prompt to the timestamped file
        with open(timestamped_path, "w", encoding="utf-8") as f:
            f.write(prompt_content)
        
        logger.info(f"✓ Created timestamped onboarding prompt for {agent_id}: {timestamped_path.name}")
        processed_count += 1
    
    logger.info(f"Completed processing {processed_count} onboarding prompts")
    return processed_count

def main():
    """Main execution function."""
    logger.info("Starting onboarding prompt injection...")
    
    # Verify environment
    if not verify_environment():
        logger.error("Environment verification failed")
        return 1
    
    # Process prompts
    processed_count = process_onboarding_prompts()
    
    if processed_count > 0:
        logger.info(f"Successfully processed {processed_count} onboarding prompts")
        logger.info("Your agents are ready to resume autonomy!")
    else:
        logger.warning("No onboarding prompts were processed")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 