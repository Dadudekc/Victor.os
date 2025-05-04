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

# from dreamos.core.orchestrator import Orchestrator # INCORRECT/STALE IMPORT
from dreamos.automation.execution.swarm_controller import SwarmController

# Use canonical AppConfig and setup_logging from dreamos.config
from dreamos.config import AppConfig, setup_logging

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
    """Initialize and run the main SwarmController."""
    config = ctx.obj["config"]
    try:
        # orchestrator = Orchestrator(config) # EDIT: Remove old instantiation
        # logger.info("Orchestrator initialized.") # EDIT: Remove old log
        # logger.info("Running Orchestrator... (Add main loop/task execution here)") # EDIT: Remove old log
        # # Example: await orchestrator.start() or await orchestrator.run_task(...)
        # # For now, just log and exit gracefully
        # await asyncio.sleep(1)  # Placeholder for actual run logic
        # logger.info("Orchestrator run complete (placeholder). Exiting.") # EDIT: Remove old log

        # {{ EDIT START: Instantiate and run SwarmController }}
        # TODO: Handle initial tasks loading if needed
        initial_tasks = []
        # Example: Load from a file or default tasks
        # initial_tasks_path = config.paths.project_root / "runtime/initial_tasks.json"
        # if initial_tasks_path.exists():
        #     try:
        #         with open(initial_tasks_path, "r") as f:
        #             initial_tasks = json.load(f)
        #         logger.info(f"Loaded {len(initial_tasks)} initial tasks.")
        #     except Exception as e:
        #         logger.warning(f"Failed to load initial tasks: {e}")

        controller = SwarmController(config=config)
        logger.info("SwarmController initialized.")
        # Note: controller.start() is blocking and contains the main loop internally
        # It also handles worker threads, so we don't need separate asyncio tasks here usually.
        # However, `start` itself is NOT async. Need to run it appropriately.
        # Running blocking `start` in executor to not block main CLI thread if needed,
        # OR just run it directly if CLI's purpose is just to launch the controller.
        # For simplicity, assume direct run blocks until shutdown.
        # If this needs to run in background, threading or asyncio.to_thread is needed.

        # Since SwarmController.start manages its own threads and loops,
        # we likely don't need `async def run(ctx)` unless other async setup is needed.
        # For now, keep async def but run start synchronously.
        # Consider refactoring `start` or how it's called if true async needed here.
        controller.start(initial_tasks=initial_tasks)
        # The start method blocks until shutdown is called or loop ends.
        logger.info("SwarmController start method returned (likely shutdown). Exiting.")
        # {{ EDIT END }}

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
