import typer
import logging
from typing import Optional
from pathlib import Path
import click
import sys

# ---------------------------------------------------
# Safe import of config and logging setup
# ---------------------------------------------------
try:
    from core.config import AppConfig, setup_logging, ConfigError
except ImportError as e:
    logging.basicConfig(level=logging.WARNING)
    logging.warning(f"[Dream.OS] core.config not available: {e}")
    AppConfig = None
    class ConfigError(Exception): pass
    def setup_logging(config): pass

# ---------------------------------------------------
# Custom Click Group to override default help
# ---------------------------------------------------
class DreamGroup(click.Group):
    def get_help(self, ctx):
        return 'dream-os\n' + super().get_help(ctx)

# ---------------------------------------------------
# Typer CLI App
# ---------------------------------------------------
app = typer.Typer(
    name="dream-os",
    help="Dream.OS Agent – Your AI-powered Operating System Assistant.",
    add_completion=False,
    cls=DreamGroup
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------
# Primary Run Command
# ---------------------------------------------------
@app.command()
def run(
    task: Optional[str] = typer.Option(None, "--task", "-t", help="Task description (for non-GUI mode)."),
    config_path: Path = typer.Option(
        Path("config.yaml"),
        "--config",
        "-c",
        help="Path to config file",
        exists=True
    )
):
    """
    Launch Dream.OS using a config file or direct task execution mode.
    """
    try:
        typer.echo(f"🔧 Loading config from: {config_path.resolve()}")
        config = AppConfig.load(str(config_path.resolve()))
        setup_logging(config)

        logger.info("✅ Configuration loaded.")
        logger.info(f"Run mode: {config.mode}, Logging Level: {config.logging.level}")

        # Determine execution mode
        run_mode = "task" if task else config.mode

        if run_mode == "gui":
            logger.info("🖥️ Launching GUI mode...")
            # TODO: hook to actual GUI launcher
            print("🔧 GUI launch stub (not yet connected to main.py)")
        elif run_mode == "task":
            if not task:
                logger.error("❌ Task mode requires --task 'description'")
                raise typer.Exit(code=1)
            logger.info(f"⚙ Executing task: {task}")
            # TODO: hook to task runner
            print(f"🔧 Task runner stub (task = '{task}')")
        else:
            logger.error(f"❌ Invalid mode: {run_mode}. Must be 'gui' or 'task'.")
            raise typer.Exit(code=1)

    except ConfigError as ce:
        logging.exception("❌ Config validation failed.")
        typer.echo(f"Configuration Error: {ce}")
        raise typer.Exit(code=1)
    except Exception as e:
        logging.exception("❌ Unhandled error during CLI launch.")
        typer.echo(f"Unexpected Error: {e}")
        raise typer.Exit(code=1)

# ---------------------------------------------------
# Stats Snapshot Command
# ---------------------------------------------------
@app.command()
def log_stats():
    """
    Logs the current system stats snapshot.
    """
    try:
        from core.hooks.stats_logger import StatsLoggingHook
        from dream_mode.task_nexus.task_nexus import TaskNexus
    except ImportError as e:
        typer.echo(f"Failed to import stats logging components: {e}")
        raise typer.Exit(code=1)

    nexus = TaskNexus(task_file="runtime/task_list.json")
    hook = StatsLoggingHook(nexus)
    hook.log_snapshot()
    typer.echo("📊 Stats snapshot written.")

# ---------------------------------------------------
# Future Extensions Placeholder
# ---------------------------------------------------
# @app.command()
# def validate_config(...):
#     """Validate config structure and values."""
#     ...

# ---------------------------------------------------
# Entry Point
# ---------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    print("🚀 Starting Dream.OS CLI...")
    app()
