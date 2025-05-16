"""
Main entry point for Agent Bootstrap Runner
"""

import argparse
import asyncio
import logging
import sys

from .agent_loop import agent_loop
from .config import AgentConfig


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Dream.OS Agent Bootstrap Runner")
    parser.add_argument(
        "--agent", type=str, default="Agent-2", help="Agent ID (e.g. Agent-2)"
    )
    parser.add_argument("--no-delay", action="store_true", help="Skip startup delay")
    parser.add_argument(
        "--run-once", action="store_true", help="Run one cycle then exit"
    )
    parser.add_argument("--custom-prompt", type=str, help="Custom prompt text")
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )

    try:
        # Create agent config
        config = AgentConfig(
            agent_id=args.agent, startup_delay_sec=0 if args.no_delay else None
        )

        # Run agent loop
        await agent_loop(config, run_once=args.run_once)

    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
