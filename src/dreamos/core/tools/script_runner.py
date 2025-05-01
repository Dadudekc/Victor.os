import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Use PROJECT_ROOT from core config instead
from ..config import PROJECT_ROOT
from ..errors import ToolError

logger = logging.getLogger(__name__)


class ScriptExecutionError(Exception):
    """Custom exception for script execution failures."""

    def __init__(self, message, return_code=None, stdout=None, stderr=None):
        super().__init__(message)
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr


def run_script(
    script_path_str: str,
    args: Optional[List[str]] = None,
    cwd: Optional[Path] = None,
    capture_output: bool = True,
) -> Tuple[int, str, str]:
    """Executes a Python script within the project context, handling environment.

    Attempts to use 'poetry run' first. If poetry is not found, it falls back
    to direct python execution, ensuring 'src' is in the PYTHONPATH for the subprocess.

    Args:
        script_path_str: Path to the script relative to the project root.
        args: Optional list of arguments to pass to the script.
        cwd: Optional working directory. Defaults to project root.
        capture_output: Whether to capture stdout/stderr (True) or let them print (False).

    Returns:
        Tuple[int, str, str]: return_code, stdout, stderr

    Raises:
        FileNotFoundError: If the script_path does not exist.
        ScriptExecutionError: If execution fails.
    """
    args = args or []
    try:
        project_root = PROJECT_ROOT
    except FileNotFoundError:
        logger.error(
            "Could not find project root. Cannot ensure correct script execution environment."
        )
        raise ScriptExecutionError("Project root not found")

    if cwd is None:
        cwd = project_root

    script_full_path = (project_root / script_path_str).resolve()
    if not script_full_path.is_file():
        raise FileNotFoundError(f"Script not found at: {script_full_path}")

    poetry_path = shutil.which("poetry")
    command: List[str] = []
    env = os.environ.copy()

    if poetry_path:
        logger.info(
            f"Found poetry at {poetry_path}. Attempting execution with 'poetry run'."
        )
        command = [poetry_path, "run", "python", str(script_full_path)] + args
        # Poetry should handle the environment/paths correctly
    else:
        logger.warning(
            "Poetry executable not found in PATH. Attempting direct Python execution."
        )
        python_exe = (
            sys.executable
        )  # Use the same python interpreter running this agent
        command = [python_exe, str(script_full_path)] + args

        # Modify PYTHONPATH for the subprocess to include the src directory
        src_path = str((project_root / "src").resolve())
        existing_python_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{src_path}{os.pathsep}{existing_python_path}"
        logger.debug(f"Updated PYTHONPATH for subprocess: {env['PYTHONPATH']}")

    logger.info(f"Executing script: {' '.join(command)} in CWD: {cwd}")

    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=False,  # Don't raise CalledProcessError automatically
            env=env,
        )

        stdout = process.stdout or ""
        stderr = process.stderr or ""

        if process.returncode != 0:
            logger.error(
                f"Script execution failed with return code {process.returncode}."
            )
            logger.error(f"Stderr:\n{stderr}")
            # Optionally raise a more specific error here or let the caller check code
            # Uncomment to raise error on failure
            raise ScriptExecutionError(
                f"Script {script_path_str} failed with code {process.returncode}",
                return_code=process.returncode,
                stdout=stdout,
                stderr=stderr,
            )
        else:
            logger.info(
                f"Script {script_path_str} executed successfully (Code: {process.returncode})."
            )

        return process.returncode, stdout, stderr

    except FileNotFoundError as e:
        logger.error(
            f"Error executing command: {e}. Is '{command[0]}' installed and in PATH?",
            exc_info=True,
        )
        raise ScriptExecutionError(f"Execution command not found: {command[0]}") from e
    except Exception as e:
        logger.error(
            f"Unexpected error executing script {script_path_str}: {e}", exc_info=True
        )
        raise ScriptExecutionError(f"Unexpected error during script execution: {e}")


# Example Usage (for testing purposes)
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )  # Use DEBUG for testing
    # EDIT START: Use the newly created hello_world_script.py
    # test_script = "scripts/utility/test_runner.py" # ADJUST PATH AS NEEDED
    test_script = "scripts/utility/hello_world_script.py"
    test_args = ["--test-arg", "value123", "another_arg"]
    # EDIT END

    try:
        logger.info(
            f"--- Running test script: {test_script} with args: {test_args} ---"
        )
        # Force CWD to None to test default behavior (project root)
        return_code, stdout, stderr = run_script(test_script, args=test_args, cwd=None)
        logger.info(f"Return Code: {return_code}")
        logger.info(f"Stdout:\n{stdout}")
        if stderr:
            logger.warning(f"Stderr:\n{stderr}")

        if return_code == 0:
            logger.info("TEST SUCCEEDED")
        else:
            logger.error("TEST FAILED")

    except (FileNotFoundError, ScriptExecutionError) as e:
        logger.error(f"Test script execution failed: {e}")
        logger.error("TEST FAILED")

    # Example: Test script not found
    # try:
    #     logger.info("--- Running non-existent script test ---")
    #     run_script("scripts/utility/non_existent_script.py")
    # except FileNotFoundError as e:
    #     logger.info(f"Caught expected FileNotFoundError: {e}")
    # except ScriptExecutionError as e:
    #     logger.error(f"Caught unexpected ScriptExecutionError: {e}")


class ScriptRunner:
    @classmethod
    def _resolve_script_path(cls, script_name: str) -> Path:
        """Finds the absolute path of the script relative to the project root."""
        # Assume scripts are in a 'scripts/' directory at the project root
        script_path = PROJECT_ROOT / "scripts" / script_name
        # Allow for scripts potentially being in subdirs like scripts/utils
        if not script_path.exists():
            script_path = PROJECT_ROOT / "scripts" / "utils" / script_name

        if not script_path.exists() or not script_path.is_file():
            # Attempt to find it more dynamically if initial guesses fail?
            # This part might need refinement based on actual script locations.
            logger.warning(
                f"Script '{script_name}' not found at standard locations: {PROJECT_ROOT / 'scripts'} or {PROJECT_ROOT / 'scripts/utils'}. Attempting search."
            )
            # Simple search in common script dirs:
            common_script_dirs = ["scripts", "scripts/utils", "tools"]
            found = False
            for script_dir in common_script_dirs:
                potential_path = PROJECT_ROOT / script_dir / script_name
                if potential_path.exists() and potential_path.is_file():
                    script_path = potential_path
                    logger.info(f"Found script '{script_name}' at {script_path}")
                    found = True
                    break
            if not found:
                raise ToolError(
                    f"Script '{script_name}' not found in project root {PROJECT_ROOT}"
                )

        return script_path.resolve()

    def _run_script(
        self,
        script_name: str,
        args: Optional[List[str]] = None,
        cwd: Optional[Path] = None,
        capture_output: bool = True,
    ) -> Tuple[int, str, str]:
        """Runs a script with the given name and arguments.

        Args:
            script_name: The name of the script to run.
            args: Optional list of arguments to pass to the script.
            cwd: Optional working directory. Defaults to project root.
            capture_output: Whether to capture stdout/stderr (True) or let them print (False).

        Returns:
            Tuple[int, str, str]: return_code, stdout, stderr

        Raises:
            FileNotFoundError: If the script_path does not exist.
            ScriptExecutionError: If execution fails.
        """
        script_path = self._resolve_script_path(script_name)
        return run_script(
            script_path, args=args, cwd=cwd, capture_output=capture_output
        )
