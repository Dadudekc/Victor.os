# Contents of src/dreamos/tools/base.py moved here
# import argparse # Removed unused import
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Minimal Placeholder for ToolParameter
class ToolParameter:
    def __init__(self, name: str, type: str, description: str, required: bool = False):
        self.name = name
        self.type = type
        self.description = description
        self.required = required

    def __repr__(self):
        return f"ToolParameter(name={self.name}, type={self.type}, required={self.required})"  # noqa: E501


# Minimal Placeholder for ToolContext
class ToolContext:
    def __init__(
        self, args: Dict[str, Any], execution_context: Optional[Dict[str, Any]] = None
    ):
        self.args = args
        # Provide access to results from previous steps if needed
        self.execution_context = execution_context or {}
        logger.debug(f"ToolContext created with args: {args}")

    def get_argument(self, name: str, default: Any = None) -> Any:
        """Helper to safely get an argument."""
        return self.args.get(name, default)


# Minimal Abstract Base Class for Tools
class BaseTool(ABC):
    name: str = "base_tool"
    description: str = "Base class for tools"
    parameters: List[ToolParameter] = []

    @abstractmethod
    async def execute(self, context: ToolContext) -> Any:
        """Executes the tool's logic. Asynchronous."""
        pass

    def __init__(self):
        logger.debug(f"Initializing tool: {self.name}")

    def __repr__(self):
        return f"<{self.__class__.__name__} name='{self.name}'>"


# Minimal Placeholder for BaseToolExecutor (needed for __init__.py)
class BaseToolExecutor(ABC):  # Often might inherit from BaseTool or be separate
    """Placeholder base class for a tool executor concept. Now async."""

    def __init__(self):
        logger.warning("Using placeholder BaseToolExecutor (async version).")

    @abstractmethod
    async def execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Executes a named tool with given arguments and context. Asynchronous."""
        pass


# Ensure classes are available for import
__all__ = ["ToolParameter", "ToolContext", "BaseTool", "BaseToolExecutor"]
