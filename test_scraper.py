import logging
import time

# Assuming UnifiedDriverManager and ChatGPTScraper are accessible 
# via the project's structure when running from the root.
# Adjust imports if necessary based on how the project is structured for execution.
try:
    from social.digital_dreamscape.dreamscape_generator.src.core.UnifiedDriverManager import UnifiedDriverManager
    from social.digital_dreamscape.dreamscape_generator.src.chatgpt_scraper import ChatGPTScraper
except ImportError as e:
    print(f"Import Error: {e}")
    print("Please ensure you are running this script from the workspace root (D:\\Dream.os)")
    print("And that the required modules exist at the specified paths.")
    exit(1)

# Basic logging setup for the test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_scraper_test():
    logger.info("Starting scraper test...")
    
    # Initialize the driver manager (non-headless to observe)
    # It will use existing cookies/profile if available
    try:
        # Use context manager for cleanup
        # Get the manager instance (initial headless state might be ignored due to singleton)
        with UnifiedDriverManager(headless=True) as manager: 
            logger.info("Retrieved UnifiedDriverManager instance.")
            
            # ---> Explicitly update options to ensure headless mode for this test <--- 
            logger.info("Applying headless=True via update_options...")
            manager.update_options({"headless": True})
            logger.info("Options updated, driver will restart if needed.")

            # Initialize the scraper
            scraper = ChatGPTScraper(manager=manager)
            logger.info("ChatGPTScraper initialized.")

            # Test prompt
            test_prompt = "What is 2 + 2?"
            logger.info(f"Sending prompt: '{test_prompt}'")

            # Send the prompt and get the response
            # This will handle login checks/waits internally
            response = scraper.send_prompt(test_prompt)
            
            logger.info("--- Response Received ---")
            print(response)
            logger.info("--- End of Response ---")

            # Add a small delay before quitting to see the final state
            logger.info("Test finished. Closing browser shortly...")
            time.sleep(5) 
            
    except Exception as e:
        logger.error(f"An error occurred during the test: {e}", exc_info=True)
    finally:
        logger.info("Scraper test script finished.")


if __name__ == "__main__":
    run_scraper_test() 
