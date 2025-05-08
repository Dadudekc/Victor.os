# src/dreamscape/agents/writer_agent.py
# Agent responsible for writing devblog content based on plans.
import asyncio
import logging
import traceback  # Added for error details

# from datetime import datetime, timezone # Removed unused import
from typing import Any, Dict  # Removed Type

# EDIT START: Add missing imports
# {{ EDIT START: Updated Imports }}
from dreamos.core.coordination.base_agent import BaseAgent, TaskMessage

# from dreamos.core.utils.llm_provider import BaseLLMProvider, OpenAILLMProvider # Removed unused import  # noqa: E501
from dreamos.integrations.openai_client import (  # Import the specific client
    OpenAIClient,
    OpenAIClientError,
)

# Import Dreamscape specific models
from ..core.content_models import ContentDraft, ContentPlan

# EDIT END

# ADDED: Import get_config
from dreamos.core.config import get_config

# from ..events.event_types import DreamscapeEventType # Removed
# from ..schemas.event_schemas import WritingRequestedPayload # Removed
# from pydantic import ValidationError # Removed
# {{ EDIT END }}

logger = logging.getLogger(__name__)

# Constants (Consider moving to config)
# REMOVED: DEFAULT_MODEL, DEFAULT_MAX_TOKENS constants at module level


# {{ EDIT START: Inherit from BaseAgent }}
class ContentWriterAgent(BaseAgent):
    # {{ EDIT END }}
    """Generates content drafts based on provided ContentPlans, handling tasks of type 'WRITE_CONTENT_DRAFT'."""  # noqa: E501

    WRITE_COMMAND_TYPE = "WRITE_CONTENT_DRAFT"

    # EDIT START: Updated __init__
    def __init__(self, agent_id: str, **kwargs):
        """
        Initializes the Content Writer Agent.

        Args:
            agent_id: The ID of the agent.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(agent_id=agent_id, **kwargs)

        agent_config = get_config() # Get global config
        # Assuming path like: agent_config.dreamscape.agents.writer.model
        self.model = agent_config.dreamscape.agents.writer.model if \
                       hasattr(agent_config.dreamscape.agents, 'writer') and \
                       hasattr(agent_config.dreamscape.agents.writer, 'model') else "gpt-4-turbo"
        self.max_tokens = agent_config.dreamscape.agents.writer.max_tokens if \
                            hasattr(agent_config.dreamscape.agents, 'writer') and \
                            hasattr(agent_config.dreamscape.agents.writer, 'max_tokens') else 4096

        if not hasattr(self, 'openai_client') or not self.openai_client:
             self.openai_client = OpenAIClient() # OpenAIClient uses get_config internally now

        if not self.openai_client.is_functional():
            logger.error("ContentWriterAgent requires a functional OpenAI client.")
            # Handle appropriately

        # Register command handler
        self.register_command_handler(
            self.WRITE_COMMAND_TYPE, self.handle_write_request
        )

        logger.info(
            f"ContentWriterAgent ({self.agent_id}) initialized and ready for '{self.WRITE_COMMAND_TYPE}' tasks."  # noqa: E501
        )

    # {{ EDIT END }}

    # {{ EDIT START: Implement _on_start/_on_stop (Optional placeholders) }}
    async def _on_start(self):
        """Called when the agent starts."""
        logger.info(f"{self.agent_id} _on_start called.")
        # EDIT START: Check client readiness
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
        await asyncio.sleep(0)

    # {{ EDIT END }}

    # {{ EDIT START: Modified handle_write_request to be a command handler }}
    async def handle_write_request(self, task: TaskMessage) -> Dict[str, Any]:
        """Handles a task request to generate a content draft based on a plan.

        Args:
            task: The TaskMessage object containing the request details.
                  Expected params: {'plan': Dict[str, Any]} where the dict
                  can be parsed into a ContentPlan.

        Returns:
            A dictionary containing the generated draft or error information.
        """
        plan_data = task.params.get("plan")

        if not plan_data or not isinstance(plan_data, dict):
            logger.error(
                f"Task {task.task_id}: Writing request received without valid plan data in params."  # noqa: E501
            )
            return {"error": "Invalid or missing 'plan' in task parameters"}

        try:
            # Attempt to parse the plan data
            plan = ContentPlan(**plan_data)
        except Exception as e:  # Catch potential errors during plan parsing
            logger.error(
                f"Task {task.task_id}: Failed to parse ContentPlan from task params: {e}",  # noqa: E501
                exc_info=True,
            )
            return {
                "error": f"Failed to parse ContentPlan data: {e}",
                "details": traceback.format_exc(),
            }

        # EDIT START: Check if OpenAI client is available
        if not self.openai_client:
            error_reason = "OpenAI client not available or configured for writer agent."
            logger.error(f"Task {task.task_id}: {error_reason}")
            return {
                "error": error_reason,
                "topic": plan.topic,
            }  # Include topic in error
        # EDIT END

        logger.info(
            f"Task {task.task_id}: Generating content draft for topic: '{plan.topic}'."
        )
        await self.publish_task_progress(
            task, 0.1, "Starting content draft generation..."
        )

        # === Placeholder Writing Logic ===
        # TODO: Implement actual LLM call here.
        #   - Choose LLM integration (e.g., OpenAI, Azure via config).
        #   - Construct prompt using 'plan' (topic, keywords, outline).
        #   - Call LLM client, handle response/errors.
        #   - Parse LLM output into title and body sections.
        #   - Populate ContentDraft object.
        try:
            # Construct prompt
            prompt = self._build_writing_prompt(plan)
            logger.debug(
                f"Task {task.task_id}: Sending writing prompt to LLM:\n{prompt[:500]}..."  # Log prompt start
            )
            await self.publish_task_progress(
                task, 0.3, "Calling LLM for draft..."
            )  # Update progress

            # Call LLM
            model = self.model
            max_tokens = self.max_tokens

            # === Actual LLM Call ===
            llm_response = await self.openai_client.generate_text(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=0.7,  # Higher temperature for more creative writing
            )
            # ========================

            logger.debug(
                f"Task {task.task_id}: Received LLM response.\n{llm_response[:500]}..."  # Log response start
            )
            await self.publish_task_progress(task, 0.7, "Parsing LLM response...")

            # Parse response
            title, body = self._parse_llm_draft(llm_response, plan.topic)

            draft = ContentDraft(title=title, body=body, plan=plan)
            logger.info(
                f"Task {task.task_id}: Generated draft via LLM for topic: '{plan.topic}'."  # noqa: E501
            )

            await self.publish_task_progress(task, 0.9, "Draft generation complete.")

            # Return the successful result payload
            result_payload = (
                draft.model_dump() if hasattr(draft, "model_dump") else draft.__dict__
            )
            return result_payload

        except OpenAIClientError as e:
            error_reason = f"OpenAI Client Error during writing: {e}"
            logger.error(f"Task {task.task_id}: {error_reason}", exc_info=True)
            return {
                "error": error_reason,
                "details": traceback.format_exc(),
                "topic": plan.topic,
            }
        except Exception as e:
            error_reason = (
                f"Exception during draft generation: {type(e).__name__}: {str(e)}"
            )
            logger.error(
                f"Task {task.task_id}: Error generating draft for topic '{plan.topic}': {e}",  # noqa: E501
                exc_info=True,
            )
            # Return error details
            return {
                "error": error_reason,
                "details": traceback.format_exc(),
                "topic": plan.topic,
            }
        # EDIT END

    # {{ EDIT END }}

    # {{ EDIT START: Add helper methods for prompt building and parsing }} # Keep this edit block if methods are new  # noqa: E501
    def _build_writing_prompt(self, plan: ContentPlan) -> str:
        """Builds the prompt for the LLM to generate content based on a plan."""
        outline_str = "\n".join([f"- {item}" for item in plan.outline])
        prompt = (
            f"You are a content writer for a software development blog called Digital Dreamscape.\n"  # noqa: E501
            f"Your task is to write a blog post draft based on the following topic and outline.\n\n"  # noqa: E501
            f"Topic: {plan.topic}\n\n"
            f"Outline:\n{outline_str}\n\n"
            f"Instructions:\n"
            f"- Write engaging and informative content suitable for a developer audience.\n"  # noqa: E501
            f"- Follow the structure provided by the outline.\n"
            f"- Start the response with a suitable Title for the blog post, prefixed with 'Title: '.\n"  # noqa: E501
            f"- After the title, provide the main Body of the blog post.\n"
            f"- Use Markdown for formatting (e.g., headings for outline sections, code blocks if appropriate).\n"  # noqa: E501
            f"- Aim for clarity and accuracy.\n\n"
            f"Title: [Your Title Here]\n\n"
            f"Body:\n[Your Blog Post Body Here]"
        )
        return prompt

    def _parse_llm_draft(
        self, llm_response: str, default_topic: str
    ) -> tuple[str, str]:
        """Parses the LLM response to extract title and body."""
        title = f"Draft: {default_topic}"  # Default title
        body = llm_response.strip()  # Default body is the whole response

        lines = llm_response.strip().split("\n")
        title_found = False
        body_lines = []

        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if not title_found and stripped_line.lower().startswith("title:"):
                potential_title = stripped_line[len("title:") :].strip()
                if potential_title:
                    title = potential_title
                    title_found = True
                    # Assume body starts after title line, potentially skipping blank lines  # noqa: E501
                    start_body_index = i + 1
                    while (
                        start_body_index < len(lines)
                        and not lines[start_body_index].strip()
                    ):
                        start_body_index += 1
                    # Check if body marker exists
                    if (
                        start_body_index < len(lines)
                        and lines[start_body_index].strip().lower() == "body:"
                    ):
                        start_body_index += 1  # Skip the "Body:" line itself

                    body_lines = lines[start_body_index:]
                    break  # Stop searching for title once found

        if body_lines:  # If title parsing logic ran and found body lines
            body = "\n".join(body_lines).strip()
        elif title_found:  # If title was found but no body lines followed immediately
            body = ""  # Assume empty body if only title line exists
            logger.warning(
                "Found 'Title:' prefix but couldn't clearly identify body content."
            )
        # Else: keep default body (whole response) if title prefix wasn't found

        if not body:
            logger.warning("Parsed body content is empty.")
            body = f"[LLM generated empty body for topic: {default_topic}]"

        return title, body

    # {{ EDIT END }}

    # {{ EDIT START: Removed old AgentBus interaction methods }}
    # def subscribe_to_requests(self):
    #     ...
    # async def handle_write_request_event(self, event_data: Dict[str, Any]):
    #     ...
    # async def publish_event(self, event_type: DreamscapeEventType, payload: Dict[str, Any]):  # noqa: E501
    #     ...
    # {{ EDIT END }}
