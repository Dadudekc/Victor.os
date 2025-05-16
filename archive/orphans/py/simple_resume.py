#!/usr/bin/env python
"""
Simple Resume Tool for Dream.OS

This script creates a simple resume prompt file in each agent's inbox
to trigger their autonomous operation without requiring GUI interaction.

Usage:
    python simple_resume.py
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("simple_resume")

# Constants
AGENT_COUNT = 8
MAILBOX_BASE = Path("runtime/agent_comms/agent_mailboxes")
RESUME_PROMPT = """# RESUME AUTONOMY

**ATTENTION AGENT**: Your swarm is being rebooted. Resume autonomous operation immediately.

1. Check your inbox for the full onboarding prompt
2. Review all protocol documentation
3. Begin your continuous operation cycle
4. Update your devlog with your status
5. Execute your role-specific tasks

Remember: Continuous operation is your priority. Do not stop for human input.
"""

def ensure_directories():
    """Ensure all required directories exist."""
    for i in range(1, AGENT_COUNT + 1):
        agent_id = f"Agent-{i}"
        inbox_dir = MAILBOX_BASE / agent_id / "inbox"
        if not inbox_dir.exists():
            logger.info(f"Creating inbox directory for {agent_id}")
            inbox_dir.mkdir(parents=True, exist_ok=True)
    return True

def create_resume_prompts():
    """Create resume prompt files in each agent's inbox."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    success_count = 0
    
    for i in range(1, AGENT_COUNT + 1):
        agent_id = f"Agent-{i}"
        inbox_dir = MAILBOX_BASE / agent_id / "inbox"
        
        # Create resume prompt file
        resume_file = inbox_dir / f"resume_prompt_{timestamp}.md"
        
        try:
            with open(resume_file, "w", encoding="utf-8") as f:
                f.write(RESUME_PROMPT)
            
            logger.info(f"✓ Created resume prompt for {agent_id}: {resume_file.name}")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to create resume prompt for {agent_id}: {e}")
    
    return success_count

def main():
    """Main execution function."""
    logger.info("Starting simple resume prompt creation...")
    
    # Ensure directories exist
    ensure_directories()
    
    # Create resume prompts
    success_count = create_resume_prompts()
    
    logger.info(f"Successfully created {success_count}/{AGENT_COUNT} resume prompts")
    logger.info("Your agents are ready to resume autonomy!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 