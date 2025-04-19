# Placeholder for CLI logic
# Responsibilities:
# - Parse command-line arguments (using argparse?)
#   - Specify history source, model, output dir, etc.
# - Initialize necessary managers (MemoryManager, HistoryManager, etc.)
# - Instantiate and run StoryGenerator
# - Handle potential errors and user feedback

import logging
import argparse

# Import necessary components (will need real implementations)
from .core.MemoryManager import MemoryManager
# from .history_manager import HistoryManager
# from .context_manager import ContextManager
# from .experience_parser import ExperienceParser
from .story_generator import StoryGenerator
import config as project_config

# Setup basic logging for CLI
logging.basicConfig(level=project_config.LOG_LEVEL, format=project_config.LOG_FORMAT)
logger = logging.getLogger("cli")

def main():
    parser = argparse.ArgumentParser(description="Generate the next episode of your Developer Dreamscape RPG.")
    parser.add_argument("--history", help="Path to the history file/source to use for context.", default=None)
    parser.add_argument("--model", help="OpenAI model ID to use for generation.", default=project_config.OPENAI_MODEL)
    parser.add_argument("-o", "--output-dir", help="Directory to save generated episodes.", default=project_config.EPISODE_DIR)
    # Add more arguments as needed (e.g., --prompt-step, --temperature)

    args = parser.parse_args()

    logger.info("Starting Dev Dreamscape CLI...")
    logger.info(f"Using model: {args.model}") # TODO: Pass this model to StoryGenerator
    logger.info(f"History source: {args.history or 'Default (placeholder)'}")
    logger.info(f"Output directory: {args.output_dir}")

    try:
        # --- Initialization ---
        # TODO: Instantiate real HistoryManager, ContextManager, ExperienceParser
        # history_manager = HistoryManager(project_config.HISTORY_DIR)
        memory_manager = MemoryManager(project_config.MEMORY_DIR)
        # context_manager = ContextManager(memory_manager, history_manager)
        # experience_parser = ExperienceParser()

        # For now, StoryGenerator uses internal placeholders for missing managers
        story_generator = StoryGenerator(memory_manager=memory_manager)

        # --- Run Generation ---
        new_episode_path = story_generator.generate_next_episode(history_source=args.history)

        if new_episode_path:
            logger.info(f"Successfully generated episode: {new_episode_path}")
        else:
            logger.error("Episode generation failed.")
            # Exit with error code?

    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True)
        # Exit with error code?

    logger.info("Dev Dreamscape CLI finished.")

if __name__ == "__main__":
    main()

__all__ = ["main"] 