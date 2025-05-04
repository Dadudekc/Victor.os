# src/dreamos/cli/state_cmds.py
import logging
from pathlib import Path
from typing import Optional

import typer

# Assuming config loader and other necessary imports exist
from dreamos.core.config import AppConfig, load_config

# Import the new manager
from dreamos.core.state.snapshot_manager import SnapshotError, SnapshotManager

from ..core.config import setup_logging

# {{ EDIT END }}
# {{ EDIT START: Comment out missing state_explorer import }}
# from ..tools.state_explorer import display_full_state_report
# {{ EDIT END }}

logger = logging.getLogger(__name__)

state_app = typer.Typer(help="Commands for managing system state and snapshots.")


@state_app.command("snapshot")
def create_snapshot_cmd(
    reason: Optional[str] = typer.Option(
        "manual_cli", help="Reason for creating the snapshot."
    ),
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to the AppConfig YAML file."
    ),
):
    """Creates a system state snapshot (copies the database file)."""
    try:
        config: AppConfig = load_config(config_path)
        setup_logging(config.logging)

        db_path = Path(config.database.path)  # Get DB path from config
        snapshot_dir = Path(config.state.snapshot_dir)  # Get snapshot dir from config

        manager = SnapshotManager(db_path=db_path, snapshot_dir=snapshot_dir)
        typer.echo(f"Creating snapshot (Reason: {reason})...")
        snapshot_file = manager.create_snapshot(reason=reason)
        typer.echo(
            typer.style(
                f"Snapshot created successfully: {snapshot_file}", fg=typer.colors.GREEN
            )
        )

    except SnapshotError as e:
        typer.echo(typer.style(f"Snapshot Error: {e}", fg=typer.colors.RED), err=True)
        raise typer.Exit(code=1)
    except FileNotFoundError as e:
        typer.echo(
            typer.style(f"Configuration Error: {e}", fg=typer.colors.RED), err=True
        )
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(
            typer.style(f"An unexpected error occurred: {e}", fg=typer.colors.RED),
            err=True,
        )
        # Consider logging the full exception with logger
        logger.exception("Snapshot command failed unexpectedly.")
        raise typer.Exit(code=1)


@state_app.command("list-snapshots")
def list_snapshots_cmd(
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to the AppConfig YAML file."
    ),
):
    """Lists available system state snapshots."""
    try:
        config: AppConfig = load_config(config_path)
        # Logging setup might not be needed just to list
        # setup_logging(config.logging)

        db_path = Path(config.database.path)
        snapshot_dir = Path(config.state.snapshot_dir)

        manager = SnapshotManager(db_path=db_path, snapshot_dir=snapshot_dir)
        snapshots = manager.list_snapshots()

        if not snapshots:
            typer.echo("No snapshots found.")
            return

        typer.echo("Available Snapshots:")
        # Print as a table?
        for snap in snapshots:
            typer.echo(
                f" - {snap['filename']} ({snap['size_bytes'] / 1024:.1f} KB, {snap['created_at_local']})"
            )

    except SnapshotError as e:
        typer.echo(typer.style(f"Snapshot Error: {e}", fg=typer.colors.RED), err=True)
        raise typer.Exit(code=1)
    except FileNotFoundError as e:
        typer.echo(
            typer.style(f"Configuration Error: {e}", fg=typer.colors.RED), err=True
        )
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(
            typer.style(f"An unexpected error occurred: {e}", fg=typer.colors.RED),
            err=True,
        )
        logger.exception("List snapshots command failed unexpectedly.")
        raise typer.Exit(code=1)
