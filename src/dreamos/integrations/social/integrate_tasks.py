#!/usr/bin/env python3
"""
Dream.OS Social Media Task Integration Script

This script integrates social media lead tasks into the Dream.OS task management system.
It runs the task integration cycle to:
1. Scan for newly created social media lead tasks
2. Add them to the future_tasks.json file
3. Optionally assign them to a specific agent

Usage:
  python integrate_tasks.py [--agent AGENT_ID]
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports when run as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from dreamos.integrations.social.task_integration import integrate_social_tasks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dreamos.integrations.social.integrate_tasks")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Integrate social media lead tasks into the Dream.OS task system"
    )
    
    parser.add_argument(
        "--agent", "-a",
        help="Agent ID to assign tasks to (e.g., cursor_6)"
    )
    
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Watch for new tasks (run in a loop)"
    )
    
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=300,
        help="Interval in seconds between watch cycles (default: 300)"
    )
    
    args = parser.parse_args()
    
    agent_id = args.agent
    
    # Check environment variable if agent ID not provided
    if not agent_id:
        agent_id = os.environ.get("DREAMOS_LEAD_AGENT_ID")
        if agent_id:
            logger.info(f"Using agent ID from environment: {agent_id}")
    
    # Get default agent from task board if available
    if not agent_id:
        # Attempt to find an idle agent
        task_board_path = Path("runtime/task_board.json")
        if task_board_path.exists():
            try:
                import json
                with open(task_board_path, 'r') as f:
                    task_board = json.load(f)
                
                # Look for an idle agent
                for cursor_id, cursor_data in task_board.get("cursor_agents", {}).items():
                    if cursor_data.get("status") == "IDLE":
                        agent_id = cursor_id
                        logger.info(f"Found idle agent: {agent_id}")
                        break
            except Exception as e:
                logger.error(f"Error reading task board: {e}")
    
    # Run in watch mode if requested
    if args.watch:
        import time
        logger.info(f"Watching for new social media tasks every {args.interval} seconds")
        
        try:
            while True:
                task_count = integrate_social_tasks(agent_id)
                if task_count > 0:
                    logger.info(f"Processed {task_count} social media lead tasks")
                else:
                    logger.info("No new tasks found")
                
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Watch mode stopped by user")
            return 0
    else:
        # Run once
        task_count = integrate_social_tasks(agent_id)
        logger.info(f"Processed {task_count} social media lead tasks")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 