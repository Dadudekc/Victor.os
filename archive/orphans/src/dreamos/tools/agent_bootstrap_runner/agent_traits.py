"""
Agent traits and validation policies.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .config import AGENT_CHARTERS, AGENT_TRAITS


class TraitsConfigError(Exception):
    """Error raised for invalid traits configuration."""

    pass


class AgentTraits:
    """Manages agent-specific traits and validation policies."""

    def __init__(self, agent_id: str, traits_file: Optional[Path] = None):
        """
        Initialize agent traits.

        Args:
            agent_id: Agent identifier (e.g. "Agent-2")
            traits_file: Optional path to custom traits file
        """
        self.agent_id = agent_id
        self.traits = AGENT_TRAITS.get(agent_id, [])
        self.charter = AGENT_CHARTERS.get(agent_id, "GENERAL OPERATIONS")
        self.validation_policy = "strict"  # Default to strict validation
        self.prompt_context = {}

        if traits_file:
            self._load_custom_traits(traits_file)

    def _load_custom_traits(self, traits_file: Path) -> None:
        """
        Load custom traits from a file.

        Args:
            traits_file: Path to traits configuration file

        Raises:
            TraitsConfigError: If traits file is invalid
        """
        try:
            if not traits_file.exists():
                raise TraitsConfigError(f"Traits file not found: {traits_file}")

            with traits_file.open() as f:
                config = json.load(f)

            if not isinstance(config, dict):
                raise TraitsConfigError(
                    "Invalid traits file format - must be a JSON object"
                )

            agent_config = config.get(self.agent_id)
            if not agent_config:
                raise TraitsConfigError(f"No configuration found for {self.agent_id}")

            # Update traits
            if "traits" in agent_config:
                if not isinstance(agent_config["traits"], list):
                    raise TraitsConfigError("Traits must be a list of strings")
                self.traits = agent_config["traits"]

            # Update charter
            if "charter" in agent_config:
                if not isinstance(agent_config["charter"], str):
                    raise TraitsConfigError("Charter must be a string")
                self.charter = agent_config["charter"]

            # Update validation policy
            if "validation_policy" in agent_config:
                if agent_config["validation_policy"] not in ["strict", "lenient"]:
                    raise TraitsConfigError(
                        "Validation policy must be 'strict' or 'lenient'"
                    )
                self.validation_policy = agent_config["validation_policy"]

            # Update prompt context
            if "prompt_context" in agent_config:
                if not isinstance(agent_config["prompt_context"], dict):
                    raise TraitsConfigError("Prompt context must be a dictionary")
                self.prompt_context = agent_config["prompt_context"]

        except json.JSONDecodeError as e:
            raise TraitsConfigError(f"Invalid JSON in traits file: {e}")
        except Exception as e:
            raise TraitsConfigError(f"Error loading traits file: {e}")

    def validate_traits(self) -> bool:
        """
        Validate that traits are properly configured.

        Returns:
            bool: True if traits are valid
        """
        if not self.traits:
            logging.warning(f"No traits defined for {self.agent_id}")
            return False

        if not self.charter:
            logging.warning(f"No charter defined for {self.agent_id}")
            return False

        return True

    def get_prompt_context(self) -> Dict[str, Any]:
        """
        Get context for prompt generation.

        Returns:
            dict: Context for prompt generation
        """
        context = {
            "traits": self.traits,
            "charter": self.charter,
            "validation_policy": self.validation_policy,
        }

        # Add any custom prompt context
        context.update(self.prompt_context)

        return context

    def apply_validation_policy(self, validation_result: bool) -> bool:
        """
        Apply validation policy to a validation result.

        Args:
            validation_result: Raw validation result

        Returns:
            bool: Modified validation result based on policy
        """
        if self.validation_policy == "lenient":
            # In lenient mode, warnings are treated as successes
            return True
        return validation_result

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert traits to dictionary format.

        Returns:
            dict: Dictionary representation of traits
        """
        return {
            "agent_id": self.agent_id,
            "traits": self.traits,
            "charter": self.charter,
            "validation_policy": self.validation_policy,
            "prompt_context": self.prompt_context,
        }
