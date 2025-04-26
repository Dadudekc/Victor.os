"""Tools for interacting with the file system."""
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from dreamos.tools.base import AgentTool # Assuming base.py is in core/tools

logger = logging.getLogger(__name__)

# Determine workspace root (assuming this file is core/tools/functional/file_tools.py)
# Adjust the number of .parent calls if the file structure is different.
_WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
logger.info(f"Determined workspace root: {_WORKSPACE_ROOT}")

class FileReadTool(AgentTool):
    """Reads the content of a specified file."""
    
    @property
    def name(self) -> str:
        return "read_file"
        
    @property
    def description(self) -> str:
        return "Reads the entire content of a file specified by its path. Input args: {'filepath': 'path/to/file'}. Output: {'content': 'file content'}."

    def execute(self, args: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        filepath_str = args.get("filepath")
        if not filepath_str:
            raise ValueError(f"Tool '{self.name}' requires 'filepath' argument.")
            
        # Normalize path relative to workspace root
        try:
            filepath = (_WORKSPACE_ROOT / filepath_str).resolve()
            # Basic security check: ensure path stays within workspace
            if _WORKSPACE_ROOT not in filepath.parents and filepath != _WORKSPACE_ROOT:
                 raise SecurityException(f"Attempted file access outside workspace: {filepath_str}")
        except Exception as e:
             # Catch potential resolution errors or security issues
             raise ValueError(f"Invalid or insecure filepath: {filepath_str} - {e}") from e

        logger.info(f"Executing '{self.name}' on resolved path: {filepath}")
        
        try:
            if not filepath.is_file():
                 raise FileNotFoundError(f"File not found or is not a regular file: {filepath}")
                 
            # Consider adding size limit checks
            content = filepath.read_text(encoding='utf-8')
            result = {"content": content}
            self._log_execution(args, f"Read {len(content)} characters.")
            return result
        except Exception as e:
            self._log_execution(args, e)
            # Re-raise to be caught by executor
            raise Exception(f"Error reading file {filepath}: {e}") from e

class FileWriteTool(AgentTool):
    """Writes content to a specified file, overwriting if it exists."""
    
    @property
    def name(self) -> str:
        return "write_file"
        
    @property
    def description(self) -> str:
        return "Writes the given content to a file specified by its path. Creates directories if needed. Overwrites existing file. Input args: {'filepath': 'path/to/file', 'content': 'text content'}. Output: {'status': 'success'}."

    def execute(self, args: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        filepath_str = args.get("filepath")
        content = args.get("content")
        
        if not filepath_str:
            raise ValueError(f"Tool '{self.name}' requires 'filepath' argument.")
        if content is None: # Allow empty string, but not None
            raise ValueError(f"Tool '{self.name}' requires 'content' argument.")
            
        # Normalize path relative to workspace root
        try:
            filepath = (_WORKSPACE_ROOT / filepath_str).resolve()
            # Basic security check: ensure path stays within workspace
            if _WORKSPACE_ROOT not in filepath.parents and filepath != _WORKSPACE_ROOT:
                 raise SecurityException(f"Attempted file access outside workspace: {filepath_str}")
        except Exception as e:
             # Catch potential resolution errors or security issues
             raise ValueError(f"Invalid or insecure filepath: {filepath_str} - {e}") from e

        logger.info(f"Executing '{self.name}' to resolved path: {filepath}")
        
        try:
            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            filepath.write_text(content, encoding='utf-8')
            result = {"status": "success"}
            self._log_execution(args, result)
            return result
        except Exception as e:
            self._log_execution(args, e)
            # Re-raise to be caught by executor
            raise Exception(f"Error writing file {filepath}: {e}") from e 

# Basic Security Exception (can be refined)
class SecurityException(Exception):
    pass 
