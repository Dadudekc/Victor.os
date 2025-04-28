# src/dreamos/automation/prompt_dispatcher.py
import time
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Attempt to import the scraper - adjust path if needed based on final structure
try:
    from dreamos.services.utils.chatgpt_scraper import ChatGPTScraper
    CHATGPT_SCRAPER_AVAILABLE = True
except ImportError:
    logging.error("ChatGPTScraper not found. Dispatcher cannot run.")
    ChatGPTScraper = None
    CHATGPT_SCRAPER_AVAILABLE = False

logger = logging.getLogger(__name__)

# --- Configuration ---
# Assumes AGENT_IDS are defined globally or loaded from config if needed elsewhere
# For simplicity, defining here, but should ideally be shared/loaded
AGENT_IDS = [f"agent_{i:02d}" for i in range(1, 9)]
DEFAULT_QUEUE_PATH = Path("runtime/cursor_queue")
DISPATCH_INTERVAL_SECONDS = 5

# --- Dispatcher Functions ---

def scrape_new_prompts(scraper_instance: ChatGPTScraper) -> List[str]:
    """Calls the ChatGPTScraper to fetch new messages/prompts."""
    if not scraper_instance:
        logger.warning("Scraper instance not available.")
        return []
    try:
        # Assuming fetch_new_messages() returns a list of strings
        # This might need adjustment based on the actual scraper's return type
        new_messages = scraper_instance.fetch_new_messages() # Or equivalent method
        if new_messages:
            logger.info(f"Scraped {len(new_messages)} new message(s)." )
            # Filter/process messages if needed - assuming they are direct prompts for now
            return [msg for msg in new_messages if isinstance(msg, str)]
        return []
    except AttributeError:
         logger.error(f"Scraper instance {type(scraper_instance)} missing expected method like 'fetch_new_messages'.")
         return []
    except Exception as e:
        logger.error(f"Error scraping ChatGPT: {e}", exc_info=True)
        return []

def route_prompt_to_agent(prompt_text: str) -> Optional[str]:
    """Determines the target agent ID based on simple routing rules."""
    if not AGENT_IDS:
        logger.error("No AGENT_IDS defined for routing.")
        return None

    prompt_lower = prompt_text.lower()
    # Simple keyword matching (agent ID mentioned in prompt)
    for agent_id in AGENT_IDS:
        if agent_id.replace('_', '') in prompt_lower or agent_id in prompt_lower:
            logger.debug(f"Routing prompt to {agent_id} based on keyword match.")
            return agent_id

    # Fallback: Random assignment
    chosen_agent = random.choice(AGENT_IDS)
    logger.debug(f"Routing prompt to {chosen_agent} via random fallback.")
    return chosen_agent

def save_prompt_to_queue(agent_id: str, prompt_text: str, queue_base: Path = DEFAULT_QUEUE_PATH):
    """Saves the prompt text to the specified agent's queue directory."""
    try:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f") # Added microseconds for uniqueness
        queue_dir = queue_base / agent_id
        queue_dir.mkdir(parents=True, exist_ok=True)
        # Use a unique filename
        prompt_filename = f"{timestamp}_prompt.txt"
        prompt_file = queue_dir / prompt_filename
        prompt_file.write_text(prompt_text, encoding="utf-8")
        logger.info(f"Saved prompt to queue: {prompt_file}")
    except Exception as e:
        logger.error(f"Failed to save prompt for {agent_id} to {queue_dir}: {e}", exc_info=True)

def run_dispatcher_loop(interval: int = DISPATCH_INTERVAL_SECONDS):
    """Continuously scrapes ChatGPT and dispatches prompts to agent queues."""
    if not CHATGPT_SCRAPER_AVAILABLE:
        logger.critical("ChatGPTScraper dependency not met. Dispatcher loop cannot start.")
        return

    # Initialize the scraper - This might require configuration (e.g., profile path)
    # Pass necessary config to ChatGPTScraper constructor if needed
    try:
        scraper = ChatGPTScraper() # Add arguments if constructor needs them
        logger.info("ChatGPT Scraper initialized for dispatcher loop.")
    except Exception as e:
        logger.critical(f"Failed to initialize ChatGPTScraper: {e}. Dispatcher loop cannot start.", exc_info=True)
        return

    logger.info(f"Starting Prompt Dispatcher loop (interval: {interval}s)... Press Ctrl+C to stop.")
    while True:
        try:
            new_prompts = scrape_new_prompts(scraper)
            if new_prompts:
                logger.info(f"Dispatching {len(new_prompts)} scraped prompts...")
                for prompt in new_prompts:
                    target_agent = route_prompt_to_agent(prompt)
                    if target_agent:
                        save_prompt_to_queue(target_agent, prompt)
                    else:
                        logger.warning(f"Could not route prompt, discarding: {prompt[:100]}...")
            else:
                logger.debug("No new prompts to dispatch this cycle.")

            time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Dispatcher loop stopped by user.")
            break
        except Exception as e:
            logger.error(f"Error in dispatcher loop: {e}. Pausing before retry...", exc_info=True)
            time.sleep(interval * 2) # Longer pause after error


if __name__ == '__main__':
    # Configure logging for direct script run
    log_format = "%(asctime)s - %(levelname)-8s - %(name)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format)

    # Example: Run the dispatcher loop directly
    # Note: Requires ChatGPTScraper to be configured and functional
    # Ensure Chrome profile/cookies are set up if needed by the scraper
    run_dispatcher_loop() 