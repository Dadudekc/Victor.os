#!/usr/bin/env python3
"""
Script to verify the agent mailbox directory structure after flattening.

This script checks:
1. All agent-Agent directories are gone
2. All Agent directories have the expected structure
3. All references to agent-Agent in files have been updated
"""

import json
import logging
import os
import re
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('verify_agent_mailboxes')

# Path configuration
MAILBOXES_DIR = Path('runtime/agent_comms/agent_mailboxes')
AGENT_PATTERN = re.compile(r'^agent-Agent-\d+$')
EXPECTED_DIRS = ['inbox', 'outbox', 'processed', 'state', 'workspace']

def verify_agent_directories():
    """Verify that all agent-Agent directories are gone and Agent directories have expected structure."""
    # Check that no agent-Agent directories exist
    agent_agent_dirs = [d for d in MAILBOXES_DIR.iterdir() if d.is_dir() and AGENT_PATTERN.match(d.name)]
    
    if agent_agent_dirs:
        logger.error(f"Found {len(agent_agent_dirs)} agent-Agent directories that should have been removed:")
        for d in agent_agent_dirs:
            logger.error(f"  - {d}")
        return False
    
    logger.info("✅ No agent-Agent directories found")
    
    # Check that Agent directories have expected structure
    agent_dirs = [d for d in MAILBOXES_DIR.iterdir() if d.is_dir() and d.name.startswith('Agent-')]
    
    if not agent_dirs:
        logger.error("No Agent directories found")
        return False
    
    logger.info(f"Found {len(agent_dirs)} Agent directories")
    
    all_valid = True
    for agent_dir in agent_dirs:
        missing_dirs = [d for d in EXPECTED_DIRS if not (agent_dir / d).exists()]
        if missing_dirs:
            logger.error(f"{agent_dir.name} is missing expected subdirectories: {', '.join(missing_dirs)}")
            all_valid = False
    
    if all_valid:
        logger.info("✅ All Agent directories have the expected structure")
    
    return all_valid

def verify_message_references():
    """Verify that all references to agent-Agent in message files have been updated."""
    agent_dirs = [d for d in MAILBOXES_DIR.iterdir() if d.is_dir() and d.name.startswith('Agent-')]
    
    all_valid = True
    for agent_dir in agent_dirs:
        inbox_dir = agent_dir / 'inbox'
        if not inbox_dir.exists():
            continue
        
        for msg_file in inbox_dir.glob('*.json'):
            try:
                with open(msg_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if 'agent-Agent' in content:
                    logger.error(f"Found reference to agent-Agent in {msg_file}")
                    all_valid = False
                    
                    # Check if it's in the checklist_location field
                    try:
                        data = json.loads(content)
                        if 'metadata' in data and 'checklist_location' in data['metadata']:
                            if 'agent-Agent' in data['metadata']['checklist_location']:
                                logger.error(f"  - Reference is in checklist_location: {data['metadata']['checklist_location']}")
                    except json.JSONDecodeError:
                        logger.error(f"  - Could not parse JSON in {msg_file}")
            except Exception as e:
                logger.error(f"Error processing {msg_file}: {e}")
                all_valid = False
    
    if all_valid:
        logger.info("✅ No references to agent-Agent found in message files")
    
    return all_valid

def verify_violation_references():
    """Verify that all references to agent-Agent in violation files have been updated."""
    agent_dirs = [d for d in MAILBOXES_DIR.iterdir() if d.is_dir() and d.name.startswith('Agent-')]
    
    all_valid = True
    for agent_dir in agent_dirs:
        violations_dir = agent_dir / 'violations'
        if not violations_dir.exists():
            continue
        
        for violation_file in violations_dir.glob('*.json'):
            try:
                with open(violation_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if 'agent-Agent' in content:
                    logger.error(f"Found reference to agent-Agent in {violation_file}")
                    all_valid = False
            except Exception as e:
                logger.error(f"Error processing {violation_file}: {e}")
                all_valid = False
    
    if all_valid:
        logger.info("✅ No references to agent-Agent found in violation files")
    
    return all_valid

def main():
    """Main function to run all verification checks."""
    logger.info("Starting verification of agent mailbox directory structure")
    
    dir_check = verify_agent_directories()
    msg_check = verify_message_references()
    violation_check = verify_violation_references()
    
    if dir_check and msg_check and violation_check:
        logger.info("✅ All checks passed! Agent mailbox directory structure is valid.")
        return 0
    else:
        logger.error("❌ Some checks failed. See errors above.")
        return 1

if __name__ == "__main__":
    exit(main()) 