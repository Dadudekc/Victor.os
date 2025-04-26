"""Tools for searching code using Ripgrep."""
import logging
import subprocess
import shutil
from typing import Dict, Any, Optional

from dreamos.tools.base import AgentTool

logger = logging.getLogger(__name__)

class GrepSearchTool(AgentTool):
    """Performs a search using Ripgrep (rg) command."""
    
    @property
    def name(self) -> str:
        return "grep_search"
        
    @property
    def description(self) -> str:
        return ("Performs a regex search using Ripgrep (rg) within a specified path. "
                "Input args: {'query': 'regex_pattern', 'path': 'search/path', 'options': '(optional) string of rg flags'}. "
                "Output: {'results': 'search output text'}. Requires 'rg' command to be installed and in PATH.")

    def _check_ripgrep_installed(self) -> bool:
        """Checks if ripgrep (rg) is installed and accessible."""
        if hasattr(self, '_rg_exists'): # Cache check result
            return self._rg_exists
        self._rg_exists = shutil.which("rg") is not None
        if not self._rg_exists:
            logger.error("Ripgrep command 'rg' not found in PATH. GrepSearchTool cannot function.")
        return self._rg_exists

    def execute(self, args: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        query = args.get("query")
        path = args.get("path", ".") # Default to current directory if path not specified
        options = args.get("options", "") # Optional rg flags (e.g., "-i -C 2" for case-insensitive, 2 context lines)
        
        if not query:
            raise ValueError(f"Tool '{self.name}' requires 'query' argument.")
            
        if not self._check_ripgrep_installed():
             raise EnvironmentError("Ripgrep command 'rg' not found in PATH.")

        logger.info(f"Executing '{self.name}' with query '{query}' in path '{path}' (Options: '{options}')")
        
        command = ["rg"] + options.split() + ["--", query, path]
        command_str = " ".join(command) # For logging
        logger.debug(f"Running command: {command_str}")

        try:
            # Use subprocess.run for simplicity, capture output
            # Set timeout to prevent hanging
            # Use text=True for automatic decoding
            process = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=False, # Don't raise exception on non-zero exit code (rg returns 1 if no matches)
                timeout=30 # Add a timeout (e.g., 30 seconds)
            )

            output = process.stdout
            error_output = process.stderr
            exit_code = process.returncode

            if exit_code > 1: # Exit code 0=matches, 1=no matches, >1=error
                logger.error(f"Ripgrep command failed with exit code {exit_code}. Error: {error_output}")
                raise RuntimeError(f"Ripgrep error (Exit Code {exit_code}): {error_output}")
            
            if exit_code == 1: # No matches found is not an error for the tool
                 logger.info(f"Ripgrep finished: No matches found for query '{query}' in '{path}'.")
                 output = "" # Return empty string for no matches
            else:
                 logger.info(f"Ripgrep search completed successfully.")

            result = {"results": output}
            self._log_execution(args, f"Found {len(output.splitlines())} lines.")
            return result
            
        except subprocess.TimeoutExpired:
            self._log_execution(args, "Ripgrep command timed out.")
            raise TimeoutError("Ripgrep command timed out after 30 seconds.")
        except Exception as e:
            self._log_execution(args, e)
            raise Exception(f"Error running Ripgrep search: {e}") from e 
