"""
JARVIS Interaction Patterns
Implements intuitive human-AI communication patterns for the JARVIS system.

This module provides:
- Natural language interaction patterns
- Multi-modal input/output handling
- Context-aware communication
- Adaptive response generation
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List

from .jarvis_core import JarvisCore

logger = logging.getLogger(__name__)


class InteractionPattern:
    """Base class for interaction patterns."""

    def __init__(self, name: str, description: str):
        """Initialize an interaction pattern.

        Args:
            name: Name of the pattern
            description: Description of the pattern
        """
        self.name = name
        self.description = description

    def matches(self, input_text: str) -> bool:
        """Check if this pattern matches the input.

        Args:
            input_text: Input text to check

        Returns:
            True if pattern matches, False otherwise
        """
        raise NotImplementedError("Subclasses must implement matches()")

    def process(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process input according to this pattern.

        Args:
            input_text: Input text to process
            context: Current interaction context

        Returns:
            Response dictionary
        """
        raise NotImplementedError("Subclasses must implement process()")


class CommandPattern(InteractionPattern):
    """Pattern for command-like interactions."""

    def __init__(self, command_words: List[str], handler: Callable):
        """Initialize a command pattern.

        Args:
            command_words: List of words that trigger this command
            handler: Function to handle the command
        """
        super().__init__(
            name="command", description="Direct command interaction pattern"
        )
        self.command_words = command_words
        self.handler = handler

    def matches(self, input_text: str) -> bool:
        """Check if input matches command pattern.

        Args:
            input_text: Input text to check

        Returns:
            True if pattern matches, False otherwise
        """
        input_lower = input_text.lower()
        return any(cmd in input_lower.split() for cmd in self.command_words)

    def process(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process command input.

        Args:
            input_text: Input text to process
            context: Current interaction context

        Returns:
            Response dictionary
        """
        return self.handler(input_text, context)


class ConversationalPattern(InteractionPattern):
    """Pattern for natural conversational interactions."""

    def __init__(self):
        """Initialize a conversational pattern."""
        super().__init__(
            name="conversational", description="Natural language conversation pattern"
        )

    def matches(self, input_text: str) -> bool:
        """Always matches as fallback pattern.

        Args:
            input_text: Input text to check

        Returns:
            True (always matches as fallback)
        """
        return True

    def process(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process conversational input.

        Args:
            input_text: Input text to process
            context: Current interaction context

        Returns:
            Response dictionary
        """
        # Simple response for now - in a real implementation would use NLP
        return {
            "type": "conversation",
            "content": f"I understand you're saying: {input_text}",
            "confidence": 0.7,
        }


class QueryPattern(InteractionPattern):
    """Pattern for question/query interactions."""

    def __init__(self):
        """Initialize a query pattern."""
        super().__init__(name="query", description="Question answering pattern")
        self.question_starters = [
            "what",
            "when",
            "where",
            "who",
            "why",
            "how",
            "can",
            "could",
            "would",
            "will",
            "is",
            "are",
            "do",
            "does",
        ]

    def matches(self, input_text: str) -> bool:
        """Check if input is a question.

        Args:
            input_text: Input text to check

        Returns:
            True if pattern matches, False otherwise
        """
        input_lower = input_text.lower().strip()

        # Check for question mark
        if input_lower.endswith("?"):
            return True

        # Check for question starters
        first_word = input_lower.split()[0] if input_lower else ""
        return first_word in self.question_starters

    def process(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process query input.

        Args:
            input_text: Input text to process
            context: Current interaction context

        Returns:
            Response dictionary
        """
        # Simple response for now - in a real implementation would use QA system
        return {
            "type": "query_response",
            "content": f"To answer your question: I would need to search for information about '{input_text}'",
            "confidence": 0.8,
        }


class InteractionManager:
    """Manager for JARVIS interaction patterns."""

    def __init__(self, jarvis_core: JarvisCore):
        """Initialize the interaction manager.

        Args:
            jarvis_core: Reference to the JARVIS core system
        """
        self.jarvis = jarvis_core
        self.patterns = []
        self.context = {
            "session_start": datetime.now().isoformat(),
            "interaction_count": 0,
            "last_interaction": None,
            "user_preferences": {},
        }
        self.lock = threading.RLock()

        # Register default patterns
        self._register_default_patterns()

    def _register_default_patterns(self) -> None:
        """Register the default interaction patterns."""
        # Command pattern for system commands
        self.register_pattern(
            CommandPattern(
                command_words=["jarvis", "system", "activate", "deactivate", "status"],
                handler=self._handle_system_command,
            )
        )

        # Query pattern for questions
        self.register_pattern(QueryPattern())

        # Conversational pattern as fallback
        self.register_pattern(ConversationalPattern())

    def register_pattern(self, pattern: InteractionPattern) -> None:
        """Register a new interaction pattern.

        Args:
            pattern: The pattern to register
        """
        with self.lock:
            self.patterns.append(pattern)
            logger.info(f"Registered interaction pattern: {pattern.name}")

    def process_input(self, input_text: str, source: str = "user") -> Dict[str, Any]:
        """Process input using registered patterns.

        Args:
            input_text: Input text to process
            source: Source of the input

        Returns:
            Response dictionary
        """
        with self.lock:
            # Update context
            self.context["interaction_count"] += 1
            self.context["last_interaction"] = datetime.now().isoformat()

            # Find matching pattern
            for pattern in self.patterns:
                if pattern.matches(input_text):
                    logger.debug(f"Using pattern: {pattern.name}")

                    # Process with pattern
                    response = pattern.process(input_text, self.context.copy())

                    # Pass to JARVIS core if needed
                    if not response.get("bypass_core", False):
                        jarvis_response = self.jarvis.process_input(input_text, source)

                        # Merge responses (pattern response takes precedence)
                        for key, value in jarvis_response.items():
                            if key not in response:
                                response[key] = value

                    return response

            # Fallback to JARVIS core directly
            return self.jarvis.process_input(input_text, source)

    def _handle_system_command(
        self, input_text: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle system commands.

        Args:
            input_text: Input text containing command
            context: Current interaction context

        Returns:
            Response dictionary
        """
        input_lower = input_text.lower()

        if "activate" in input_lower or "start" in input_lower:
            success = self.jarvis.activate()
            return {
                "type": "system_response",
                "content": (
                    "JARVIS activated and ready."
                    if success
                    else "Failed to activate JARVIS."
                ),
                "success": success,
                "bypass_core": True,
            }

        elif "deactivate" in input_lower or "stop" in input_lower:
            success = self.jarvis.deactivate()
            return {
                "type": "system_response",
                "content": (
                    "JARVIS deactivated." if success else "Failed to deactivate JARVIS."
                ),
                "success": success,
                "bypass_core": True,
            }

        elif "status" in input_lower:
            system_state = (
                self.jarvis._get_system_state()
                if self.jarvis.is_active
                else {"status": "inactive"}
            )
            return {
                "type": "system_response",
                "content": f"JARVIS is {system_state['status']}.",
                "system_state": system_state,
                "bypass_core": True,
            }

        return {
            "type": "system_response",
            "content": "Unknown system command.",
            "success": False,
            "bypass_core": True,
        }

    def load_user_preferences(self, user_id: str) -> bool:
        """Load user preferences.

        Args:
            user_id: User identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            prefs_path = Path(f"runtime/jarvis/user_preferences/{user_id}.json")

            if not prefs_path.exists():
                logger.info(f"No preferences found for user {user_id}")
                return False

            with open(prefs_path, "r", encoding="utf-8") as f:
                self.context["user_preferences"] = json.load(f)

            logger.info(f"Loaded preferences for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error loading user preferences: {str(e)}")
            return False

    def save_user_preferences(self, user_id: str) -> bool:
        """Save user preferences.

        Args:
            user_id: User identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            prefs_path = Path(f"runtime/jarvis/user_preferences/{user_id}.json")
            prefs_path.parent.mkdir(parents=True, exist_ok=True)

            with open(prefs_path, "w", encoding="utf-8") as f:
                json.dump(self.context["user_preferences"], f, indent=2)

            logger.info(f"Saved preferences for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving user preferences: {str(e)}")
            return False
