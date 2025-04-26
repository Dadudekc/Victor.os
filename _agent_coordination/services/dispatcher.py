from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class Dispatcher(ABC):
    """
    Service responsible for routing parsed action dictionaries to appropriate handlers or agents.
    """
    @abstractmethod
    async def route(
        self,
        action_dict: Dict[str, Any],
        **kwargs
    ) -> Optional[str]:
        """
        Routes the given action to its handler (e.g., save_file, execute_cursor_goal) via AgentBus or other mechanisms.

        Args:
            action_dict: Parsed action dictionary from ResponseInterpreter.
            **kwargs: Additional context such as instance_id, original_task_id, etc.

        Returns:
            A sub-task identifier string if the action yields a trackable sub-task, or None.
        """
        ... 
