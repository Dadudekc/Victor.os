# Placeholder for ContextManager logic
# Responsibilities:
# - Use MemoryManager to get current RPG state (skills, quests, etc.)
# - Use HistoryManager to get relevant recent history snippets
# - Assemble the final context dictionary needed by the Jinja2 template

import logging
from typing import Dict, Any, Optional, List

# Import necessary components
from .core.MemoryManager import MemoryManager
from .history_manager import HistoryManager
from dreamscape_generator import config as project_config

logger = logging.getLogger(__name__)
logger.setLevel(project_config.LOG_LEVEL)

class ContextManager:
    """Builds the context dictionary for Jinja2 prompt templates."""

    def __init__(self, memory_manager: MemoryManager, history_manager: Optional[HistoryManager] = None):
        # Make history_manager optional, as context might come directly from scraping
        if not isinstance(memory_manager, MemoryManager):
             raise TypeError("ContextManager requires a valid MemoryManager instance.")
        if history_manager and not isinstance(history_manager, HistoryManager):
             raise TypeError("ContextManager received an invalid HistoryManager instance.")

        self.memory_manager = memory_manager
        self.history_manager = history_manager # Can be None
        logger.info("ContextManager initialized.")

    def build_prompt_context(self,
                             history_file: Optional[str] = None,
                             history_query: Optional[str] = None,
                             scraped_messages: Optional[List[Dict[str, str]]] = None,
                             num_snippets: int = 20 # Number of messages/turns to use
                            ) -> Dict[str, Any]:
        """Constructs the context dictionary using memory and provided history/messages."""
        logger.debug(f"Building prompt context. History file: {history_file}, Query: {history_query}, Got Scraped: {scraped_messages is not None}")
        snippets_text = "[No history context provided]"
        try:
            # 1. Get current world state from MemoryManager
            current_world_state = self.memory_manager.get_current_state()

            # 2. Format history snippets from scraped messages or file
            if scraped_messages is not None:
                logger.info(f"Using {len(scraped_messages)} structured scraped messages for context.")
                # Take the last N turns
                start_index = max(0, len(scraped_messages) - num_snippets)
                relevant_turns = scraped_messages[start_index:]
                # Format into a readable string for the template
                formatted_lines = []
                for turn in relevant_turns:
                    role = turn.get('role', 'unknown').capitalize()
                    content = turn.get('content', '')
                    formatted_lines.append(f"{role}: {content}")
                snippets_text = "\n\n".join(formatted_lines) # Separate turns by double newline

            elif self.history_manager:
                # Fallback to using HistoryManager (which reads raw lines for now)
                logger.info("Using HistoryManager to get recent snippets (fallback)...")
                # This part might need adjustment if HistoryManager also returns structured data later
                snippets_text = self.history_manager.get_recent_snippets(
                    history_file=history_file,
                    query=history_query,
                    num_snippets=num_snippets * 2 # Get more lines if unstructured
                )
            else:
                 logger.warning("No scraped messages provided and no HistoryManager available.")

            # 3. Assemble the context dictionary
            context = {
                "username": project_config.USERNAME,
                "skills": current_world_state.get("skills", {}),
                "quests": current_world_state.get("quests", {}),
                "inventory": current_world_state.get("inventory", {}),
                "recent_snippets": snippets_text, # Use the formatted snippets
            }
            logger.info("Successfully built prompt context.")
            return context

        except Exception as e:
            logger.error(f"Error building prompt context: {e}", exc_info=True)
            # Return a minimal default context or raise the error?
            return { "username": project_config.USERNAME, "error": "Failed to build full context." }

__all__ = ["ContextManager"] 