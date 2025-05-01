"""Utilities for performing searches, e.g., using Ripgrep."""

import logging
import shutil
import subprocess
from typing import List, Optional

logger = logging.getLogger(__name__)


def is_ripgrep_installed() -> bool:
    """Checks if ripgrep (rg) is installed and accessible in the PATH."""
    return shutil.which("rg") is not None


def run_ripgrep_search(
    query: str,
    path: str = ".",
    rg_options: Optional[List[str]] = None,
    timeout: int = 30,
) -> str:
    """Runs a Ripgrep search and returns the raw stdout results.

    Args:
        query: The regex pattern to search for.
        path: The directory or file path to search within (defaults to current directory).
        rg_options: A list of additional Ripgrep command-line flags (e.g., ["-i", "-C", "2"]).
        timeout: Timeout in seconds for the subprocess call.

    Returns:
        The stdout from Ripgrep as a string. Empty string if no matches.

    Raises:
        EnvironmentError: If 'rg' command is not found.
        RuntimeError: If Ripgrep fails with an exit code > 1.
        TimeoutError: If the Ripgrep command times out.
        Exception: For other subprocess errors.
    """
    if not is_ripgrep_installed():
        raise EnvironmentError(
            "Ripgrep command 'rg' not found in PATH. Cannot perform search."
        )

    if rg_options is None:
        rg_options = []

    command = ["rg"] + rg_options + ["--", query, path]
    command_str = " ".join(command)  # For logging
    logger.info(f"Running Ripgrep: {command_str}")

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on non-zero exit code (rg returns 1 if no matches)
            timeout=timeout,
        )

        output = process.stdout
        error_output = process.stderr
        exit_code = process.returncode

        if exit_code > 1:  # Exit code 0=matches, 1=no matches, >1=error
            logger.error(
                f"Ripgrep command failed with exit code {exit_code}. Command: '{command_str}'. Error: {error_output}"
            )
            raise RuntimeError(f"Ripgrep error (Exit Code {exit_code}): {error_output}")

        if exit_code == 1:  # No matches found is not an error
            logger.info(
                f"Ripgrep finished: No matches found for query '{query}' in '{path}'."
            )
            return ""  # Return empty string for no matches
        else:
            logger.info(
                f"Ripgrep search completed successfully for query '{query}' in '{path}'."
            )
            return output

    except subprocess.TimeoutExpired:
        logger.error(
            f"Ripgrep command timed out after {timeout} seconds. Command: '{command_str}'"
        )
        raise TimeoutError(f"Ripgrep command timed out after {timeout} seconds.")
    except Exception as e:
        logger.error(
            f"Error running Ripgrep command '{command_str}': {e}", exc_info=True
        )
        raise Exception(f"Error running Ripgrep search: {e}") from e
