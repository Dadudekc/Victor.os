#!/usr/bin/env python3
"""
_agent_coordination/bridge_adapters/cursor_bridge_adapter.py

Bridge adapter converting CursorGoal objects into TaskExecutionPlan for agent coordination.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

from _agent_coordination.state_machines.task_execution_plan import TaskExecutionPlan, TaskStep

logger = logging.getLogger("CursorBridgeAdapter")

@dataclass
class CursorGoal:
    """
    Defines a goal for Cursor execution via the bridge adapter.
    """
    goal_type: str
    task_id: str
    prompt_text: Optional[str] = None
    text_to_type: Optional[str] = None
    additional_params: Dict[str, Any] = None

class CursorBridgeAdapter:
    """
    Translates high-level CursorGoal objects into TaskExecutionPlan sequences
    that the task execution state machine can run.
    """
    def __init__(self) -> None:
        self.goal_builders = {
            "refactor": self._build_refactor_plan,
            "generate_tests": self._build_generate_tests_plan,
            "execute_prompt": self._build_execute_prompt_plan,
            "type_text": self._build_type_text_plan,
        }
        logger.info(
            "CursorBridgeAdapter initialized with %d goal builders.",
            len(self.goal_builders),
        )

    def translate_goal_to_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
        """
        Create a TaskExecutionPlan for the given CursorGoal.

        Raises:
            KeyError: if goal.goal_type is unsupported.
            ValueError: if required goal fields are missing.
        """
        logger.debug("Translating goal to plan: %s", goal)
        builder = self.goal_builders.get(goal.goal_type)
        if not builder:
            msg = f"Unsupported goal_type: '{goal.goal_type}'"
            logger.error(msg)
            raise KeyError(msg)
        return builder(goal)

    def _build_refactor_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
        """
        Placeholder for refactor plan generation.
        """
        raise NotImplementedError("Refactor plan builder is not implemented yet.")

    def _build_generate_tests_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
        """
        Placeholder for generate-tests plan generation.
        """
        raise NotImplementedError("Generate-tests plan builder is not implemented yet.")

    def _build_execute_prompt_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
        """
        Build a plan to inject and send a chat prompt in Cursor.
        """
        if not goal.prompt_text:
            msg = "'prompt_text' is required for execute_prompt goal."
            logger.error(msg)
            raise ValueError(msg)

        chat_input = goal.additional_params.get("chat_input_element", "chat_input")
        send_button = goal.additional_params.get("send_button_element", "send_button")
        response_area = goal.additional_params.get("response_output_element", "response_output_area")

        steps = [
            TaskStep(action="wait_for_element", element=chat_input, timeout=5),
            TaskStep(action="click", element=chat_input, required=True),
            TaskStep(action="type_text", params={"text": goal.prompt_text}, timeout=30, required=True),
            TaskStep(action="wait_for_element", element=send_button, timeout=5),
            TaskStep(action="click", element=send_button, required=True),
            TaskStep(action="wait_for_element", element=response_area, timeout=60, required=True),
        ]
        return TaskExecutionPlan(task_id=goal.task_id, steps=steps)

    def _build_type_text_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
        """
        Build a plan to type arbitrary text into a target element.
        """
        if not goal.text_to_type:
            msg = "'text_to_type' is required for type_text goal."
            logger.error(msg)
            raise ValueError(msg)

        target = goal.additional_params.get("target_element", "chat_input")
        steps = [
            TaskStep(action="wait_for_element", element=target, timeout=5),
            TaskStep(action="click", element=target, required=True),
            TaskStep(action="type_text", params={"text": goal.text_to_type}, timeout=30, required=True),
        ]
        return TaskExecutionPlan(task_id=goal.task_id, steps=steps)

# Stub for CursorBridgeAdapter and CursorGoal
class CursorBridgeAdapter:
    """Stub adapter to translate cursor goals into plans."""
    def translate_goal_to_plan(self, goal):
        return {}

class CursorGoal:
    """Stub goal object for cursor coordination tests."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v) 
