"""Tool Registry for managing and accessing AgentTools."""
import logging
from typing import Dict, Optional

from core.tools.base import AgentTool
# Import concrete tool implementations
from core.tools.functional.file_tools import FileReadTool, FileWriteTool
from core.tools.functional.search_tools import GrepSearchTool
from core.tools.functional.context_planner_tool import ContextPlannerTool
from core.tools.functional.utils_tools import LogMessageTool
# TODO: Implement and import LogMessageTool if used by planner fallback

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Manages a collection of available AgentTools."""

    def __init__(self):
        self._tools: Dict[str, AgentTool] = {}
        logger.info("ToolRegistry initialized.")

    def register(self, tool: AgentTool):
        """Registers a tool instance."""
        if not isinstance(tool, AgentTool):
            raise TypeError("Registered item must be an instance of AgentTool.")
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' is already registered. Overwriting.")
        self._tools[tool.name] = tool
        logger.debug(f"Tool '{tool.name}' registered.")

    def get_tool(self, tool_name: str) -> Optional[AgentTool]:
        """Retrieves a tool instance by its name."""
        tool = self._tools.get(tool_name)
        if not tool:
            logger.error(f"Tool '{tool_name}' not found in registry.")
        return tool

    def list_tools(self) -> Dict[str, str]:
        """Returns a dictionary of registered tool names and their descriptions."""
        return {name: tool.description for name, tool in self._tools.items()}

# --- Singleton Instance --- 
_global_registry = None

def get_registry() -> ToolRegistry:
    """Gets the global ToolRegistry instance, creating and populating it if needed."""
    global _global_registry
    if _global_registry is None:
        logger.info("Creating and populating global ToolRegistry...")
        _global_registry = ToolRegistry()
        _populate_default_tools(_global_registry)
    return _global_registry

def _populate_default_tools(registry: ToolRegistry):
    """Registers the default set of tools."""
    default_tools = [
        FileReadTool(),
        FileWriteTool(),
        GrepSearchTool(),
        ContextPlannerTool(),
        LogMessageTool()
    ]
    for tool in default_tools:
        registry.register(tool)
    logger.info(f"Registered {len(default_tools)} default tools.")

# Example Usage:
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Get the registry (this populates it the first time)
    registry = get_registry()
    
    print("\n--- Registered Tools ---")
    tool_list = registry.list_tools()
    for name, desc in tool_list.items():
        print(f"- {name}: {desc[:80]}...")
        
    print("\n--- Getting Tools ---")
    reader = registry.get_tool("read_file")
    planner = registry.get_tool("context_planner")
    non_existent = registry.get_tool("non_existent_tool")
    
    print(f"Reader found: {isinstance(reader, FileReadTool)}")
    print(f"Planner found: {isinstance(planner, ContextPlannerTool)}")
    print(f"Non-existent found: {non_existent is None}")

    # Example of re-getting the registry (should return the same instance)
    registry2 = get_registry()
    print(f"\nRegistry is singleton: {registry is registry2}") 