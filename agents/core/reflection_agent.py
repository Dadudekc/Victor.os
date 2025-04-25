"""
An example agent responsible for reflection or self-analysis tasks.
"""

import logging
from typing import Dict, Any, List

# Assuming utils and agents directories are siblings under _agent_coordination
# Adjust the import path if the structure is different
# !! IMPORT PATHS WILL LIKELY NEED FIXING AFTER MOVE !!
from _agent_coordination.utils.agent_registry import register_agent # TODO: Fix import - should be from core.coordination? or a local registry?
from .base_agent import BaseAgent # TODO: Fix import - will be sibling
from core.voice_engine import VictorVoiceEngine # TODO: Fix import - Should be from root core?
from _agent_coordination.utils.emotion_detector import EmotionCueDetector # TODO: Fix import

logger = logging.getLogger(__name__)
# Configure logging basicConfig in a central place if running standalone
# logging.basicConfig(level=logging.INFO)

# @register_agent # TODO: Determine correct registry location/decorator
class ReflectionAgent(BaseAgent):
    """A concrete agent implementation focusing on reflection, using VictorVoiceEngine."""

    def __init__(self, agent_id: str, analysis_depth: int = 1, **kwargs):
        """Initializes the ReflectionAgent.

        Args:
            agent_id: The unique ID for this agent.
            analysis_depth: An example specific parameter for this agent.
            **kwargs: Additional arguments passed to the BaseAgent.
        """
        super().__init__(agent_id=agent_id, **kwargs)
        self.analysis_depth = analysis_depth
        # Initialize the voice engine for this agent
        self.voice_engine = VictorVoiceEngine(persona="victor", tone="default")
        # Initialize the emotion detector
        self.emotion_detector = EmotionCueDetector()
        logger.info(f"ReflectionAgent '{self.agent_id}' initialized with depth {self.analysis_depth}, VictorVoiceEngine, and EmotionCueDetector.")

    def run(self, context: Dict[str, Any] = None, *args, **kwargs) -> Dict[str, Any]:
        """Executes the reflection protocol using VictorVoiceEngine."""
        logger.info(f"[{self.agent_id}] Running reflection protocol (Depth: {self.analysis_depth})...")

        # 1. Prepare the prompt/context for the voice engine
        # Example: Provide some context or a task description
        if context is None:
            context = {}
        initial_prompt = context.get("prompt", f"Perform a reflection cycle. Depth: {self.analysis_depth}. Consider recent activities and system state.")

        message_log: List[Dict[str, str]] = [
            {"role": "user", "content": initial_prompt}
        ]

        # 2. Use VictorVoiceEngine to generate the reflection output
        logger.info(f"[{self.agent_id}] Requesting reflection generation from VictorVoiceEngine...")
        reflection_output = self.voice_engine.speak(message_log=message_log, meta={"agent_id": self.agent_id, "task": "reflection"})

        logger.info(f"[{self.agent_id}] VictorVoiceEngine response received.")
        print(f"ReflectionAgent '{self.agent_id}' generated reflection:\n{reflection_output}")

        # 3. Detect emotion cue
        emotion, reason = self.emotion_detector.detect_emotion(reflection_output)
        logger.info(f"[{self.agent_id}] Detected emotion: {emotion} ({reason})")

        # 4. Log and return the result
        logger.info(f"[{self.agent_id}] Reflection protocol finished.")
        return {
            "status": "completed",
            "reflection": reflection_output,
            "emotion": emotion,
            "reason": reason
        } 