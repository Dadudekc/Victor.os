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

# ───────────────────────── Backend imports ─────────────────────────
try:
    from dreamos.config import AppConfig, setup_logging, ConfigError
except ImportError as e:
    typer.secho(f"[Warning] core.config not available: {e}", fg=typer.colors.YELLOW)
    AppConfig = None  # type: ignore
    setup_logging = lambda cfg: None  # type: ignore
    class ConfigError(Exception): pass  # type: ignore

# ───────────────────────── Typer app setup ────────────────────────
app = typer.Typer(
    name="dream-os",
    help="Dream.OS Agent – Your AI-powered Operating System Assistant.",
    add_completion=False,
)

# ─────────────────────────── Helpers ─────────────────────────────
def configure_logging(config: AppConfig, verbose: bool) -> None:
    """
    Initialize Python logging based on config + --verbose flag.
    """
    level = logging.DEBUG if verbose else getattr(logging, config.logging.level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    setup_logging(config)
    logging.debug("Logging configured: level=%s", logging.getLevelName(level))


# ─────────────────────────── run command ──────────────────────────
@app.command()
def run(
    task: Optional[str] = typer.Option(
        None, "--task", "-t", help="Execute a single task (non-GUI mode)."
    ),
    config_path: Path = typer.Option(
        Path("config/config.yaml"), "--config", "-c", exists=True, help="Path to config file."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose (DEBUG) logging."
    ),
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
        typer.secho(f"[Error] Config load failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"[Error] Unexpected error loading config: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Configure logging
    configure_logging(config, verbose)
    logging.info("Configuration loaded from %s", config_path)

    mode = "task" if task else config.mode

    if mode == "gui":
        logging.info("Launching GUI (mode=gui)…")
        try:
            from gui.main import launch_gui
        except ImportError:
            typer.secho("GUI component not installed.", fg=typer.colors.YELLOW)
            raise typer.Exit(code=1)
        launch_gui(config)

    elif mode == "task":
        if not task:
            typer.secho("Error: `--task` is required for task mode.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        logging.info("Running one-off task: %s", task)
        try:
            from dreamos.tasks import run_task
            run_task(task, config)
        except Exception as e:
            logging.exception("Task execution failed")
            typer.secho(f"[Error] Task failed: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    else:
        typer.secho(f"Error: Unknown mode '{mode}'. Must be 'gui' or 'task'.", fg=typer.colors.RED)
        raise typer.Exit(code=1)


# ────────────────────── stats snapshot command ────────────────────
@app.command("stats")
def log_stats():
    """
    Write a snapshot of current system stats (via StatsLoggingHook).
    """
    try:
        from dreamos.hooks.stats_logger import StatsLoggingHook
        from dream_os.services.task_nexus import TaskNexus
    except ImportError as e:
        typer.secho(f"Stats logging unavailable: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    nexus = TaskNexus(task_file="runtime/task_list.json")
    hook = StatsLoggingHook(nexus)
    hook.log_snapshot()
    typer.secho("Stats snapshot saved.", fg=typer.colors.GREEN)


# ───────────────────── validate-config command ────────────────────
@app.command("validate-config")
def validate_config(
    config_path: Path = typer.Option(
        Path("config/config.yaml"), "--config", "-c", exists=True, help="Path to config file."
    )
):
    """
    Validate the structure and values of the Dream.OS config file.
    """
    try:
        config = AppConfig.load(str(config_path.resolve()))
        typer.secho("Configuration is valid.", fg=typer.colors.GREEN)
    except ConfigError as e:
        typer.secho(f"[Error] Invalid config: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"[Error] Unexpected error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


# ───────────────────────── version command ─────────────────────────
@app.command()
def version():
    """Show Dream.OS version."""
    try:
        from dreamos.version import __version__
        typer.echo(__version__)
    except ImportError:
        typer.echo("Version info unavailable")


# ─────────────────────────── entrypoint ───────────────────────────
if __name__ == "__main__":
    print("Starting Dream.OS CLI...")
    app()

