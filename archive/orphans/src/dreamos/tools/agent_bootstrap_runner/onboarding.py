"""
Agent Onboarding System for Dream.OS

Handles automated onboarding of Cursor-based agents with response tracking.
"""

import asyncio
import logging

from dreamos.utils.gui.injector import CursorInjector
from dreamos.utils.gui.retriever import ResponseRetriever

from .config import AgentConfig
from .validation import validate_all_files


class AgentOnboardingManager:
    """Manages onboarding for multiple agents."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(f"onboarding.{config.agent_id}")

    async def onboard(self) -> bool:
        """
        Run the onboarding process for this agent.

        Returns:
            bool: True if onboarding was successful
        """
        try:
            # Validate all required files and directories
            validation = validate_all_files(
                self.logger, self.config, is_onboarding=True
            )
            if not validation.passed:
                self.logger.error(f"Validation failed: {validation.error}")
                return False

            # Initialize UI components
            injector = CursorInjector(
                agent_id=self.config.agent_id, coords_file=str(self.config.coords_file)
            )
            retriever = ResponseRetriever(
                agent_id=self.config.agent_id_for_retriever,
                coords_file=str(self.config.copy_coords_file),
            )

            # Generate and send onboarding prompt
            onboarding_prompt = self._generate_onboarding_prompt()
            self.logger.info(f"Sending onboarding prompt to {self.config.agent_id}")

            # Inject prompt using cursor coordinates
            try:
                injector.inject(onboarding_prompt)
                self.logger.info(f"Successfully sent prompt to {self.config.agent_id}")

                # Wait for and verify response
                await asyncio.sleep(5)  # Give agent time to process
                response = retriever.get_response()

                if response:
                    self.logger.info(f"Received response from {self.config.agent_id}")
                    self.logger.info(f"Successfully onboarded {self.config.agent_id}")
                    return True
                else:
                    self.logger.error(
                        f"No response received from {self.config.agent_id}"
                    )
                    return False

            except Exception as e:
                self.logger.error(
                    f"Failed to interact with {self.config.agent_id}: {e}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Onboarding failed: {e}")
            return False

    def _generate_onboarding_prompt(self) -> str:
        """Generate the onboarding prompt for this agent."""
        return f"""# {self.config.agent_id} Onboarding

## Welcome
You are now being onboarded as {self.config.agent_id} in the Dream.OS system.

## Your Role: {self.config.charter}

## Your Traits
{self.config.traits}

## Initial Tasks
1. Review the INBOX_LOOP_PROTOCOL
2. Familiarize yourself with your designated role
3. Begin monitoring your assigned responsibilities
4. Establish communication with other agents

## Ready State
Systems initialized. Awaiting confirmation and ready to begin operations.
"""


async def onboard_single_agent(agent_id: str) -> bool:
    """
    Onboard a single agent with the specified ID.

    Args:
        agent_id: The ID of the agent to onboard (e.g. "Agent-2")

    Returns:
        bool: True if onboarding was successful
    """
    config = AgentConfig(agent_id=agent_id)
    manager = AgentOnboardingManager(config)
    return await manager.onboard()
