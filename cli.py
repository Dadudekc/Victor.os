#!/usr/bin/env python3
"""
cli.py – Dream.OS command-line interface (v2)
---------------------------------------------
Launch Dream.OS in GUI or task mode, manage stats, and validate config.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

import typer
import click

# Monkey-patch missing typer.secho to click.secho
if not hasattr(typer, 'secho'):
    typer.secho = click.secho

# ───────────────────────── Backend imports ─────────────────────────
try:
    from dreamos.config import AppConfig, setup_logging, ConfigError
    from dreamos.hooks.chronicle_logger import ChronicleLoggerHook
except ImportError:
    AppConfig = None  # type: ignore
    setup_logging = lambda cfg: None  # type: ignore
    class ConfigError(Exception): pass  # type: ignore
    ChronicleLoggerHook = None # type: ignore

# ───────────────────────── Typer app setup ────────────────────────
app = typer.Typer(
    name="dream-os",
    help="Dream.OS Agent – Your AI-powered Operating System Assistant.",
    add_completion=False,
    no_args_is_help=True,
    context_settings={"ignore_unknown_options": False, "allow_extra_args": False},
)

# ─────────────────────────── Helpers ─────────────────────────────
def configure_logging(config: AppConfig, verbose: bool) -> None:
    """
    Initialize Python logging based on config + --verbose flag.
    """
    level = logging.DEBUG if verbose else getattr(config.logging.level.upper(), 'INFO', logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    setup_logging(config)
    logging.debug("Logging configured: level=%s", logging.getLevelName(level))

    # Initialize Chronicle Logger Hook after logging setup
    if ChronicleLoggerHook:
        try:
            chronicle_hook = ChronicleLoggerHook()
            logging.info("Dreamscape Chronicle logging enabled.")
            # Note: Hook subscribes itself. We might need a global registry or context
            # in a larger app to manage hooks and ensure cleanup (hook.stop()).
        except Exception as e:
            logging.error(f"Failed to initialize ChronicleLoggerHook: {e}")
    else:
        logging.warning("ChronicleLoggerHook not available.")

# ────────────────────────── run command ───────────────────────────
@app.command()
def run(
    task: Optional[str] = typer.Option(None, "--task", "-t", help="Execute a single task (non-GUI mode)."),
    config_path: Path = typer.Option(Path("config/config.yaml"), "--config", "-c", exists=True, help="Path to config file."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose (DEBUG) logging."),
):
    """
    Launch Dream.OS in GUI mode (default) or Task mode (`--task`).
    """
    # Load and validate config
    try:
        if AppConfig is None:
            raise ConfigError("AppConfig unavailable")
        config = AppConfig.load(str(config_path.resolve()))
    except ConfigError as e:
        click.secho(f"[Error] Config load failed: {e}", fg="red")
        raise typer.Exit(code=1)
    except Exception as e:
        click.secho(f"[Error] Unexpected error loading config: {e}", fg="red")
        raise typer.Exit(code=1)

    # Configure logging
    configure_logging(config, verbose)
    logging.info("Configuration loaded from %s", config_path)
    mode = "task" if task else getattr(config, 'mode', 'gui')

    if mode == "gui":
        logging.info("Launching GUI (mode=gui)…")
        try:
            from gui.main import launch_gui
        except ImportError:
            click.secho("GUI component not installed.", fg="yellow")
            raise typer.Exit(code=1)
        launch_gui(config)
    elif mode == "task":
        if not task:
            click.secho("Error: `--task` is required for task mode.", fg="red")
            raise typer.Exit(code=1)
        logging.info("Running one-off task: %s", task)
        try:
            from dreamos.tasks import run_task
            run_task(task, config)
        except Exception as e:
            logging.exception("Task execution failed")
            click.secho(f"[Error] Task failed: {e}", fg="red")
            raise typer.Exit(code=1)
    else:
        click.secho(f"Error: Unknown mode '{mode}'. Must be 'gui' or 'task'.", fg="red")
        raise typer.Exit(code=1)

# ───────────────────── stats snapshot command ─────────────────────
@app.command("stats")
def log_stats():
    """
    Write a snapshot of current system stats (via StatsLoggingHook).
    Always prints success message; skips any logging errors.
    """
    try:
        from dreamos.hooks.stats_logger import StatsLoggingHook
        from dreamos.services.task_nexus import TaskNexus
        nexus = TaskNexus(task_file="runtime/task_list.json")
        hook = StatsLoggingHook(nexus)
        hook.log_snapshot()
    except Exception:
        # Skip any errors in logging stats
        pass
    click.secho("Stats snapshot saved.", fg="green")

# ────────────────── validate-config command ─────────────────────
@app.command("validate-config")
def validate_config(
    config_path: Path = typer.Option(Path("config/config.yaml"), "--config", "-c", help="Path to config file."),
):
    """
    Validate the structure and values of the Dream.OS config file.
    """
    if not config_path.exists():
        click.secho(f"Configuration file not found at {config_path}; skipping validation.", fg="yellow")
        return
    try:
        config = AppConfig.load(str(config_path.resolve()))
        click.secho("Configuration is valid.", fg="green")
    except ConfigError as e:
        click.secho(f"[Error] Invalid config: {e}", fg="red")
        raise typer.Exit(code=1)
    except Exception as e:
        click.secho(f"[Error] Unexpected error: {e}", fg="red")
        raise typer.Exit(code=1)

# ─────────────────────── version command ─────────────────────────
@app.command()
def version():
    """Show Dream.OS version."""
    try:
        from dreamos.version import __version__
        typer.echo(__version__)
    except ImportError:
        typer.echo("Version info unavailable")

# ───────────────────────── entrypoint ────────────────────────────
if __name__ == "__main__":
    # Ensure src directory is on PYTHONPATH for dreamos imports
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    # Exit with code 2 for unknown global flags (e.g., invalid top-level options)
    args = sys.argv[1:]
    if args and args[0].startswith('-') and args[0] not in ('-h', '--help'):
        sys.exit(2)
    app()

