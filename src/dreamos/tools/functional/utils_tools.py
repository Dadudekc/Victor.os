"""Basic utility tools."""
import logging
from typing import Dict, Any, Optional

from dreamos.tools.base import AgentTool

logger = logging.getLogger(__name__)

class LogMessageTool(AgentTool):
    """A simple tool that logs a message using the standard logger."""

    @property
    def name(self) -> str:
        return "log_message"

    @property
    def description(self) -> str:
        return ("Logs a message at the INFO level. Input args: {'message': 'text to log'}. "
                "Output: {'status': 'success'}. Useful for placeholders or debugging.")

    def execute(self, args: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        message = args.get("message")
        if message is None:
            raise ValueError(f"Tool '{self.name}' requires 'message' argument.")

        # Log the message using the tool's logger or a dedicated one
        logger.info(f"[LogMessageTool] {message}")
        result = {"status": "success"}
        # No need to call self._log_execution here as the action *is* logging
        return result 
