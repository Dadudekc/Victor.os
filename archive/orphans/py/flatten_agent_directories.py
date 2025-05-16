#!/usr/bin/env python3
"""
Script to flatten agent-agent directories into original agent directories.

This script will:
1. Identify all 'agent-Agent-X' directories 
2. Merge their contents into the corresponding 'Agent-X' directories
3. Remove the 'agent-Agent-X' directories after successful merging
"""

import logging
import os
import re
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('flatten_agents')

# Path configuration
MAILBOXES_DIR = Path('runtime/agent_comms/agent_mailboxes')
AGENT_PATTERN = re.compile(r'^agent-Agent-(\d+)$')

def merge_directories(source_dir, target_dir):
    """
    Merge contents from source directory to target directory.
    
    Args:
        source_dir: Path object to source directory
        target_dir: Path object to target directory
        
    Returns:
        tuple: (success, error_count)
    """
    if not source_dir.exists() or not source_dir.is_dir():
        logger.error(f"Source directory does not exist: {source_dir}")
        return False, 1
    
    if not target_dir.exists() or not target_dir.is_dir():
        logger.error(f"Target directory does not exist: {target_dir}")
        return False, 1
    
    error_count = 0
    
    # Process all items in the source directory
    for item in source_dir.iterdir():
        target_item = target_dir / item.name
        
        if item.is_file():
            if target_item.exists():
                # If file exists in target, create a uniquely named file
                base_name = item.stem
                extension = item.suffix
                counter = 1
                while target_item.exists():
                    new_name = f"{base_name}_merged_{counter}{extension}"
                    target_item = target_dir / new_name
                    counter += 1
                
            try:
                shutil.copy2(item, target_item)
                logger.info(f"Copied file: {item} -> {target_item}")
            except Exception as e:
                logger.error(f"Error copying file {item}: {e}")
                error_count += 1
        
        elif item.is_dir():
            # If directory doesn't exist in target, create it
            if not target_item.exists():
                target_item.mkdir(exist_ok=True)
                logger.info(f"Created directory: {target_item}")
            
            # Recursively merge the subdirectory
            _, sub_errors = merge_directories(item, target_item)
            error_count += sub_errors
    
    return True, error_count

def main():
    """Main function to flatten agent directories."""
    if not MAILBOXES_DIR.exists() or not MAILBOXES_DIR.is_dir():
        logger.error(f"Mailboxes directory not found: {MAILBOXES_DIR}")
        return
    
    # Get all agent-Agent directories
    agent_agent_dirs = []
    for item in MAILBOXES_DIR.iterdir():
        if item.is_dir():
            match = AGENT_PATTERN.match(item.name)
            if match:
                agent_num = match.group(1)
                target_dir = MAILBOXES_DIR / f"Agent-{agent_num}"
                
                if target_dir.exists() and target_dir.is_dir():
                    agent_agent_dirs.append((item, target_dir, agent_num))
                else:
                    logger.warning(f"Target agent directory not found: {target_dir}")
    
    logger.info(f"Found {len(agent_agent_dirs)} agent-Agent directories to process")
    
    # Process each agent-Agent directory
    total_errors = 0
    dirs_to_remove = []
    
    for source_dir, target_dir, agent_num in agent_agent_dirs:
        logger.info(f"Processing agent-Agent-{agent_num} -> Agent-{agent_num}")
        success, errors = merge_directories(source_dir, target_dir)
        total_errors += errors
        
        if success:
            dirs_to_remove.append(source_dir)
        else:
            logger.error(f"Failed to merge {source_dir} to {target_dir}")
    
    # Remove processed agent-Agent directories
    for dir_to_remove in dirs_to_remove:
        try:
            shutil.rmtree(dir_to_remove)
            logger.info(f"Removed directory: {dir_to_remove}")
        except Exception as e:
            logger.error(f"Error removing directory {dir_to_remove}: {e}")
            total_errors += 1
    
    logger.info(f"Flattening complete. Total errors: {total_errors}")
    logger.info(f"Successfully processed and removed {len(dirs_to_remove)} directories")

if __name__ == "__main__":
    main() 