"""
Thin adapters so the GUI can import:
    from dreamscape_generator.src import build_context, generate_episode
Uses ChatGPTScraper for web automation if available; otherwise raises.
"""
import logging
from pathlib import Path

# Import the new driver manager
from .core.UnifiedDriverManager import UnifiedDriverManager

# Still need the scraper class
from .chatgpt_scraper import ChatGPTScraper

# --------------------------------------------------------------------- #
# 1. build_context – naive version (reads memory json if present)       #
# --------------------------------------------------------------------- #
def build_context() -> dict:
    mem_path = Path("memory/episode_memory.json")
    if mem_path.exists():
        rendered = mem_path.read_text()
    else:
        rendered = "### Dreamscape Episode ###\n(No prior memory found.)"
    # Ensure the logs directory exists here too, in case build_context is called first
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    return {"rendered_prompt": rendered}

# --------------------------------------------------------------------- #
# 2. generate_episode – orchestrate one prompt cycle using UC driver  #
# --------------------------------------------------------------------- #
def generate_episode(prompt: str, model: str = "gpt-4o",
                     headless: bool = True, reverse: bool = False) -> str:
    logging.info("generate_episode() using model=%s headless=%s reverse=%s", model, headless, reverse)

    # --- Get the singleton driver manager instance --- 
    # Pass headless setting during initialization (only matters first time)
    # Subsequent calls will use existing instance
    try:
        # NOTE: Consider if headless should be updated dynamically via manager.update_options
        # For now, init uses the flag passed here if it's the first time.
        manager = UnifiedDriverManager(headless=headless)
    except Exception as init_err:
         logging.error(f"Failed to initialize UnifiedDriverManager: {init_err}", exc_info=True)
         return f"[ERROR] Failed to initialize driver manager: {init_err}"

    # --- Instantiate scraper with the manager --- 
    try:
        # The scraper will now get the driver from the manager
        scraper = ChatGPTScraper(manager=manager) 
    except Exception as scraper_err:
        logging.error(f"Failed to initialize ChatGPTScraper: {scraper_err}", exc_info=True)
        # Attempt cleanup? Manager might not have driver yet.
        manager.quit_driver() 
        return f"[ERROR] Failed to initialize scraper: {scraper_err}"

    output = "[ERROR] Placeholder - Scraper interaction failed"
    try:
        # --- Call the scraper's send_prompt method --- 
        # This method should now use the Selenium driver from the manager
        logging.info("Calling Selenium/UC-based scraper.send_prompt...")
        output = scraper.send_prompt(prompt, model=model, reverse=reverse)
        logging.info("scraper.send_prompt (Selenium/UC) call finished.")

    except Exception as e:
        # Catch potential errors from send_prompt itself
        logging.error(f"Error during generate_episode scraper interaction: {e}", exc_info=True)
        output = f"[ERROR] Generation failed: {e}"
    finally:
         # --- Driver cleanup is handled by the manager's __del__ or context manager ---
         # We might not need explicit quit here if manager is used elsewhere or 
         # if the whole process exits. Let's leave it out for now unless needed.
         # manager.quit_driver() 
         pass
    
    return output 