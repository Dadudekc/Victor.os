import os
import json
import time
import logging
import shutil # Added import
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# import openai # Old import
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

# Use project config
from dreamscape_generator import config as project_config

# Import utilities
from .utils import sanitize_filename, save_episode_file

# Import implemented components
from .core.MemoryManager import MemoryManager
from .history_manager import HistoryManager # Import the real (stub) HistoryManager
from .context_manager import ContextManager # Import the real ContextManager
from .experience_parser import ExperienceParser # Import the real ExperienceParser
from .chatgpt_scraper import ChatGPTScraper # Keep if needed later
from .external_stubs import StubDiscordManager # Keep for notifications if needed

# Configure logging
logger = logging.getLogger("StoryGenerator")
logger.setLevel(project_config.LOG_LEVEL)

# --- Removed Placeholder Functions ---
# def load_history_snippets(...)
# def parse_llm_response(...)

class StoryGenerator:
    """Generates narrative episodes based on history and RPG state using LLMs."""

    def __init__(self,
                 memory_manager: MemoryManager,
                 # history_manager: HistoryManager, # No longer primary input
                 context_manager: ContextManager, # Require ContextManager
                 experience_parser: ExperienceParser, # Require ExperienceParser
                 chat_scraper: Optional[ChatGPTScraper] = None, # Added scraper
                 discord_manager: Optional[StubDiscordManager] = None):

        if not isinstance(memory_manager, MemoryManager):
            raise TypeError("StoryGenerator requires a valid MemoryManager instance.")
        # if not isinstance(history_manager, HistoryManager):
        #     raise TypeError("StoryGenerator requires a valid HistoryManager instance.")
        if not isinstance(context_manager, ContextManager):
            raise TypeError("StoryGenerator requires a valid ContextManager instance.")
        if not isinstance(experience_parser, ExperienceParser):
             raise TypeError("StoryGenerator requires a valid ExperienceParser instance.")
        # Scraper is optional for now, but required by generate_episodes_from_web
        if chat_scraper and not isinstance(chat_scraper, ChatGPTScraper):
             raise TypeError("Invalid ChatGPTScraper instance provided.")

        self.memory_manager = memory_manager
        # self.history_manager = history_manager # Remove direct use
        self.context_manager = context_manager
        self.experience_parser = experience_parser
        self.chat_scraper = chat_scraper # Store the scraper instance
        self.discord_manager = discord_manager

        # Initialize Jinja2 environment
        try:
            self.jinja_env = Environment(
                loader=FileSystemLoader(project_config.TEMPLATE_DIR),
                trim_blocks=True,
                lstrip_blocks=True
            )
            logger.info(f"Jinja2 environment loaded from: {project_config.TEMPLATE_DIR}")
        except Exception as e:
            logger.error(f"Failed to initialize Jinja2 Environment: {e}", exc_info=True)
            self.jinja_env = None

        self.episode_dir = project_config.EPISODE_DIR
        os.makedirs(self.episode_dir, exist_ok=True)

        logger.info("StoryGenerator initialized with required managers.")

    def _render_prompt(self, template_name: str = "episode_prompt.j2", context: Dict[str, Any] = None) -> str:
        """Renders the specified Jinja2 template with the given context."""
        if not self.jinja_env:
            logger.error("Cannot render prompt, Jinja2 environment not initialized.")
            raise RuntimeError("Jinja2 environment failed to initialize.")
        if context is None:
            context = {}
        try:
            template = self.jinja_env.get_template(template_name)
            rendered_prompt = template.render(context)
            logger.debug(f"Rendered prompt template '{template_name}'.")
            return rendered_prompt
        except TemplateNotFound:
             logger.error(f"Template '{template_name}' not found in {project_config.TEMPLATE_DIR}")
             raise
        except Exception as e:
            logger.error(f"Failed to render template '{template_name}': {e}", exc_info=True)
            raise

    def _call_llm(self, prompt: str, model: str, temperature: float, max_tokens: int) -> str:
        # Use ChatGPTScraper for web UI-based LLM calls
        if not self.chat_scraper:
            logger.error("ChatGPTScraper not provided. Cannot call LLM.")
            raise ValueError("ChatGPTScraper is not available.")
        logger.info(f"Calling web-scraped LLM ({model}) - Temp: {temperature}, Max Tokens: {max_tokens}")
        try:
            content = self.chat_scraper.send_prompt(prompt, model=model)
            logger.info("Web-scraped LLM response received.")
            return content
        except Exception as e:
            logger.error(f"Error during web-scraped LLM call: {e}", exc_info=True)
            raise

    def generate_episodes_from_web(self, model_override: Optional[str] = None) -> None:
        """Scrapes all chats from the web UI and generates an episode for each."""
        if not self.chat_scraper:
            logger.error("ChatGPTScraper not provided during initialization. Cannot generate from web.")
            return

        logger.info("--- Starting episode generation cycle from Web Scraper --- ")
        start_cycle_time = time.monotonic()
        processed_count = 0
        failed_count = 0

        # 1. Get list of chats from scraper
        try:
            logger.info("Retrieving chat list via scraper...")
            all_chats = self.chat_scraper.get_all_chat_titles()
            if not all_chats:
                 logger.warning("Scraper returned no chat titles.")
                 return
            logger.info(f"Found {len(all_chats)} chats via scraper.")
        except Exception as e:
            logger.error(f"Failed to get chat titles via scraper: {e}", exc_info=True)
            return

        # 2. Loop through each chat
        for chat_info in all_chats:
            chat_title = chat_info.get("title", "Untitled Chat")
            chat_link = chat_info.get("link")
            log_prefix = f"[Chat: {chat_title[:30]}...] ({os.path.basename(chat_link or 'no_link')})" # Add link basename for context
            logger.info(f"{log_prefix} Processing chat...")

            if not chat_link:
                logger.warning(f"{log_prefix} No link found. Skipping.")
                failed_count += 1
                continue

            # --- Generate single episode for this chat ---
            episode_filepath = self._generate_single_episode_from_scraped(
                chat_title=chat_title,
                chat_link=chat_link,
                model_override=model_override
            )

            if episode_filepath:
                 processed_count += 1
            else:
                 failed_count += 1
                 logger.error(f"{log_prefix} Failed to generate episode for this chat.")
            # Optional: Add a small delay between chats?
            # time.sleep(1)

        cycle_duration = time.monotonic() - start_cycle_time
        logger.info(f"--- Web generation cycle complete in {cycle_duration:.2f}s. Generated: {processed_count}, Failed: {failed_count} ---")

    def _generate_single_episode_from_scraped(self, chat_title: str, chat_link: str, model_override: Optional[str] = None) -> Optional[str]:
        """Generates a single episode based on scraped messages from a chat link."""
        start_time = time.monotonic()
        log_prefix = f"[Chat: {chat_title[:30]}...] ({os.path.basename(chat_link or 'no_link')})"
        episode_filepath = None
        # Determine consistent filename early
        sanitized_title = sanitize_filename(chat_title)
        episode_filename = f"{sanitized_title}.json" # Ensure consistent name

        try:
            # 1. Navigate and Scrape Messages
            logger.info(f"{log_prefix} Navigating to: {chat_link}")
            if not self.chat_scraper or not self.chat_scraper.safe_get(chat_link):
                 logger.error(f"{log_prefix} Failed to navigate to chat link (scraper missing or navigation failed).")
                 return None

            logger.info(f"{log_prefix} Scraping messages...")
            scraped_messages = self.chat_scraper.scrape_current_chat_messages()
            if not scraped_messages:
                 logger.warning(f"{log_prefix} No messages scraped from this chat.")
                 # For now, skip if no messages found.
                 return None
            logger.info(f"{log_prefix} Scraped {len(scraped_messages)} messages.")

            # 2. Build Context using scraped messages
            logger.debug(f"{log_prefix} Building context...")
            context = self.context_manager.build_prompt_context(scraped_messages=scraped_messages)
            if context.get("error"):
                 logger.error(f"{log_prefix} Failed to build context: {context.get('error')}")
                 return None

            # 3. Render Prompt
            logger.debug(f"{log_prefix} Rendering prompt...")
            prompt = self._render_prompt(context=context)

            # 4. Call LLM
            model_to_use = model_override or project_config.OPENAI_MODEL
            logger.debug(f"{log_prefix} Calling LLM ({model_to_use})...")
            llm_output = self._call_llm(
                prompt=prompt,
                model=model_to_use,
                temperature=project_config.GENERATION_TEMPERATURE,
                max_tokens=project_config.GENERATION_MAX_TOKENS
            )

            # 5. Parse Response
            logger.debug(f"{log_prefix} Parsing LLM response...")
            narrative, update_dict = self.experience_parser.parse(llm_output)
            if not narrative: # If parsing fails, narrative might be empty
                logger.warning(f"{log_prefix} Parsing resulted in empty narrative. Using full LLM output.")
                narrative = llm_output # Fallback

            # 6. Update Memory (if update exists)
            memory_updated = False
            if update_dict:
                logger.info(f"{log_prefix} Applying memory update...")
                try:
                    memory_updated = self.memory_manager.update_state(update_dict)
                    if memory_updated:
                         logger.info(f"{log_prefix} Memory updated successfully.")
                    else:
                         logger.info(f"{log_prefix} Memory update resulted in no changes.")
                except Exception as e:
                    logger.error(f"{log_prefix} Error applying memory update: {e}", exc_info=True)
                    # Continue to save episode even if memory update fails? Or abort?
                    # For now, let's still save the episode with the update_dict included.
            else:
                logger.info(f"{log_prefix} No memory update found in response.")

            # 7. Save Episode (uses consistent filename)
            logger.debug(f"{log_prefix} Saving episode...")
            metadata = {
                "source_type": "chatgpt_web_scrape",
                "chat_title": chat_title,
                "chat_link": chat_link,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "generation_model": model_to_use,
                "memory_updated": memory_updated, # Record if memory was changed
                "memory_version_after_update": self.memory_manager.get_full_state().get("version") if memory_updated else self.memory_manager.get_full_state().get("version") # Get current version
            }
            episode_filepath = save_episode_file(
                episode_dir=self.episode_dir, # Pass instance variable
                episode_filename=episode_filename,
                narrative=narrative,
                update_dict=update_dict,
                metadata=metadata
            )

            # (Optional) Discord Notification for success
            if episode_filepath and self.discord_manager:
                elapsed = time.monotonic() - start_time
                msg = f"Successfully generated episode '{episode_filename}' from chat '{chat_title}' in {elapsed:.2f}s. Memory updated: {memory_updated}."
                self.discord_manager.send_notification(msg)

        except Exception as e:
            logger.error(f"{log_prefix} Failed to generate episode: {e}", exc_info=True)
             # (Optional) Discord Notification for general failure
            if self.discord_manager:
                 self.discord_manager.send_notification(f"ERROR: Unexpected failure generating episode for chat '{chat_title}': {e}")
            return None # Abort for this chat on other errors

        finally:
            duration = time.monotonic() - start_time
            if episode_filepath:
                 logger.info(f"{log_prefix} Episode generation complete in {duration:.2f}s. Saved to: {episode_filepath}")
            else:
                 logger.warning(f"{log_prefix} Episode generation failed or skipped after {duration:.2f}s.")

        return episode_filepath # Return the path if successful

__all__ = ["StoryGenerator"] 
