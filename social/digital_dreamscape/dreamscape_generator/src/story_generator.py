import os
import json
import time
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

import openai
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

# Use project config
import config as project_config

# Import the new MemoryManager and other core/external components
from .core.MemoryManager import MemoryManager
from .chatgpt_scraper import ChatGPTScraper # Assuming this is used for history eventually
# Placeholder imports for components to be built
# from .history_manager import HistoryManager
# from .context_manager import ContextManager
# from .experience_parser import ExperienceParser
from .external_stubs import StubDiscordManager # Keep for notifications if needed

# Configure logging
logger = logging.getLogger("StoryGenerator")
logger.setLevel(project_config.LOG_LEVEL)

# --- OpenAI API Key Setup ---
if not project_config.OPENAI_API_KEY or project_config.OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
    logger.warning("OpenAI API Key not set in config.py or environment variables. Story generation will fail.")
else:
    openai.api_key = project_config.OPENAI_API_KEY
    logger.info("OpenAI API Key configured for StoryGenerator.")

# --- Placeholder Functions (Replace with actual module implementations later) ---

def load_history_snippets(history_file: Optional[str] = None, num_snippets: int = 5) -> str:
    """Placeholder: Load relevant snippets from history files."""
    # TODO: Implement logic in history_manager.py to load and filter history
    logger.warning("Using placeholder function for loading history snippets.")
    if history_file and os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                # Crude example: take last N lines
                lines = f.readlines()
                return "\n".join(lines[-num_snippets:])
        except Exception as e:
            logger.error(f"Error reading history file {history_file}: {e}")
            return "[Error loading history]"
    return "Placeholder: User fixed a complex bug involving async database calls."

def parse_llm_response(llm_output: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Placeholder: Parse LLM output into narrative and EXPERIENCE_UPDATE dict."""
    # TODO: Implement robust parsing in experience_parser.py
    logger.warning("Using placeholder function for parsing LLM response.")
    narrative = llm_output
    update_dict = None
    try:
        # Simple regex assuming block is at the end
        match = re.search(r"EXPERIENCE_UPDATE:\s*(\{.*?\})$", llm_output, re.DOTALL | re.IGNORECASE)
        if match:
            json_str = match.group(1).strip()
            narrative = llm_output[:match.start()].strip()
            # Clean up potential preceding 'Narrative:' heading
            narrative = re.sub(r'^Narrative:\s*' ,'', narrative, flags=re.IGNORECASE).strip()
            try:
                update_dict = json.loads(json_str)
                logger.info("Successfully parsed EXPERIENCE_UPDATE block.")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse EXPERIENCE_UPDATE JSON: {e}")
                logger.debug(f"Invalid JSON string: {json_str}")
        else:
            logger.warning("EXPERIENCE_UPDATE block not found in the expected format.")
    except Exception as e:
        logger.error(f"Error parsing LLM response: {e}")

    return narrative, update_dict
# --- End Placeholder Functions ---

class StoryGenerator:
    """Generates narrative episodes based on history and RPG state using LLMs."""

    def __init__(self,
                 memory_manager: MemoryManager,
                 # Inject other managers later (HistoryManager, ContextManager, ExperienceParser)
                 # chat_scraper: Optional[ChatGPTScraper] = None, # If needed for direct history pull
                 discord_manager: Optional[StubDiscordManager] = None):

        if not isinstance(memory_manager, MemoryManager):
            raise TypeError("StoryGenerator requires a valid MemoryManager instance.")

        self.memory_manager = memory_manager
        self.discord_manager = discord_manager
        # self.chat_scraper = chat_scraper # Optional
        # self.history_manager = HistoryManager() # TODO: Instantiate real managers
        # self.context_manager = ContextManager(self.memory_manager, self.history_manager)
        # self.experience_parser = ExperienceParser()

        # Initialize Jinja2 environment
        try:
            self.jinja_env = Environment(
                loader=FileSystemLoader(project_config.TEMPLATE_DIR),
                trim_blocks=True,
                lstrip_blocks=True
            )
            logger.info(f"Jinja2 environment loaded from: {project_config.TEMPLATE_DIR}")
        except Exception as e:
            logger.error(f"Failed to initialize Jinja2 Environment: {e}")
            self.jinja_env = None

        self.episode_dir = project_config.EPISODE_DIR
        os.makedirs(self.episode_dir, exist_ok=True)

        logger.info("StoryGenerator initialized.")

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
        """Calls the specified OpenAI model with the given prompt."""
        if not openai.api_key:
             logger.error("OpenAI API Key not configured. Cannot call LLM.")
             raise ValueError("OpenAI API Key is not set.")

        logger.info(f"Calling LLM ({model}) - Temp: {temperature}, Max Tokens: {max_tokens}")
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content.strip()
            logger.info(f"LLM ({model}) response received.")
            logger.debug(f"LLM Response (preview): {content[:150]}...")
            return content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}", exc_info=True)
            raise # Re-raise the exception for the caller to handle

    def generate_next_episode(self, history_source: Optional[str] = None) -> Optional[str]:
        """Generates the next episode, updates memory, and saves the episode file."""
        start_time = time.monotonic()
        logger.info("Starting new episode generation...")

        try:
            # 1. Build Context (Use placeholders for now)
            logger.debug("Building context for prompt...")
            current_world_state = self.memory_manager.get_current_state()
            recent_snippets = load_history_snippets(history_source)
            context = {
                "username": project_config.USERNAME,
                "skills": current_world_state.get("skills", {}),
                "quests": current_world_state.get("quests", {}),
                "inventory": current_world_state.get("inventory", {}),
                "recent_snippets": recent_snippets,
                # Add any other necessary context variables
            }
            logger.info("Context built.")

            # 2. Render Prompt
            logger.debug("Rendering prompt...")
            prompt = self._render_prompt(context=context)
            logger.debug(f"Rendered Prompt (preview):\n{prompt[:300]}...")

            # 3. Call LLM
            llm_output = self._call_llm(
                prompt=prompt,
                model=project_config.OPENAI_MODEL, # Use configured model
                temperature=project_config.GENERATION_TEMPERATURE,
                max_tokens=project_config.GENERATION_MAX_TOKENS
            )

            # 4. Parse LLM Response (Use placeholder)
            logger.debug("Parsing LLM response...")
            narrative, experience_update = parse_llm_response(llm_output)
            if not narrative:
                logger.error("Failed to parse narrative from LLM output.")
                return None

            # 5. Update Memory State
            if experience_update:
                logger.debug("Updating memory state...")
                self.memory_manager.update_state(experience_update)
            else:
                logger.info("No experience update found in LLM response.")

            # 6. Archive/Save Episode
            episode_number = self._get_next_episode_number()
            timestamp_iso = datetime.now(timezone.utc).isoformat()
            episode_filename = f"episode_{episode_number:03d}.md"
            episode_filepath = os.path.join(self.episode_dir, episode_filename)

            logger.info(f"Saving episode {episode_number} to: {episode_filepath}")
            try:
                with open(episode_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# Episode {episode_number}\n\n")
                    f.write(f"**Generated:** {timestamp_iso}\n")
                    f.write(f"**Model Used:** {project_config.OPENAI_MODEL}\n\n")
                    f.write("## Narrative\n\n")
                    f.write(narrative)
                    f.write("\n\n")
                    # Include the raw update block for reference
                    if experience_update:
                        f.write("## Experience Update Applied\n\n```json\n")
                        json.dump(experience_update, f, indent=2)
                        f.write("\n```\n")
                    else:
                        f.write("_(No experience update block detected)_\n")

                logger.info(f"✅ Episode {episode_number} saved successfully.")

                # 7. Optional: Discord Notification
                if self.discord_manager:
                    try:
                        message = f"📜 **New Dev Dreamscape Episode!**\n**Episode {episode_number}** generated using {project_config.OPENAI_MODEL}.\n*Narrative Preview:* {narrative[:200]}..."
                        # Assuming send_message exists on the stub/real manager
                        self.discord_manager.send_message(message)
                        logger.info("Sent Discord notification for new episode.")
                    except Exception as e:
                        logger.error(f"Failed to send Discord notification: {e}")

                duration = time.monotonic() - start_time
                logger.info(f"Episode generation finished in {duration:.2f} seconds.")
                return episode_filepath # Return path to the new episode

            except Exception as e:
                logger.error(f"Failed to write episode file {episode_filepath}: {e}", exc_info=True)
                return None

        except Exception as e:
            logger.error(f"Episode generation failed: {e}", exc_info=True)
            return None

    def _get_next_episode_number(self) -> int:
        """Determines the next episode number based on files in the episode directory."""
        try:
            max_num = 0
            pattern = re.compile(r"episode_(\d+)\.md")
            for filename in os.listdir(self.episode_dir):
                match = pattern.match(filename)
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
            return max_num + 1
        except Exception as e:
            logger.error(f"Error determining next episode number: {e}. Defaulting to 1.")
            return 1

__all__ = ["StoryGenerator"] 