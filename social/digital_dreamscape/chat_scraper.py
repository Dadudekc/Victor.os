from dreamscape_generator.src import generate_episode # Use the re-exported function
from utils import log_event
import logging, threading

def process_all_chats(prompt: str, *, model: str, headless=True, reverse=False):
    """Stub for processing all chats - currently just runs one generation."""
    logging.info(f"Starting Process-All-Chats stub (runs single generation) with model={model}, headless={headless}, reverse={reverse}...")
    # TODO: Implement actual chat fetching/looping logic here
    # For now, it just calls the standard single-episode generation
    try:
        content = generate_episode(
            prompt, model=model, headless=headless, reverse=reverse
        )
        log_event("ALL_CHATS_COMPLETE", "ChatScraper", {"bytes": len(content)})
        logging.info("Process-All-Chats stub finished.")
        return content
    except Exception as e:
        logging.error(f"Error during Process-All-Chats stub: {e}", exc_info=True)
        log_event("ALL_CHATS_ERROR", "ChatScraper", {"error": str(e)})
        return f"[ERROR] Process-All-Chats failed: {e}" 
