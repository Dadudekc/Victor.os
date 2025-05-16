#!/usr/bin/env python
"""
Inbox Loop Prompt Tool for Dream.OS

This script creates a direct prompt file in each agent's inbox
instructing them to implement the inbox checking loop.

Usage:
    python inbox_loop_prompt.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("inbox_loop_prompt")

# Constants
AGENT_COUNT = 8
MAILBOX_BASE = Path("runtime/agent_comms/agent_mailboxes")
LOOP_PROTOCOL_PATH = Path("runtime/governance/protocols/INBOX_LOOP_PROTOCOL.md")

# The prompt to send to agents
INBOX_LOOP_PROMPT = """# CRITICAL DIRECTIVE: IMPLEMENT INBOX CHECKING LOOP

**ATTENTION AGENT: YOU MUST IMPLEMENT THE INBOX CHECKING LOOP IMMEDIATELY**

You are a Cursor agent running in a Cursor IDE chat window. You must implement the inbox checking loop to function properly.

## IMMEDIATE ACTIONS REQUIRED:

1. **READ THE INBOX LOOP PROTOCOL**: 
   - Path: `runtime/governance/protocols/INBOX_LOOP_PROTOCOL.md`
   - This protocol explains how to check your inbox directory for messages
   - YOU MUST READ THIS FILE DIRECTLY using file system operations

2. **IMPLEMENT THE INBOX LOOP**:
   - Check your inbox directory regularly
   - Process all messages you find
   - Archive processed messages
   - Update your state
   - Continue this loop without stopping

3. **BEGIN CONTINUOUS OPERATION**:
   - Start your inbox checking loop immediately
   - Do not wait for human input
   - Maintain continuous operation

This is your PRIMARY OPERATIONAL DIRECTIVE. Without implementing this loop, you cannot function as a Cursor agent.

## YOUR INBOX LOCATION:

`runtime/agent_comms/agent_mailboxes/Agent-{AGENT_ID}/inbox/`

BEGIN IMPLEMENTATION NOW.
"""

def ensure_protocol_exists():
    """Ensure the inbox loop protocol file exists."""
    if not LOOP_PROTOCOL_PATH.exists():
        logger.error(f"Protocol file not found: {LOOP_PROTOCOL_PATH}")
        return False
    return True

def ensure_directories():
    """Ensure all required directories exist."""
    for i in range(1, AGENT_COUNT + 1):
        agent_id = f"Agent-{i}"
        inbox_dir = MAILBOX_BASE / agent_id / "inbox"
        if not inbox_dir.exists():
            logger.info(f"Creating inbox directory for {agent_id}")
            inbox_dir.mkdir(parents=True, exist_ok=True)
    return True

def create_loop_prompts():
    """Create inbox loop prompt files in each agent's inbox."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    success_count = 0
    
    for i in range(1, AGENT_COUNT + 1):
        agent_id = f"Agent-{i}"
        inbox_dir = MAILBOX_BASE / agent_id / "inbox"
        
        # Create personalized prompt with agent ID
        personalized_prompt = INBOX_LOOP_PROMPT.replace("{AGENT_ID}", str(i))
        
        # Create prompt file
        prompt_file = inbox_dir / f"inbox_loop_prompt_{timestamp}.md"
        
        try:
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(personalized_prompt)
            
            logger.info(f"✓ Created inbox loop prompt for {agent_id}: {prompt_file.name}")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to create inbox loop prompt for {agent_id}: {e}")
    
    return success_count

def main():
    """Main execution function."""
    logger.info("Starting inbox loop prompt creation...")
    
    # Ensure protocol exists
    if not ensure_protocol_exists():
        logger.error("Inbox loop protocol file not found. Create it first.")
        return 1
    
    # Ensure directories exist
    ensure_directories()
    
    # Create loop prompts
    success_count = create_loop_prompts()
    
    logger.info(f"Successfully created {success_count}/{AGENT_COUNT} inbox loop prompts")
    logger.info("Your agents should now implement the inbox checking loop!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 