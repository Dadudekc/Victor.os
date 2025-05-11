# src/dreamos/core/agents/capabilities/library/task_rewrite.py
import logging
from typing import Any, Dict, List, Optional, TypedDict

# Assuming LLM interaction utilities exist
# from dreamos.core.llm.client import get_llm_client, LlmApiError

# Assuming TaskNexus/Adapter access for fetching task details
# from dreamos.core.tasks.nexus.db_task_nexus import DbTaskNexus
# from dreamos.core.db.sqlite_adapter import SQLiteAdapter, TaskDict

logger = logging.getLogger(__name__)


# --- Placeholder for LLM Client --- #
# Replace with actual implementation
class MockLlmClient:
    def generate(self, prompt: str, **kwargs) -> str:
        logger.warning("Using MockLlmClient for task rewrite!")
        return f"[Rewritten based on guidelines]: {prompt[:100]}... (Mock Response)"


def get_llm_client():
    return MockLlmClient()


class LlmApiError(Exception):
    pass


# --- End Placeholder --- #


# --- Capability Input/Output Schemas --- #
class TaskRewriteInput(TypedDict):
    task_id: str
    original_task_data: Optional[Dict[str, Any]]  # Optional: Fetched if not provided
    rewrite_guidelines: Optional[str]


class TaskRewriteOutput(TypedDict):
    rewritten_description: str
    suggested_tags: Optional[List[str]]
    # confidence_score: Optional[float]


# --- Capability Implementation --- #
def task_rewrite_capability(
    input_data: TaskRewriteInput,
    # adapter: SQLiteAdapter # Pass adapter if needed to fetch task data
) -> TaskRewriteOutput:
    """Uses an LLM to rewrite a task description for clarity and detail."""
    task_id = input_data.get("task_id")
    task_data = input_data.get("original_task_data")
    guidelines = input_data.get("rewrite_guidelines")

    if not task_id:
        raise ValueError("task_id is required for rewriting.")

    # TODO: Fetch task_data using adapter if not provided
    if not task_data:
        logger.warning(
            f"Original task data for {task_id} not provided. Rewrite context may be limited."
        )
        # Placeholder if fetch fails or isn't implemented yet
        task_data = {
            "task_id": task_id,
            "description": "[Original Description Missing]",
        }
        # try:
        #     task_data = adapter.get_task(task_id)
        #     if not task_data:
        #         raise ValueError(f"Task {task_id} not found.")
        # except Exception as e:
        #     logger.error(f"Failed to fetch task {task_id}: {e}")
        #     raise ValueError(f"Could not fetch task {task_id} for rewrite.") from e

    original_description = task_data.get("description", "")
    original_tags = task_data.get("tags", [])

    # --- Construct LLM Prompt --- #
    prompt_lines = [
        "You are an expert project manager assistant. Your goal is to rewrite task descriptions to be clear, specific, actionable, and adhere to best practices.",
        "Rewrite the following task description:",
        f"Task ID: {task_id}",
        f"Original Description: {original_description}",
        f"Original Tags: {original_tags}",
        "\nPlease rewrite the description to be more detailed and clear. Ensure it includes:",
        "- A clear statement of the goal.",
        "- Specific, measurable acceptance criteria (if possible).",
        "- Context or background if necessary.",
    ]
    if guidelines:
        prompt_lines.append(f"\nFollow these specific guidelines: {guidelines}")

    prompt_lines.append(
        "\nOutput ONLY the rewritten description text, without any preamble or explanation."
        " (Optional: If you have suggestions for better tags, list them on a separate line starting with 'Suggested Tags:')"
    )
    prompt = "\n".join(prompt_lines)
    logger.debug(f"Task Rewrite Prompt for {task_id}:\n{prompt}")

    # --- Call LLM --- #
    try:
        llm_client = get_llm_client()
        # TODO: Add LLM parameters (model, max_tokens, temperature) from config
        llm_response = llm_client.generate(prompt)
    except LlmApiError as e:
        logger.error(f"LLM API error during task rewrite for {task_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling LLM for task rewrite {task_id}: {e}")
        raise LlmApiError(f"LLM call failed: {e}") from e

    # --- Parse Response --- #
    # Basic parsing, assuming LLM follows instructions
    rewritten_desc = llm_response.strip()
    suggested_tags = None

    # TODO: Implement more robust parsing if needed, e.g., for suggested tags
    # if "\nSuggested Tags:" in rewritten_desc:
    #    parts = rewritten_desc.split("\nSuggested Tags:", 1)
    #    rewritten_desc = parts[0].strip()
    #    try:
    #        suggested_tags = [tag.strip() for tag in parts[1].strip().split(',') if tag.strip()]
    #    except Exception: pass # Ignore tag parsing errors

    if not rewritten_desc:
        logger.warning(
            f"LLM returned empty description for task {task_id}. Using original."
        )
        rewritten_desc = original_description  # Fallback?

    logger.info(f"Task {task_id} description rewritten by LLM.")

    return {"rewritten_description": rewritten_desc, "suggested_tags": suggested_tags}


# --- Capability Definition (for registration) --- #
TASK_REWRITE_CAPABILITY_ID = "task.rewrite"
TASK_REWRITE_CAPABILITY_INFO = {
    "capability_id": TASK_REWRITE_CAPABILITY_ID,
    "capability_name": "Task Rewriter/Clarifier",
    "description": "Rewrites a task description using an LLM for clarity, detail, and adherence to standards.",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "ID of the task to rewrite."},
            "original_task_data": {
                "type": "object",
                "description": "(Optional) Full task data dictionary.",
            },
            "rewrite_guidelines": {
                "type": "string",
                "description": "(Optional) Specific instructions for the LLM.",
            },
        },
        "required": ["task_id"],
    },
    "input_schema": TaskRewriteInput.__annotations__,  # Approximate schema
    "output_schema": TaskRewriteOutput.__annotations__,  # Approximate schema
    # Add metadata, performance, resources if needed
}
