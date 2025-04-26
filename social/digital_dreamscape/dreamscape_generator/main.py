import logging
import os
import sys

# Ensure the src directory is in the path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import configuration and necessary components
import dreamos.config as config as project_config
from src.core.MemoryManager import MemoryManager
# Stubs are used implicitly by StoryGenerator for now
# from src.external_stubs import get_stubs
from src.story_generator import StoryGenerator

# Setup logging based on config
logging.basicConfig(level=project_config.LOG_LEVEL, format=project_config.LOG_FORMAT)
logger = logging.getLogger("main")

def run_generation():
    logger.info("--- Initializing Dev Dreamscape Generator --- ")

    try:
        # Initialize the Memory Manager
        memory_manager = MemoryManager(memory_dir=project_config.MEMORY_DIR)

        # Initialize other managers/stubs as needed
        # For now, StoryGenerator uses internal placeholders
        # scraper, discord_stub = get_stubs(project_config) # If using stubs directly

        # Initialize the Story Generator
        story_generator = StoryGenerator(
            memory_manager=memory_manager,
            # Pass stubs or real managers if needed
            # discord_manager=discord_stub
        )

        # --- Trigger Episode Generation ---
        # This is a basic run. The CLI (src/cli.py) provides more control.
        logger.info("--- Starting a single episode generation run --- ")
        episode_path = story_generator.generate_next_episode()

        if episode_path:
            logger.info(f"--- Episode generated successfully: {episode_path} ---")
        else:
            logger.error("--- Episode generation failed --- ")

    except Exception as e:
        logger.critical(f"--- An error occurred during initialization or generation: {e} ---", exc_info=True)
    finally:
        # Add cleanup if needed (e.g., shutting down scraper driver if used)
        # if scraper:
        #     scraper.shutdown_driver()
        logger.info("--- Dev Dreamscape Generator Finished --- ")

if __name__ == "__main__":
    run_generation() 
