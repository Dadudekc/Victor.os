# scripts/dev/test_scraper_live_chat.py
import asyncio
import logging
import os
import time

# ADDED: Explicitly load .env file
from dotenv import load_dotenv
from selenium.webdriver.support import expected_conditions as EC

# Import necessary Selenium components if not already present
from selenium.webdriver.support.ui import WebDriverWait

# --- END Added imports ---
from src.dreamos.core.config import AppConfig
from src.dreamos.services.utils.chatgpt_scraper import (
    CHATGPT_URL,
    PROMPT_BOX,
    ChatGPTScraper,
)

# Explicitly load .env file from the current directory or parent directories
load_dotenv()

TEST_PROMPT = "Return the single word 'pong'."

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ScraperTest")


async def main():
    print("Script starting...")
    logger.info("Loading config using AppConfig.load()...")
    try:
        # REVERTED: Use AppConfig.load() again
        cfg = AppConfig.load()
        logger.info("Config loaded via AppConfig.")
    except Exception as e:
        logger.error(f"Failed to load AppConfig: {e}", exc_info=True)
        print("\nERROR: Failed to load configuration.")
        return

    # CRITICAL: Check credentials via loaded AppConfig
    logger.info("Checking credentials loaded in AppConfig...")
    scraper_cfg = getattr(cfg, "chatgpt_scraper", None)
    if not (scraper_cfg and scraper_cfg.email and scraper_cfg.password):
        # Get secrets safely for logging without revealing them if they exist partially
        email_present = bool(
            scraper_cfg and scraper_cfg.email and scraper_cfg.email.get_secret_value()
        )
        pass_present = bool(
            scraper_cfg
            and scraper_cfg.password
            and scraper_cfg.password.get_secret_value()
        )
        logger.error(
            f"AppConfig check failed: Email found: {email_present}, Password found: {pass_present}. Check .env file and AppConfig structure."
        )
        print(
            "\nERROR: Missing login credentials in loaded config. Check .env file is loaded and vars are correct."
        )
        return
    else:
        logger.info("Credentials successfully loaded into AppConfig.")

    logger.info("Starting scraper test...")
    scraper_instance = None
    try:
        logger.info(
            "Initializing scraper synchronously (sync init - needs update later)..."
        )
        # Initialize scraper - Still needs AppConfig integration in __init__
        # Passing cfg here assumes __init__ is updated, which it isn't yet.
        # Sticking to original init for now to test env loading first.
        scraper_instance = ChatGPTScraper(headless=False)
        logger.info("Setting up browser...")
        scraper_instance.setup_browser()

        logger.info("Browser setup complete. Pausing briefly before navigation...")
        time.sleep(3)

        logger.info(f"Attempting navigation to: {CHATGPT_URL}")
        scraper_instance.driver.get(CHATGPT_URL)
        logger.info("Navigation command sent. Attempting login/cookie load...")

        # Use scraper's load_cookies method (which should be sync for now)
        if not scraper_instance.load_cookies():
            logger.info(
                "Waiting 30s for manual login - Please login in the browser window!"
            )
            input("Press Enter after you have manually logged in...")
            logger.info("Checking login status after manual input...")
            try:
                WebDriverWait(scraper_instance.driver, 10).until(
                    EC.presence_of_element_located(PROMPT_BOX)
                )
                logger.info("Login appears successful after manual intervention.")
                scraper_instance.save_cookies()
            except:
                logger.error(
                    "Login still not detected after manual intervention. Aborting test."
                )
                return
        else:
            logger.info("Cookies loaded successfully. Refreshing page...")
            scraper_instance.driver.refresh()
            time.sleep(3)
            logger.info("Verifying login status after cookie load...")
            try:
                WebDriverWait(scraper_instance.driver, 10).until(
                    EC.presence_of_element_located(PROMPT_BOX)
                )
                logger.info("Login confirmed via cookies.")
            except:
                logger.error(
                    "Cookie-based login failed. Manual login might be required on next run. Aborting test."
                )
                return

        # Test steps using synchronous helper methods
        logger.info("Loading latest conversation...")
        scraper_instance.load_latest_conversation()
        logger.info("Scrolling to bottom...")
        scraper_instance.scroll_to_bottom()
        logger.info(f"Sending test prompt: {TEST_PROMPT}...")
        scraper_instance.send_message_and_wait(TEST_PROMPT)
        logger.info("Extracting reply...")
        reply = scraper_instance.extract_latest_reply()

        print("\n----------------------------")
        print(f"GPT says: >>>{reply}<<<")
        print("----------------------------")

        if "pong" in reply.lower():
            print("\n✅ Smoke Test Passed!")
        else:
            print(f"\n❌ Smoke Test Failed! Unexpected reply: {reply}")

    except Exception as e:
        logger.error(f"An error occurred during the test: {e}", exc_info=True)
        print(f"\n❌ Smoke Test Failed due to error: {e}")
    finally:
        if scraper_instance and scraper_instance.driver:
            logger.info("Cleaning up scraper...")
            scraper_instance.cleanup()


if __name__ == "__main__":
    # Note: Still running sync selenium methods inside asyncio.run() workaround
    asyncio.run(main())
