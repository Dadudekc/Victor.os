# src/dreamscape/agents/planner_agent.py
# Agent responsible for planning devblog content.
import asyncio
import logging
import traceback
from typing import Any, Dict

# from dreamos.core.coordination.agent_bus import AgentBus, BaseEvent, EventType # OLD PATH  # noqa: E501
from dreamos.config import AppConfig  # Import AppConfig

# from ..events.event_types import DreamscapeEventType # No longer needed
# Import AgentBus interface
from dreamos.coordination.agent_bus import (  # CORRECTED PATH
    AgentBus,
)

# {{ EDIT: Import schema }}
# from ..schemas.event_schemas import PlanRequestedPayload, BaseEventPayload # No longer needed  # noqa: E501
# from pydantic import ValidationError # No longer needed for event handling
from dreamos.core.coordination.base_agent import BaseAgent, TaskMessage
from dreamos.integrations.openai_client import (  # Import the specific client
    OpenAIClient,
    OpenAIClientError,
)
from dreamos.utils.config_utils import (  # Keep for potential direct access if needed
    get_config,
)

# {{ EDIT: Import necessary core models and events }}
from ..core.content_models import ContentPlan

logger = logging.getLogger(__name__)


# {{ EDIT START: Inherit from BaseAgent }}
class ContentPlannerAgent(BaseAgent):
    # {{ EDIT END }}
    """Generates content plans for the Digital Dreamscape devblog.

    Listens for tasks of type 'GENERATE_CONTENT_PLAN' via the AgentBus.
    """

    PLAN_COMMAND_TYPE = "GENERATE_CONTENT_PLAN"

    # {{ EDIT START: Updated __init__ }}
    def __init__(self, config: AppConfig, agent_bus: AgentBus):
        """
        Initializes the Content Planner Agent.

        Args:
            config: The application configuration object.
            agent_bus: An instance of the AgentBus for communication.
        """
        agent_id = get_config(
            "dreamscape.planner_agent.agent_id",
            default="dreamscape_planner_001",
            config_obj=config,
        )
        super().__init__(agent_id=agent_id, agent_bus=agent_bus)
        self.config = config  # Store config if needed for other settings

        # EDIT START: Initialize OpenAI Client
        try:
            self.openai_client = OpenAIClient(config=config)
        except OpenAIClientError as e:
            logger.error(
                f"Failed to initialize OpenAI Client for {self.agent_id}: {e}",
                exc_info=True,
            )
            # Agent might still start but LLM calls will fail. Consider raising or preventing start.  # noqa: E501
            self.openai_client = None
            logger.warning(
                f"{self.agent_id} initialized WITHOUT a functional OpenAI client."
            )
        # EDIT END

        # Register command handler
        self.register_command_handler(self.PLAN_COMMAND_TYPE, self.handle_plan_request)

        logger.info(
            f"ContentPlannerAgent ({self.agent_id}) initialized and ready for '{self.PLAN_COMMAND_TYPE}' tasks."  # noqa: E501
        )

    # {{ EDIT END }}

    # {{ EDIT START: Implement _on_start/_on_stop (Optional placeholders) }}
    async def _on_start(self):
        """Called when the agent starts."""
        logger.info(f"{self.agent_id} _on_start called.")
        # EDIT START: Check client readiness
        # Add any specific startup logic here (e.g., load models)
        if self.openai_client:
            logger.info(f"OpenAI Client ready for {self.agent_id}.")
        else:
            logger.warning(
                f"{self.agent_id} started but OpenAI client is not available/configured."  # noqa: E501
            )
        # EDIT END
        await asyncio.sleep(0)  # Yield control

    async def _on_stop(self):
        """Called when the agent stops."""
        logger.info(f"{self.agent_id} _on_stop called.")
        # Add any specific cleanup logic here
        await asyncio.sleep(0)

    # {{ EDIT END }}

    # {{ EDIT START: Modified handle_plan_request to be a command handler }}
    async def handle_plan_request(self, task: TaskMessage) -> Dict[str, Any]:
        """Handles a task request to generate a content plan.

        Args:
            task: The TaskMessage object containing the request details.

        Returns:
            A dictionary containing the generated plan or error information.
        """
        # Parameters are now in task.params
        topic = task.params.get("topic")
        # Optional: requester_id = task.originator_agent_id (might be supervisor or another agent)  # noqa: E501
        # Correlation ID is automatically handled by BaseAgent

        if not topic:
            logger.error(
                f"Task {task.task_id}: Planning request received without a topic."
            )
            # Let BaseAgent handle publishing failure via raising exception or returning error dict  # noqa: E501
            # For clarity, explicitly return error payload:
            return {"error": "Missing topic in task parameters"}

        # EDIT START: Check if OpenAI client is available
        if not self.openai_client:
            error_reason = (
                "OpenAI client not available or configured for planner agent."
            )
            logger.error(f"Task {task.task_id}: {error_reason}")
            return {"error": error_reason}
        # EDIT END

        logger.info(
            f"Task {task.task_id}: Generating content plan for topic: '{topic}'."
        )

        # BaseAgent handles publishing TASK_STARTED before calling this handler.
        # We can optionally publish progress.
        await self.publish_task_progress(task, 0.1, "Starting planning process...")

        # EDIT START: Replace Placeholder with LLM Call
        # === LLM Planning Logic ===
        try:
            # Construct prompt
            prompt = self._build_planning_prompt(topic)
            logger.debug(
                f"Task {task.task_id}: Sending planning prompt to LLM:\n{prompt}"
            )

            # Call LLM
            # Get model/params from config if needed
            model = get_config(
                "dreamscape.planner_agent.llm_model",
                default="gpt-3.5-turbo",
                config_obj=self.config,
            )
            max_tokens = get_config(
                "dreamscape.planner_agent.max_tokens",
                default=500,
                config_obj=self.config,
            )

            llm_response = await self.openai_client.generate_text(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=0.5,  # Lower temperature for more structured output like an outline  # noqa: E501
            )

            logger.debug(f"Task {task.task_id}: Received LLM response:\n{llm_response}")
            await self.publish_task_progress(task, 0.7, "Parsing LLM response...")

            # Parse LLM response into an outline
            parsed_outline = self._parse_llm_outline(llm_response)
            if not parsed_outline:  # Add check even for placeholder
                raise ValueError(
                    "Failed to parse a valid outline from the LLM response."
                )

            plan = ContentPlan(topic=topic, outline=parsed_outline)
            logger.info(
                f"Task {task.task_id}: Generated plan via LLM for topic: '{topic}'."
            )

            await self.publish_task_progress(task, 0.9, "Planning complete.")

            # Return the successful result payload for BaseAgent to publish TASK_COMPLETED  # noqa: E501
            # Use model_dump() if ContentPlan is a Pydantic model
            result_payload = (
                plan.model_dump() if hasattr(plan, "model_dump") else plan.__dict__
            )
            return result_payload

        # EDIT START: Add specific OpenAIClientError handling
        except OpenAIClientError as e:
            error_reason = f"OpenAI Client Error during planning: {e}"
            logger.error(f"Task {task.task_id}: {error_reason}", exc_info=True)
            return {"error": error_reason, "details": traceback.format_exc()}
        # EDIT END
        except Exception as e:
            error_reason = f"Exception during planning: {type(e).__name__}: {str(e)}"
            logger.error(
                f"Task {task.task_id}: Error generating plan for topic '{topic}': {e}",
                exc_info=True,
            )
            # Return error details for BaseAgent to publish TASK_FAILED
            return {"error": error_reason, "details": traceback.format_exc()}
        # EDIT END

    # {{ EDIT END }}

    # {{ EDIT START: Add helper methods for prompt building and parsing }} # Keep this edit block if methods are new  # noqa: E501
    def _build_planning_prompt(self, topic: str) -> str:
        """Builds the prompt for the LLM to generate a content plan outline."""
        # Simple prompt, can be refined based on desired plan structure
        prompt = (
            f"You are a content planner for a software development blog called Digital Dreamscape.\n"  # noqa: E501
            f"Your task is to create a concise, logical outline for a blog post about the following topic:\n\n"  # noqa: E501
            f"Topic: {topic}\n\n"
            f"Provide the outline as a numbered list. Each item should represent a major section or sub-section of the blog post.\n"  # noqa: E501
            f"Focus on structure and flow. Do not write the content itself.\n\n"
            f"Outline:\n"
            f"1."
        )
        return prompt

    def _parse_llm_outline(self, llm_response: str) -> list[str]:
        """Parses the LLM response text to extract a list of outline items."""
        lines = llm_response.strip().split("\n")
        outline = []
        for line in lines:
            line = line.strip()
            # Try to capture numbered items or lines starting with common list markers
            if line and (line[0].isdigit() or line.startswith(("-", "*", "+"))):
                # Remove the number/marker and leading space if present
                parts = line.split(".", 1)
                if len(parts) == 2 and parts[0].isdigit():
                    item = parts[1].strip()
                elif line.startswith(("-", "*", "+")):
                    item = line[1:].strip()
                else:
                    item = line  # Keep line as is if parsing fails

                if item:  # Avoid empty items
                    outline.append(item)
            elif (
                line and not outline
            ):  # Handle case where LLM might not start numbering immediately
                outline.append(line)

        # Basic sanity check - avoid single-line, non-sensical responses
        if len(outline) < 2 and len(llm_response) < 30:
            logger.warning(f"Parsed outline seems too short or trivial: {outline}")
            # Return empty list to indicate parsing failure if it seems invalid
            # return [] # Stricter parsing

        if not outline:
            logger.warning(
                f"Could not parse any outline items from LLM response:\n{llm_response}"
            )

        return outline

    # {{ EDIT END }}

    # {{ EDIT START: Removed old AgentBus interaction methods }}
    # def subscribe_to_requests(self):
    #     ...
    # async def handle_plan_request_event(self, event_data: Dict[str, Any]):
    #     ...
    # async def publish_event(self, event_type: DreamscapeEventType, payload: Dict[str, Any]):  # noqa: E501
    #     ...
    # {{ EDIT END }}

    # Example: If planning logic needed config
    # async def handle_plan_request(...):
    # planning_model = get_config("dreamscape.planner_agent.llm_model", default="gpt-4", config_obj=self.config)  # noqa: E501
    # ... use planning_model ...
