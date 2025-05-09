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
from dreamos.core.db.sqlite_adapter import SQLiteAdapter
from dreamos.core.coordination.agent_bus import AgentBus

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
    "cli_config_path", # Renamed to avoid conflict with AppConfig instance
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to the main configuration file (e.g., config.yaml)",
)
@click.pass_context
def cli(ctx, cli_config_path):
    """DreamOS Command Line Interface"""
    ctx.ensure_object(dict)
    try:
        # Instantiate AppConfig directly - uses pydantic-settings sources
        loaded_config = AppConfig()

        # If a specific --config file was passed via CLI, load it and override
        if cli_config_path:
            logger.info(f"CLI --config specified: {cli_config_path}. Attempting override.")
            # No need for exists check as click type=Path(exists=True) handles it
            try:
                with open(cli_config_path, "r") as f:
                    override_data = yaml.safe_load(f) or {}
                # Update the initially loaded config with override data
                loaded_config = loaded_config.model_copy(update=override_data)
                logger.info(f"Successfully applied overrides from {cli_config_path}")
            except Exception as e:
                logger.error(
                    f"Failed to load or apply override config {cli_config_path}: {e}"
                )
                sys.exit(1)

        setup_logging(loaded_config)
        ctx.obj["config"] = loaded_config
        logger.info("DreamOS CLI starting...")
        # Avoid logging potentially sensitive full config dump to INFO
        logger.debug(f"Loaded configuration: {loaded_config.model_dump_json(indent=2)}")
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
    config_from_ctx: AppConfig = ctx.obj["config"]
    try:
        # Load initial tasks if needed (example logic commented out)
        initial_tasks = []

        logger.info("Initializing core dependencies...")

        # Initialize SQLiteAdapter
        # Ensure the database path is correctly derived from config
        db_path_str = getattr(config_from_ctx.paths, "database_path", None)
        if not db_path_str:
            # Constructing a plausible default path if not in config
            db_path = config_from_ctx.paths.project_root / "runtime" / "db" / "dreamos.db"
            logger.warning(f"AppConfig.paths.database_path not set, using default: {db_path}")
        else:
            db_path = Path(db_path_str)
            if not db_path.is_absolute():
                db_path = config_from_ctx.paths.project_root / db_path

        db_path = db_path.resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using database path: {db_path}")
        sqlite_adapter = SQLiteAdapter(db_path=str(db_path))

        # Ensure DB schema exists (assuming sync method for simplicity here)
        try:
            # Replace with actual schema creation logic if needed, potentially async
            # e.g., if adapter has `create_schema_if_not_exists() -> None` (sync):
            # sqlite_adapter.create_schema_if_not_exists()
            # Or if it requires connection context (sync example):
            # with sqlite_adapter.connect_sync() as conn:
            #     sqlite_adapter.create_schema_sync(conn)
            # Or handle via asyncio.run if methods are async.
            # For now, assuming adapter handles schema implicitly or it's done elsewhere.
            logger.info("SQLiteAdapter initialized.")
        except Exception as db_err:
            logger.error(f"Failed during SQLiteAdapter setup: {db_err}", exc_info=True)
            sys.exit(1)

        # Initialize AgentBus (it's a singleton, so this gets the instance)
        agent_bus = AgentBus()
        logger.info("AgentBus instance obtained.")

        logger.info("Attempting to initialize SwarmController...")
        # Pass the required adapter and agent_bus
        controller = SwarmController(config=config_from_ctx, adapter=sqlite_adapter, agent_bus=agent_bus)
        logger.info("SwarmController initialized.")

        logger.info("Attempting to start SwarmController...")
        # SwarmController.start() is blocking and manages its own threads/loops.
        controller.start(initial_tasks=initial_tasks)

        logger.info("SwarmController start method returned (likely shutdown). Exiting.")

    except Exception as e:
        logger.exception(
            f"An unexpected error occurred during SwarmController execution: {e}"
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
        cli(standalone_mode=False) # Add standalone_mode=False for click>=8 compatibility
    except KeyboardInterrupt:
        logger.info("DreamOS CLI terminated by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"An unexpected error occurred during execution: {e}")
        sys.exit(1)
# EDIT END
