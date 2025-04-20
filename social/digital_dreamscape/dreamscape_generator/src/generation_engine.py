"""
Thin adapters so the GUI can import:
    from dreamscape_generator.src import build_context, generate_episode
Uses ChatGPTScraper for web automation if available; otherwise raises.
"""
import logging
from pathlib import Path

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
# 2. generate_episode – orchestrate one prompt cycle                    #
# --------------------------------------------------------------------- #
def generate_episode(prompt: str, model: str = "gpt-4o",
                     headless: bool = True, reverse: bool = False) -> str:
    logging.info("generate_episode() using model=%s headless=%s reverse=%s", model, headless, reverse)

    # --- Import ChatGPTScraper --- 
    try:
        # Scraper class now handles Playwright internally
        from .chatgpt_scraper import ChatGPTScraper
    except ImportError as e:
        raise RuntimeError("ChatGPTScraper not found; cannot send prompt") from e

    # Instantiate scraper (no driver options needed here now)
    scraper = ChatGPTScraper()
    output = "[ERROR] Placeholder - Scraper interaction failed"
    try:
        # --- Call the scraper's send_prompt method --- 
        # This method now uses Playwright and manages its own browser lifecycle.
        # It also handles the headless flag internally.
        # Login is currently assumed within send_prompt - add explicit login step if needed.
        logging.info("Calling Playwright-based scraper.send_prompt...")
        output = scraper.send_prompt(prompt, model=model, reverse=reverse, headless=headless)
        logging.info("scraper.send_prompt (Playwright) call finished.")

    except Exception as e:
        # Catch potential errors from send_prompt itself
        logging.error(f"Error during generate_episode scraper interaction: {e}", exc_info=True)
        output = f"[ERROR] Generation failed: {e}"
    # --- No finally/shutdown block needed, Playwright context manager handles it ---
    
    return output 