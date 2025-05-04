"""Command-line interface for the safe_write_file utility."""

# EDIT START: Replace argparse with click
# import argparse
import logging
import os

# EDIT END
import sys
from pathlib import Path

import click

# --- Adjust sys.path to allow importing from src --- START
# This assumes the script is run from the project root (D:\\Dream.os)
# If run from elsewhere, this path adjustment might need modification.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (
    SCRIPT_DIR.parent.parent.parent
)  # src/dreamos/cli -> src/dreamos -> src -> .
SRC_PATH = SCRIPT_DIR.parent.parent  # src/dreamos/cli -> src/dreamos -> src
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
# --- Adjust sys.path --- END

try:
    # Now import the function from its location within src
    from dreamos.core.utils.safe_file_writer import SafeWriteError, safe_write_file
except ImportError as e:
    print(
        f"ERROR: Failed to import safe_write_file. Ensure src is in PYTHONPATH or script is run correctly. Details: {e}",  # noqa: E501
        file=sys.stderr,
    )
    sys.exit(1)

# --- Basic Logging Setup ---
# Note: Agents calling this might have their own logging context.
# This provides standalone logging if run directly.
log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level_str, logging.INFO),
    format="%(asctime)s - safe_writer_cli - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
# --- Logging Setup End ---


# EDIT START: Define click command
@click.command()
@click.option(
    "--target-file",
    required=True,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="The path to the file to write.",
)
@click.option(
    "--lock-timeout",
    type=int,
    default=10,
    show_default=True,
    help="Timeout in seconds for acquiring the file lock.",
)
@click.argument("content_input", type=click.File("r"), default=sys.stdin)
def safe_write_cli(target_file: Path, lock_timeout: int, content_input):
    """Safely write content (from stdin or file) to a target file atomically."""
    logger.info(f"Attempting safe write to: {target_file}")

    try:
        # Read content from input stream (stdin by default)
        content_to_write = content_input.read()
        logger.debug(f"Read {len(content_to_write)} bytes from input.")

        # Call the safe write function
        safe_write_file(
            target_file=target_file, content=content_to_write, lock_timeout=lock_timeout
        )

        logger.info(f"Successfully wrote content to {target_file}")
        click.echo(f"Success: Content written to {target_file}", err=False)
        # sys.exit(0) # Click handles exit code on success

    except (SafeWriteError, TypeError, ValueError) as e:
        logger.error(f"Failed to write to {target_file}: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        click.echo(f"Error: An unexpected error occurred: {e}", err=True)
        sys.exit(1)


# EDIT END

if __name__ == "__main__":
    # EDIT START: Invoke click command
    # main()
    safe_write_cli()
    # EDIT END
