# src/dreamos/core/agents/capabilities/library/narrative_generate.py
import logging
from pathlib import Path
from typing import Any, Optional, TypedDict
from datetime import datetime, timezone

# EDIT: Use real LLM client
from dreamos.core.llm.client import LlmApiError, get_llm_client

# Import the parser and its types
from dreamos.core.narrative.lore_parser import (
    ContextWindow,
    NarrativeContextData,
    gather_narrative_context,
)

# Assuming access to DB adapter and config for paths
# from dreamos.core.db.sqlite_adapter import SQLiteAdapter
# from dreamos.core.config import AppConfig

logger = logging.getLogger(__name__)

# --- Placeholder for LLM Client --- #
# EDIT: Remove Mock Client
# class MockLlmClient:
#     def generate(self, prompt: str, **kwargs) -> str:
#         logger.warning("Using MockLlmClient for narrative generation!")
#         return f"# Episode: Generated Narrative\n\nBased on the provided context, here is a summary:\n{prompt[:200]}... (Mock Response)"
#
# def get_llm_client():
#     return MockLlmClient()
#
# class LlmApiError(Exception):
#     pass
# --- End Placeholder --- #


# --- Capability Input/Output Schemas --- #
class NarrativeGenerateInput(TypedDict):
    trigger_event_summary: str
    context_window: ContextWindow  # Defined in lore_parser
    style_prompt: Optional[str]


class NarrativeGenerateOutput(TypedDict):
    episode_file_path: Optional[str]
    error: Optional[str]


# --- Capability Implementation --- #
def narrative_generate_episode_capability(
    input_data: NarrativeGenerateInput,
    adapter: Any,  # Should be SQLiteAdapter
    config: Any,  # Should be AppConfig
) -> NarrativeGenerateOutput:
    """Generates a narrative episode based on gathered context using an LLM."""
    trigger_event = input_data.get("trigger_event_summary", "Unknown Event")
    context_window = input_data.get("context_window", {})
    style_prompt = input_data.get("style_prompt", "Write a concise narrative summary.")

    # Get necessary paths from config
    try:
        repo_path = Path(config.project_root)  # Assuming project_root is the repo root
        log_dir = Path(config.logging.log_directory)
        report_dir = Path(config.reporting.captain_log_dir)
        lore_dir = Path(config.narrative.lore_repository_dir)
        episode_dir = lore_dir / "episodes"
        episode_dir.mkdir(parents=True, exist_ok=True)  # Ensure dir exists
    except AttributeError as e:
        error_msg = f"Configuration missing required paths for narrative engine: {e}"
        logger.error(error_msg)
        return {"episode_file_path": None, "error": error_msg}
    except Exception as e:
        error_msg = f"Error accessing config paths: {e}"
        logger.error(error_msg, exc_info=True)
        return {"episode_file_path": None, "error": error_msg}

    # 1. Gather Context using Lore Parser
    logger.info(f"Gathering narrative context for trigger: '{trigger_event}'")
    try:
        context_data: NarrativeContextData = gather_narrative_context(
            context_window=context_window,
            adapter=adapter,
            repo_path=repo_path,
            log_dir=log_dir,
            report_dir=report_dir,
            lore_dir=lore_dir,
        )
    except Exception as e:
        error_msg = f"Failed to gather narrative context: {e}"
        logger.error(error_msg, exc_info=True)
        return {"episode_file_path": None, "error": error_msg}

    # 2. Construct LLM Prompt
    prompt_lines = [
        "Narrative Generation Request",
        f"Trigger Event: {trigger_event}",
        "\n=== Context Data ===",
    ]
    # Add Tasks
    if context_data["tasks"]:
        prompt_lines.append("\n--- Tasks ---")
        for task in context_data["tasks"]:
            # Format task info concisely
            prompt_lines.append(
                f"  - Task {task.get('task_id')}: {task.get('description')[:100]}... (Status: {task.get('status')}, Agent: {task.get('agent_id')}) - Result: {task.get('result_summary')}"
            )

    # Add Commits
    if context_data["commits"]:
        prompt_lines.append("\n--- Git Commits ---")
        prompt_lines.append(context_data["commits"])

    # Add Agent Logs (Summarize potentially?)
    if context_data["agent_logs"]:
        prompt_lines.append("\n--- Agent Logs (Excerpts) ---")
        for agent_id, logs in context_data["agent_logs"].items():
            prompt_lines.append(f"  Agent {agent_id}:")
            # Include first/last few lines or sample?
            for line in logs[:5]:  # Limit log lines included
                prompt_lines.append(f"    {line}")
            if len(logs) > 5:
                prompt_lines.append("    ...")

    # Add Captain Logs
    if context_data["captain_logs"]:
        prompt_lines.append("\n--- Captain Logs (Excerpts) ---")
        prompt_lines.append(context_data["captain_logs"][:1000] + "...")  # Limit length

    # Add Lore Context
    if context_data["lore_context"]:
        prompt_lines.append("\n--- Additional Lore Context ---")
        prompt_lines.append(context_data["lore_context"])

    prompt_lines.extend(
        [
            "\n=== Instructions ===",
            f"Based on the context above, {style_prompt}",
            "Generate a narrative episode summarizing the key events, decisions, and outcomes.",
            "Focus on creating an engaging and informative story.",
            "Output ONLY the narrative text for the episode, suitable for saving to a Markdown file.",
        ]
    )

    prompt = "\n".join(prompt_lines)
    logger.debug(
        f"Narrative Generation Prompt (Trigger: '{trigger_event}'):\n{prompt[:500]}..."
    )  # Log truncated prompt

    # 3. Call LLM
    try:
        llm_client = get_llm_client()
        episode_text = llm_client.generate(prompt)
    except LlmApiError as e:
        error_msg = f"LLM API error during narrative generation: {e}"
        logger.error(error_msg)
        return {"episode_file_path": None, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error calling LLM for narrative generation: {e}"
        logger.error(error_msg, exc_info=True)
        return {"episode_file_path": None, "error": error_msg}

    if not episode_text or not episode_text.strip():
        error_msg = "LLM returned empty response for narrative generation."
        logger.error(error_msg)
        return {"episode_file_path": None, "error": error_msg}

    # 4. Save Episode
    # Generate filename (simple version)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe_trigger = "".join(
        c for c in trigger_event if c.isalnum() or c in (" ", "-")
    ).rstrip()
    safe_trigger = safe_trigger.replace(" ", "_")[:50]  # Limit length
    episode_filename = f"episode_{timestamp}_{safe_trigger}.md"
    episode_filepath = episode_dir / episode_filename

    try:
        episode_filepath.write_text(episode_text, encoding="utf-8")
        logger.info(f"Narrative episode saved successfully: {episode_filepath}")
        return {"episode_file_path": str(episode_filepath), "error": None}
    except Exception as e:
        error_msg = f"Failed to save narrative episode to {episode_filepath}: {e}"
        logger.error(error_msg, exc_info=True)
        # Return error but maybe keep the generated text?
        return {"episode_file_path": None, "error": error_msg}


# --- Capability Definition (for registration) --- #
NARRATIVE_GENERATE_CAPABILITY_ID = "narrative.generate.episode"
NARRATIVE_GENERATE_CAPABILITY_INFO = {
    "capability_id": NARRATIVE_GENERATE_CAPABILITY_ID,
    "capability_name": "Narrative Episode Generator",
    "description": "Generates a narrative episode summary based on project context (tasks, commits, logs) using an LLM.",
    "parameters": {
        "type": "object",
        "properties": {
            "trigger_event_summary": {
                "type": "string",
                "description": "Description of the main event triggering the narrative.",
            },
            "context_window": {
                "type": "object",
                "description": "Specifies the data scope (time range, task IDs, etc.). See ContextWindow type.",
                "properties": ContextWindow.__annotations__,
            },
            "style_prompt": {
                "type": "string",
                "description": "(Optional) Instructions for narrative tone/style.",
            },
        },
        "required": ["trigger_event_summary", "context_window"],
    },
    "input_schema": NarrativeGenerateInput.__annotations__,  # Approximate schema
    "output_schema": NarrativeGenerateOutput.__annotations__,  # Approximate schema
}
