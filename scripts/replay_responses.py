#!/usr/bin/env python3
"""
Response Replay CLI Tool

Usage:
    # Replay all responses from Agent-3 since a given timestamp
    replay_responses.py --agent Agent-3 --since 2025-05-20T00:00:00Z

    # Replay a specific response by hash into Agent-5's inbox
    replay_responses.py --hash d30fad... --target Agent-5

    # Dry-run mode (show what would be replayed)
    replay_responses.py --agent Agent-6 --limit 5 --dry-run
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.append(str(src_path))

from dreamos.tools.agent_resume import AgentResume

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('replay_responses')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Replay historical agent responses")
    
    # Source options (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--agent', help="Source agent ID")
    source_group.add_argument('--hash', help="Specific response hash to replay")
    
    # Target options
    parser.add_argument('--target', help="Target agent ID (defaults to source agent if not specified)")
    
    # Time range options
    parser.add_argument('--since', help="Replay responses since timestamp (ISO format)")
    parser.add_argument('--until', help="Replay responses until timestamp (ISO format)")
    
    # Other options
    parser.add_argument('--limit', type=int, help="Limit number of responses to replay")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be replayed without making changes")
    parser.add_argument('--delay', type=float, default=0.0, help="Delay between replays in seconds")
    parser.add_argument('--status', action='store_true', help="Show replay status for target agent")
    
    return parser.parse_args()

def validate_timestamp(timestamp: str) -> bool:
    """Validate ISO format timestamp."""
    try:
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False

def main():
    """Main entry point."""
    try:
        args = parse_args()
        
        # Initialize agent resume manager
        agent_manager = AgentResume()
        
        # Handle status request
        if args.status:
            if not args.target:
                logger.error("--target required for status check")
                return 1
                
            status = agent_manager.replay_controller.get_replay_status(args.target)
            print("\nReplay Status:")
            print(f"Total Messages: {status['total_messages']}")
            print(f"Replayed Messages: {status['replayed_messages']}")
            if status.get('latest_replay'):
                print(f"Latest Replay: {status['latest_replay']}")
            return 0
            
        # Set target agent
        target_agent = args.target or args.agent
        if not target_agent:
            logger.error("Target agent required")
            return 1
            
        # Validate timestamps
        if args.since and not validate_timestamp(args.since):
            logger.error("Invalid --since timestamp format")
            return 1
        if args.until and not validate_timestamp(args.until):
            logger.error("Invalid --until timestamp format")
            return 1
            
        # Replay responses
        success = False
        if args.hash:
            # Replay specific response
            success = agent_manager.replay_controller.replay_by_hash(
                response_hash=args.hash,
                target_agent=target_agent,
                dry_run=args.dry_run
            )
        else:
            # Replay agent responses
            success = agent_manager.replay_controller.replay_by_agent(
                source_agent=args.agent,
                target_agent=target_agent,
                since=args.since,
                until=args.until,
                limit=args.limit,
                dry_run=args.dry_run,
                delay=args.delay
            )
            
        if success:
            logger.info("Replay completed successfully")
            return 0
        else:
            logger.error("Replay failed")
            return 1
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 