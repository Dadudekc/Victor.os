"""
Degraded Operation Mode implementation for Dream.OS agents.

This module implements the Degraded Operation Mode pattern described in
docs/knowledge/patterns/degraded_operation_mode.md.
"""
import time
import logging
import threading
from enum import Enum
from typing import Dict, List, Callable, Optional, Any, Set

logger = logging.getLogger(__name__)

class ActionCategory(Enum):
    """Categories of alternative actions in degraded mode."""
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"
    DIAGNOSTICS = "diagnostics"
    TOOL_SELF_TEST = "tool_self_test"
    CLEANUP = "cleanup"
    PLANNING = "planning"


class AlternativeAction:
    """
    Represents an alternative action that can be taken in degraded operation mode.
    """
    
    def __init__(
        self,
        name: str,
        category: ActionCategory,
        action_fn: Callable,
        prerequisites: List[str] = None,
        description: str = ""
    ):
        """
        Initialize an alternative action.
        
        Args:
            name: Unique name for this action
            category: Category this action belongs to
            action_fn: Function to call to execute this action
            prerequisites: List of resource names required for this action
            description: Human-readable description of what this action does
        """
        self.name = name
        self.category = category
        self.action_fn = action_fn
        self.prerequisites = prerequisites or []
        self.description = description
        self.success = False
    
    def can_execute(self, available_resources: List[str]) -> bool:
        """
        Check if this action can be executed with available resources.
        
        Args:
            available_resources: List of available resource names
            
        Returns:
            True if all prerequisites are available, False otherwise
        """
        return all(prereq in available_resources for prereq in self.prerequisites)
    
    def execute(self, context: Dict[str, Any] = None) -> bool:
        """
        Execute this action.
        
        Args:
            context: Optional context dictionary
            
        Returns:
            True if action was successful, False otherwise
        """
        context = context or {}
        try:
            self.success = self.action_fn(context)
            return self.success
        except Exception as e:
            logger.error(f"Failed to execute action {self.name}: {str(e)}")
            self.success = False
            return False
    
    def was_successful(self) -> bool:
        """
        Check if the last execution of this action was successful.
        
        Returns:
            True if the last execution was successful, False otherwise
        """
        return self.success


class AlternativeActions:
    """
    Registry of alternative actions that can be used in degraded operation mode.
    """
    
    _registry: Dict[str, AlternativeAction] = {}
    _registry_lock = threading.RLock()
    
    @classmethod
    def register(cls, action: AlternativeAction) -> AlternativeAction:
        """
        Register an alternative action.
        
        Args:
            action: The action to register
            
        Returns:
            The registered action
        """
        with cls._registry_lock:
            cls._registry[action.name] = action
        return action
    
    @classmethod
    def get_action(cls, name: str) -> Optional[AlternativeAction]:
        """
        Get an action by name.
        
        Args:
            name: Name of the action
            
        Returns:
            The action or None if not found
        """
        with cls._registry_lock:
            return cls._registry.get(name)
    
    @classmethod
    def get_actions_by_category(cls, category: ActionCategory) -> List[AlternativeAction]:
        """
        Get all actions in a category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of actions in that category
        """
        with cls._registry_lock:
            return [
                action for action in cls._registry.values()
                if action.category == category
            ]
    
    @classmethod
    def get_all_actions(cls) -> List[AlternativeAction]:
        """
        Get all registered actions.
        
        Returns:
            List of all registered actions
        """
        with cls._registry_lock:
            return list(cls._registry.values())


class DegradedOperationMode:
    """
    Context manager for operating in degraded mode.
    
    This implements the Degraded Operation Mode pattern, allowing agents to continue
    functioning in a limited capacity when normal operations are blocked or impaired.
    
    Usage:
        with DegradedOperationMode() as degraded:
            for action in degraded.get_alternative_actions():
                try:
                    action.execute()
                except Exception as e:
                    logger.error(f"Failed to execute {action.name}: {str(e)}")
    """
    
    def __init__(
        self,
        reason: str = "Unspecified failure",
        available_resources: List[str] = None,
        max_degraded_time: int = 3600  # 1 hour
    ):
        """
        Initialize degraded operation mode.
        
        Args:
            reason: Reason for entering degraded mode
            available_resources: List of resource names that are still available
            max_degraded_time: Maximum time in seconds to stay in degraded mode
        """
        self.reason = reason
        self.available_resources = available_resources or []
        self.max_degraded_time = max_degraded_time
        
        self.start_time = None
        self.attempted_actions: Set[str] = set()
        self.successful_actions: Set[str] = set()
        self.telemetry: Dict[str, Any] = {
            "actions_attempted": 0,
            "actions_succeeded": 0,
            "actions_failed": 0,
            "categories_attempted": set(),
        }
    
    def __enter__(self):
        """
        Enter degraded operation mode.
        
        Returns:
            self
        """
        self.start_time = time.time()
        logger.warning(f"Entering degraded operation mode: {self.reason}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit degraded operation mode.
        
        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        duration = time.time() - self.start_time
        logger.info(
            f"Exiting degraded mode after {duration:.1f}s. "
            f"Attempted {self.telemetry['actions_attempted']} actions, "
            f"{self.telemetry['actions_succeeded']} succeeded."
        )
        return False  # Don't suppress exceptions
    
    def get_alternative_actions(self) -> List[AlternativeAction]:
        """
        Get prioritized list of alternative actions that can be performed.
        
        Returns:
            List of alternative actions, prioritized
        """
        # Get all registered actions
        all_actions = AlternativeActions.get_all_actions()
        
        # Filter out actions that can't be executed with available resources
        executable_actions = [
            action for action in all_actions
            if action.can_execute(self.available_resources)
        ]
        
        # Prioritize actions
        prioritized = self._prioritize_actions(executable_actions)
        
        return prioritized
    
    def record_action_attempt(self, action: AlternativeAction, success: bool):
        """
        Record that an action was attempted.
        
        Args:
            action: The action that was attempted
            success: Whether the attempt was successful
        """
        self.attempted_actions.add(action.name)
        self.telemetry["actions_attempted"] += 1
        self.telemetry["categories_attempted"].add(action.category.value)
        
        if success:
            self.successful_actions.add(action.name)
            self.telemetry["actions_succeeded"] += 1
        else:
            self.telemetry["actions_failed"] += 1
    
    def should_continue(self) -> bool:
        """
        Check if degraded mode should continue.
        
        Returns:
            True if degraded mode should continue, False if it should exit
        """
        # Check if maximum time has been exceeded
        if time.time() - self.start_time > self.max_degraded_time:
            logger.warning(
                f"Maximum degraded mode time ({self.max_degraded_time}s) exceeded"
            )
            return False
        
        # Check if all possible actions have been attempted
        all_actions = AlternativeActions.get_all_actions()
        executable_actions = [
            action for action in all_actions
            if action.can_execute(self.available_resources)
        ]
        
        if all(action.name in self.attempted_actions for action in executable_actions):
            logger.info("All possible actions have been attempted")
            return False
        
        return True
    
    def get_available_resources(self) -> List[str]:
        """
        Get list of available resources.
        
        Returns:
            List of available resource names
        """
        return self.available_resources
    
    def _prioritize_actions(self, actions: List[AlternativeAction]) -> List[AlternativeAction]:
        """
        Prioritize actions based on category and other factors.
        
        Args:
            actions: List of actions to prioritize
            
        Returns:
            Prioritized list of actions
        """
        # Define category priorities (highest to lowest)
        category_priority = {
            ActionCategory.DOCUMENTATION: 1,
            ActionCategory.DIAGNOSTICS: 2,
            ActionCategory.ANALYSIS: 3,
            ActionCategory.TOOL_SELF_TEST: 4,
            ActionCategory.CLEANUP: 5,
            ActionCategory.PLANNING: 6
        }
        
        # Sort by:
        # 1. Not previously attempted
        # 2. Category priority
        # 3. Number of prerequisites (fewer is better)
        return sorted(
            actions,
            key=lambda a: (
                a.name in self.attempted_actions,  # Not attempted first
                category_priority.get(a.category, 99),  # Then by category priority
                len(a.prerequisites)  # Then by fewer prerequisites
            )
        )


# Register some common alternative actions
def _register_common_actions():
    """Register common alternative actions that most agents can use."""
    
    def document_blocker(context):
        """Create documentation about the current blocker."""
        # Implementation would vary based on the agent
        logger.info("Creating documentation about current blocker")
        return True
    
    def run_diagnostics(context):
        """Run self-diagnostic routines."""
        # Implementation would vary based on the agent
        logger.info("Running self-diagnostics")
        return True
    
    def analyze_failures(context):
        """Analyze recent failure patterns."""
        # Implementation would vary based on the agent
        logger.info("Analyzing failure patterns")
        return True
    
    AlternativeActions.register(
        AlternativeAction(
            name="document_blocker",
            category=ActionCategory.DOCUMENTATION,
            action_fn=document_blocker,
            prerequisites=[],
            description="Create documentation about the current blocker"
        )
    )
    
    AlternativeActions.register(
        AlternativeAction(
            name="run_diagnostics",
            category=ActionCategory.DIAGNOSTICS,
            action_fn=run_diagnostics,
            prerequisites=[],
            description="Run self-diagnostic routines"
        )
    )
    
    AlternativeActions.register(
        AlternativeAction(
            name="analyze_failures",
            category=ActionCategory.ANALYSIS,
            action_fn=analyze_failures,
            prerequisites=[],
            description="Analyze recent failure patterns"
        )
    )

# Register common actions when module is imported
_register_common_actions() 