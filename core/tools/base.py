"""Base class and definitions for Agent Tools."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class AgentTool(ABC):
    """Abstract base class for all tools usable by agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does, its inputs, and outputs."""
        pass
        
    # Optional: Define input/output schemas (e.g., using Pydantic) for validation
    # @property
    # def input_schema(self) -> Optional[Type[BaseModel]]:
    #     return None
    # 
    # @property
    # def output_schema(self) -> Optional[Type[BaseModel]]:
    #     return None

    @abstractmethod
    def execute(self, args: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes the tool's logic.

        Args:
            args (Dict[str, Any]): Arguments required by the tool, fitting the input schema.
            context (Optional[Dict[str, Any]]): Optional shared context from the execution loop, 
                                               containing results from previous steps.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the tool execution. 
                            Should ideally fit the output schema. 
                            Commonly includes a 'result' key.
        Raises:
            Exception: If the tool encounters an unrecoverable error during execution.
        """
        pass

    def _log_execution(self, args: Dict[str, Any], result_or_error: Any):
        """Helper for logging tool execution."""
        if isinstance(result_or_error, Exception):
            logger.error(f"Tool '{self.name}' failed with args {args}. Error: {result_or_error}", exc_info=True)
        else:
            # Log result snippet for brevity if needed
            result_summary = str(result_or_error)
            if len(result_summary) > 150:
                result_summary = result_summary[:150] + "..."
            logger.info(f"Tool '{self.name}' executed with args {args}. Result: {result_summary}") 