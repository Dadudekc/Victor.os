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
import yaml

# Add project root to sys.path for absolute imports
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

# Now use core config path
# Other imports (relative paths need checking)
# from dreamos.agents import (
#     Agent1CodeReviewer,
#     Agent2InfraSurgeon,
#     Agent3DocArchitect,
#     Agent4TesterValidator,
#     Agent5PlannerCoordinator,
#     Agent6ObserverMonitor,
#     Agent7SecurityAuditor,
#     Agent8ResearchSynthesizer,
# )
from dreamos.automation.execution.swarm_controller import SwarmController
from dreamos.core.config import AppConfig, setup_logging

# {{ EDIT START: Explicitly remove dashboard import line }}
# from dreamos.dashboard.dashboard_app import run_dashboard # REMOVED BY AGENT-1
# {{ EDIT END }}
# from dreamos.tools.thea_relay_agent import TheaRelayAgent # Commented out, seems unused

# Use canonical AppConfig and setup_logging from dreamos.config
# {{ EDIT START: Remove duplicate config import }}
# from dreamos.config import AppConfig, setup_logging
# {{ EDIT END }}
# TODO (Masterpiece Review - Captain-Agent-8): Clean up commented-out imports
#      (Agents, dashboard, thea_relay_agent, duplicate config) if no longer needed.

# Initial basic logging config (will be overridden by setup_logging)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)  # Use __name__ for module-level logger
sys.stdout.flush()  # Flush after initial basicConfig

# Import other CLI command groups/functions
# from .agent_cmds import agent_app
# from .task_cmds import task_app
# from .config_cmds import config_app

# Import the new state command group
# TODO (Masterpiece Review - Captain-Agent-8): Clean up commented-out command group imports
#      (agent_app, task_app, config_app).

# --- Main App Initialization ---
app = click.Group(help="DreamOS Command Line Interface")

# Add other command groups
# app.add_typer(agent_app, name="agent")
# app.add_typer(task_app, name="task")
# app.add_typer(config_app, name="config")

# Add state commands (assuming state_app is defined in state_cmds.py)
# TODO: Verify integration pattern between Click and Typer if state_cmds uses Typer
# {{ EDIT START: Comment out problematic Typer integration }}
# app.add_typer(state_app, name="state")
# {{ EDIT END }}
# TODO (Masterpiece Review - Captain-Agent-8): Resolve commented-out Typer integration
#      for the 'state' command group. Either fix the integration or remove if unused.

# --- Main Execution Guard --- #
# (Keep the rest of the file as is)


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
        # {{ EDIT START: Update config loading }}
        # Instantiate AppConfig directly - uses pydantic-settings sources
        # (Init > Env > DotEnv > Default YAML)
        loaded_config = AppConfig()

        # If a specific --config file was passed via CLI, load it and override
        if config:
            logger.info(f"CLI --config specified: {config}. Attempting override.")
            if config.exists():
                try:
                    with open(config, "r") as f:
                        override_data = yaml.safe_load(f) or {}
                    # Update the initially loaded config with override data
                    # model_copy(update=...) creates a new instance with updated fields
                    loaded_config = loaded_config.model_copy(update=override_data)
                    logger.info(f"Successfully applied overrides from {config}")
                except Exception as e:
                    logger.error(
                        f"Failed to load or apply override config {config}: {e}"
                    )
                    # Decide if this is fatal or just a warning
                    sys.exit(1)  # Make it fatal for now
            else:
                logger.error(f"Specified --config file does not exist: {config}")
                sys.exit(1)

        # loaded_config = AppConfig(_config_file=config) # OLD loading
        # {{ EDIT END }}

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
def run(ctx):
    """Initialize and run the main SwarmController."""
    config = ctx.obj["config"]
    try:
        # {{ EDIT START: Instantiate and run SwarmController }}
        # Load initial tasks if needed (example logic commented out)
        initial_tasks = []
        # initial_tasks_path = config.paths.project_root / "runtime/initial_tasks.json"
        # ... loading logic ...

        logger.info("Attempting to initialize SwarmController...")
        controller = SwarmController(config=config)
        logger.info("SwarmController initialized.")

        # SwarmController.start() is blocking and manages its own threads/loops.
        # Run it directly as the CLI's primary purpose here is to launch it.
        logger.info("Attempting to start SwarmController...")
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
#     # We might need `asyncio.run(cli(standalone_mode=False))` or similar depending on Click version  # noqa: E501
#     pass # Click handles execution via the decorator typically
# TODO (Masterpiece Review - Captain-Agent-8): Remove the commented-out `main_async` function
#      if it's confirmed to be unnecessary with the Click implementation.

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
