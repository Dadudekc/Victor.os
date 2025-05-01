#!/usr/bin/env python3
"""Dream.OS Main Entry Point"""

# EDIT END
import asyncio
import logging
import sys
from pathlib import Path

# EDIT START: Replace argparse with click
# import argparse
import click

# Use canonical AppConfig and setup_logging from dreamos.config
from dreamos.config import AppConfig, setup_logging
from dreamos.core.orchestrator import Orchestrator

# Initial basic logging config (will be overridden by setup_logging)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)  # Use __name__ for module-level logger
sys.stdout.flush()  # Flush after initial basicConfig


# EDIT START: Define click command group
@click.group()
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to the main configuration file (e.g., config.yaml)",
)
@click.pass_context
def cli(ctx, config):
    """DreamOS Command Line Interface"""
    ctx.ensure_object(dict)
    try:
        # Instantiate AppConfig directly, passing CLI arg if provided
        loaded_config = AppConfig(_config_file=config)
        setup_logging(loaded_config)
        ctx.obj["config"] = loaded_config
        logger.info("DreamOS CLI starting...")
        logger.info(f"Loaded configuration: {loaded_config.model_dump_json(indent=2)}")
    except FileNotFoundError as e:
        logger.error(f"Configuration file error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred during configuration loading: {e}"
        )
        sys.exit(1)


# Example subcommand - can be expanded
@cli.command()
@click.pass_context
async def run(ctx):
    """Initialize and run the main Orchestrator."""
    config = ctx.obj["config"]
    try:
        orchestrator = Orchestrator(config)
        logger.info("Orchestrator initialized.")
        logger.info("Running Orchestrator... (Add main loop/task execution here)")
        # Example: await orchestrator.start() or await orchestrator.run_task(...)
        # For now, just log and exit gracefully
        await asyncio.sleep(1)  # Placeholder for actual run logic
        logger.info("Orchestrator run complete (placeholder). Exiting.")

    except Exception as e:
        logger.exception(
            f"An unexpected error occurred during orchestrator execution: {e}"
        )
        sys.exit(1)


# EDIT END

# EDIT START: Update main entry point for click and async
# Removing unused main_async function as click handles async command invocation
# async def main_async():
#     # Click handles argument parsing directly
#     # We need to run the async command if specified
#     # This structure might need refinement based on how click async is best handled
#     # For now, assume click handles invoking the async `run` command
#     # The `cli()` function itself isn't async, but commands under it can be.
#     # We might need `asyncio.run(cli(standalone_mode=False))` or similar depending on Click version
#     pass # Click handles execution via the decorator typically

if __name__ == "__main__":
    # Ensure the event loop is correctly managed, especially on Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        # Let Click handle the command invocation
        cli()
    except KeyboardInterrupt:
        logger.info("DreamOS CLI terminated by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"An unexpected error occurred during execution: {e}")
        sys.exit(1)
# EDIT END
