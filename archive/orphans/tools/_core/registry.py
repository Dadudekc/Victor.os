import logging
from typing import Dict, List, Optional

# Import BaseTool for type hinting
from .base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Minimal placeholder for ToolRegistry to resolve import errors."""

    def __init__(self):
        logger.warning("Using placeholder ToolRegistry implementation!")
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool_instance: BaseTool):
        # Placeholder method
        tool_name = getattr(tool_instance, "name", None)
        if tool_name:
            if tool_name in self._tools:
                logger.warning(
                    f"Tool '{tool_name}' is already registered. Overwriting placeholder registration."
                )
            logger.info(f"Placeholder ToolRegistry: Registering tool: {tool_name}")
            self._tools[tool_name] = tool_instance
        else:
            logger.warning(
                f"Placeholder ToolRegistry: Cannot register tool without a 'name' attribute: {type(tool_instance)}"  # noqa: E501
            )

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        # Placeholder method
        tool = self._tools.get(tool_name)
        if tool:
            logger.debug(f"Placeholder ToolRegistry: Retrieved tool: {tool_name}")
        else:
            logger.warning(f"Placeholder ToolRegistry: Tool not found: {tool_name}")
        return tool

    def list_tools(self) -> List[str]:
        # Placeholder method
        logger.debug("Placeholder ToolRegistry: Listing tools.")
        return list(self._tools.keys())


# --- Singleton Pattern for the Placeholder Registry ---
_registry_instance: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Returns a singleton instance of the placeholder ToolRegistry."""
    global _registry_instance
    if _registry_instance is None:
        logger.info("Creating singleton instance of placeholder ToolRegistry.")
        _registry_instance = ToolRegistry()
    return _registry_instance


# Ensure the function is directly available for import
__all__ = ["ToolRegistry", "get_registry"]
