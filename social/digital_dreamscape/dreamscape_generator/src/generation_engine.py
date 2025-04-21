"""
Thin adapters so the GUI can import:
    from dreamscape_generator.src import build_context, generate_episode
Uses ChatGPTScraper for web automation if available; otherwise raises.
"""
import logging
from pathlib import Path
from typing import Optional

# --- Import Memory Manager --- 
# Assume memory_manager.py is accessible (e.g., in the same dir or python path)
# This import might fail if structure is different
try:
    from memory_manager import UnifiedMemoryManager
except ImportError:
    UnifiedMemoryManager = None # Define as None if import fails
# ---------------------------

# --- Initialize logger for this module --- 
logger = logging.getLogger(__name__)
# ----------------------------------------

# --- Imports moved inside generate_episode ---
# from .core.UnifiedDriverManager import UnifiedDriverManager
# from .chatgpt_scraper import ChatGPTScraper
# --------------------------------------------

# --------------------------------------------------------------------- #
# 1. build_context – Now uses Memory Manager                          #
# --------------------------------------------------------------------- #
def build_context(prompt: str, reverse_flag: bool, mem_manager: Optional[UnifiedMemoryManager]) -> dict:
    # Log received arguments 
    logging.info(f"build_context called with prompt (len={len(prompt)}) and reverse_flag={reverse_flag}")
    
    memory_content = "### Dreamscape Episode ###\n(No prior memory found - Memory Manager unavailable or key missing)"
    if mem_manager:
        # --- Fetch context from Memory Manager --- 
        # Example: Get the last saved episode from the 'context' segment
        retrieved_memory = mem_manager.get(key="last_episode", segment="context", default=None)
        if isinstance(retrieved_memory, str) and retrieved_memory:
            memory_content = retrieved_memory
            logging.info(f"Retrieved last episode context from memory ({len(memory_content)} chars).")
        else:
            logging.info("No 'last_episode' found in memory context segment, using default.")
        # ---------------------------------------
    else:
         logging.warning("Memory manager instance not provided to build_context.")

    # --- Combine memory and user prompt --- 
    # --- Try Instruction First Structure --- 
    rendered = (
        f"USER INSTRUCTION:\n{prompt}\n\n"
        f"BACKGROUND CONTEXT (for reference):\n---\n{memory_content}\n---"
    )
    # -------------------------------------

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

    # --- Lazy import Manager and Scraper --- 
    try:
        from .core.UnifiedDriverManager import UnifiedDriverManager
        from .chatgpt_scraper import ChatGPTScraper
        logging.debug("UnifiedDriverManager and ChatGPTScraper imported successfully.")
    except ImportError as import_err:
        logging.error(f"Failed to import backend components: {import_err}", exc_info=True)
        return f"[ERROR] Failed backend import: {import_err}"
    # ---------------------------------------

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
         # pass
         # --- Explicitly quit the driver managed by the singleton --- 
         if 'manager' in locals() and manager: # Check if manager was initialized
             # Use logging module directly here to avoid potential NameError in child process scope
             logging.info("Ensuring driver cleanup in generate_episode finally block...")
             manager.quit_driver() 
         # -------------------------------------------------------------
    
    return output 