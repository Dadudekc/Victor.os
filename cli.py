import typer
import logging
from typing import Optional
import sys
from pathlib import Path

# Assuming main application logic will be refactored into functions
# We'll import them once main.py is updated.
# from main import launch_gui, run_task_mode # Placeholder imports

# Import config loading and logging setup
try:
    from core.config import AppConfig, setup_logging, ConfigError
except ImportError as e:
    # In case core.config isn't available at import-time, define fallbacks
    logging.getLogger(__name__).warning(f"core.config import failed: {e}. Using dummy stubs.")
    class ConfigError(Exception):
        pass
    AppConfig = None
    def setup_logging(config):
        pass


app = typer.Typer(
    name="dream-os",
    help="Dream.OS Agent - Your AI-powered Operating System Assistant.",
    add_completion=False
)

logger = logging.getLogger(__name__)

@app.command()
def run(
    task: Optional[str] = typer.Option(
        None, 
        "--task", 
        "-t", 
        help="Specify the task description to run in non-GUI mode. Overrides config mode."
    ),
    config_file: Path = typer.Option(
        "config.yaml", 
        "--config", 
        "-c", 
        help="Path to the configuration YAML file.",
        exists=True, # Ensure config file exists
        dir_okay=False,
        readable=True,
    ),
    # Add more options as needed, e.g., to override specific config values
    # log_level: Optional[str] = typer.Option(None, "--log-level", help="Override log level (e.g., DEBUG, INFO).")
):
    """
    Runs the Dream.OS agent. 
    
    By default, it uses the mode specified in the config file.
    Use --task to run in task execution mode directly.
    """
    config: Optional[AppConfig] = None
    try:
        # --- 1. Load Configuration ---
        print(f"Loading configuration from: {config_file.resolve()}") # Early feedback
        config = AppConfig.load(str(config_file.resolve()))
        print("Configuration loaded successfully.")

        # --- 2. Setup Logging ---
        # Note: Logging setup uses the config, so errors before this point might not be logged to file
        setup_logging(config)
        logger.info(f"Logging setup complete. Level: {config.logging.level}, File: {config.logging.log_file}")
        logger.info(f"Resolved Paths Config: {config.paths.dict()}")


        # --- 3. Determine Run Mode ---
        run_mode = config.mode
        if task:
            logger.info(f"Task provided via CLI ('{task}'). Forcing task execution mode.")
            run_mode = "task"
        else:
            logger.info(f"Using run mode from config file: '{run_mode}'")

        # --- 4. Execute Logic ---
        if run_mode == "gui":
            logger.info("Launching GUI mode...")
            # Placeholder: Replace with actual call after main.py refactor
            # launch_gui(config) 
            print("GUI mode selected (actual launch pending main.py refactor).")
            logger.warning("GUI launch function not yet integrated.") 
        elif run_mode == "task":
            if not task:
                # If mode is 'task' in config but no task given via CLI
                logger.error("Running in 'task' mode but no task description provided. Use the --task option.")
                print("Error: Task mode requires a task description. Use --task 'Your task description'.")
                raise typer.Exit(code=1)
            
            logger.info(f"Starting task execution mode for task: '{task}'")
            # Placeholder: Replace with actual call after main.py refactor
            # run_task_mode(config, task) 
            print(f"Task mode selected for task: '{task}' (actual execution pending main.py refactor).")
            logger.warning("Task execution function not yet integrated.")
        else:
            logger.error(f"Invalid run mode specified in config: '{run_mode}'. Must be 'gui' or 'task'.")
            print(f"Error: Invalid mode '{run_mode}' in config file.")
            raise typer.Exit(code=1)

    except ConfigError as e:
        # Specific handling for config loading/validation errors
        logging.exception("Configuration error occurred.") # Log the full traceback if logging is setup
        print(f"\nConfiguration Error: {e}")
        print(f"Please check your configuration file: {config_file}")
        raise typer.Exit(code=1)
    except FileNotFoundError as e:
        # Handle case where config file *itself* isn't found by AppConfig.load (though Typer should catch this)
        logging.exception(f"Configuration file not found.")
        print(f"\nError: Configuration file not found at '{config_file}'. {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        # Catch-all for other unexpected errors during initialization
        logger.exception("An unexpected error occurred during application startup.")
        print(f"\nAn unexpected error occurred: {e}")
        raise typer.Exit(code=1)

    logger.info("Application finished.") # Or should exit within the called functions?

@app.command()
def log_stats():
    """Manually trigger a stats snapshot."""
    try:
        from core.hooks.stats_logger import StatsLoggingHook
        from dream_mode.task_nexus.task_nexus import TaskNexus
    except ImportError as e:
        print(f"Failed to import stats logging components: {e}")
        raise typer.Exit(code=1)

    # Initialize TaskNexus and StatsLoggingHook
    nexus = TaskNexus(task_file="runtime/task_list.json")
    hook = StatsLoggingHook(nexus)
    hook.log_snapshot()
    print("✅ Stats snapshot written.")

# Add other commands if needed, e.g., config validation, tool listing
# @app.command()
# def validate_config(
#     config_file: Path = typer.Option("config.yaml", "-c", help="Path to config file.", exists=True, readable=True)
# ):
#     """Validates the configuration file structure and values."""
#     try:
#         AppConfig.load(str(config_file.resolve()))
#         print(f"✅ Configuration file '{config_file}' is valid.")
#     except ConfigError as e:
#         print(f"❌ Configuration Error in '{config_file}':\n{e}")
#         raise typer.Exit(code=1)
#     except Exception as e:
#         print(f"❌ An unexpected error occurred during validation: {e}")
#         raise typer.Exit(code=1)

if __name__ == "__main__":
    # Setup minimal logging JUST for CLI argument parsing issues, before full config is loaded
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s') 
    print("Starting Dream.OS CLI...") # Add print statement for visibility
    app() 