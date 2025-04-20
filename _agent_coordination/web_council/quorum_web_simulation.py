# quorum_web_simulation.py

import asyncio
import os
import sys
from pathlib import Path
from jinja2 import Template
# Removed Playwright imports
# from playwright.async_api import async_playwright, BrowserContext
from typing import List, Optional
import logging
# Removed inspect import as it's no longer needed for debugging this issue

# --- Selenium Imports ---
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Explicitly add project root to path --- 
# PROJECT_ROOT = Path(__file__).resolve().parents[2] # No longer needed if running via main.py or structure assumes core is importable
# if str(PROJECT_ROOT) not in sys.path:
#     sys.path.insert(0, str(PROJECT_ROOT))
# --- End path addition ---

# Removed Playwright login utils import
# from core.login_utils import ensure_login

# Import UnifiedDriverManager from CORRECT path
try:
    # Adjust path based on actual location relative to project root
    from social.digital_dreamscape.dreamscape_generator.src.driver_manager_stub import UnifiedDriverManager
    # Also import the logger setup from the driver manager for consistency?
    # from social.digital_dreamscape.dreamscape_generator.src.driver_manager_stub import setup_logger
except ImportError as e:
    logging.error(f"CRITICAL: Failed to import UnifiedDriverManager. Check path. Error: {e}", exc_info=True)
    # Define a dummy class if import fails to prevent immediate crash
    class UnifiedDriverManager: pass

# -- Basic Logging Setup --
# Consider using the logger from the driver manager or a shared logging config
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# -- Inline Jinja prompt templates --
TEMPLATES = {
    "ChatGPT": Template("You are ChatGPT. Provide strategic insights on:\n\n{{ proposal }}"),
    "DeepSeq":  Template("You are DeepSeq. Retrieve context snippets for:\n\n{{ proposal }}"),
}

# -- Base web‑agent interface (Using Selenium) --
class WebAgent:
    # Takes manager now instead of service_name directly
    def __init__(self, name: str, url: str, prompt_sel: str, submit_sel: str, response_sel: str, manager: UnifiedDriverManager):
        self.name = name
        self.url = url
        self.prompt_sel = prompt_sel # CSS Selector for prompt input
        self.submit_sel = submit_sel # CSS Selector for submit button
        self.response_sel = response_sel # CSS Selector for response area
        self.manager = manager

    # Changed evaluate to accept driver, not context
    async def evaluate(self, proposal: str, driver) -> str: 
        prompt_text = TEMPLATES[self.name].render(proposal=proposal)
        try:
            logger.info(f"Agent {self.name}: Navigating to {self.url}")
            driver.get(self.url)
            await asyncio.sleep(2)

            # Check login state using manager, attempt login if needed
            logger.info(f"Agent {self.name}: Checking login state...")
            if not self.manager.is_logged_in():
                logger.warning(f"Agent {self.name}: Not logged in. Attempting automated login...")
                login_success = self.manager.perform_login() # Call the new login method
                if not login_success:
                    logger.error(f"Agent {self.name}: Automated login failed.")
                    return f"{self.name}: ERROR - Automated Login Failed"
                logger.info(f"Agent {self.name}: Automated login successful.")
            else:
                 logger.info(f"Agent {self.name}: Already logged in.")

            # Proceed with interaction using Selenium
            wait = WebDriverWait(driver, 30) # Selenium WebDriverWait

            logger.info(f"Agent {self.name}: Waiting for prompt element: {self.prompt_sel}")
            prompt_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.prompt_sel))
            )
            logger.info(f"Agent {self.name}: Filling prompt.")
            prompt_element.clear() # Clear field first
            prompt_element.send_keys(prompt_text)
            await asyncio.sleep(0.5)

            logger.info(f"Agent {self.name}: Clicking submit selector: {self.submit_sel}")
            submit_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.submit_sel))
            )
            # Scroll into view just in case
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            await asyncio.sleep(0.5)
            submit_button.click()

            # Wait for response stabilization (Simplified: wait for non-empty text)
            logger.info(f"Agent {self.name}: Waiting for response element: {self.response_sel}")
            response_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.response_sel))
            )
            
            # More robust wait: wait until the response element has some text content
            # and potentially wait until a known 'stop generating' element appears or disappears
            logger.info(f"Agent {self.name}: Waiting for response text to appear...")
            await asyncio.sleep(5) # Initial wait
            last_text = ""
            stable_count = 0
            max_stable = 3 # Require text to be stable for 3 checks (3*2=6 seconds)
            max_wait_time = 180 # Max total wait time
            start_wait = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_wait < max_wait_time:
                try:
                    # Re-find element each time
                    current_response_element = driver.find_element(By.CSS_SELECTOR, self.response_sel)
                    current_text = current_response_element.text.strip()
                    if current_text and current_text == last_text:
                        stable_count += 1
                        logger.debug(f"Response stable count: {stable_count}/{max_stable}")
                        if stable_count >= max_stable:
                             logger.info("Response stabilized.")
                             break
                    elif current_text:
                        stable_count = 0 # Reset counter if text changes or appears
                        last_text = current_text
                    # Else: Still empty, keep waiting
                    
                except NoSuchElementException:
                    # Response element might disappear and reappear, wait
                    stable_count = 0
                    pass 
                await asyncio.sleep(2) # Poll interval
            else:
                 logger.warning(f"Agent {self.name}: Response stabilization timed out or failed.")

            content = last_text # Use the last known stable text
            
            logger.info(f"Agent {self.name}: Evaluation complete.")
            return f"{self.name}: {content}"
        
        except TimeoutException as e:
            logger.error(f"Agent {self.name}: Timeout waiting for element: {e}", exc_info=False)
            return f"{self.name}: ERROR - TimeoutException: {e}"
        except NoSuchElementException as e:
             logger.error(f"Agent {self.name}: Element not found: {e}", exc_info=False)
             return f"{self.name}: ERROR - NoSuchElementException: {e}"
        except Exception as e:
            logger.error(f"Agent {self.name}: Error during evaluation: {e}", exc_info=True)
            return f"{self.name}: ERROR - {e}"

# -- Council manager --
class CouncilManager:
    def __init__(self, agents: List[WebAgent], manager: UnifiedDriverManager):
        self.agents = agents
        self.manager = manager

    async def propose(self, proposal: str) -> List[str]:
        driver = self.manager.get_driver()
        if not driver:
             logger.error("Failed to get WebDriver from manager.")
             return [f"{agent.name}: ERROR - WebDriver not available" for agent in self.agents]
        
        responses = []
        for agent in self.agents:
             # Ensure agent has access to the current driver instance
             response = await agent.evaluate(proposal, driver)
             responses.append(response)
             await asyncio.sleep(1) 
             
        return responses

# Removed Playwright get_browser_context

# Updated main to use UnifiedDriverManager
async def main(run_headless: bool):
    proposal = "Implement v3.0 ONNX vision detector"
    
    with UnifiedDriverManager(headless=run_headless) as manager:
        # Updated selectors based on common patterns / potential reality
        # These STILL might need adjustment based on actual site structure
        agents = [
            WebAgent(
                name="ChatGPT",
                url="https://chat.openai.com/", # Use base URL
                prompt_sel='textarea[id="prompt-textarea"]', # Try ID selector
                submit_sel='button[data-testid="send-button"]', 
                response_sel='div[class*="markdown prose"]', # More specific class
                manager=manager 
            ),
            WebAgent(
                name="DeepSeq",
                url="https://chat.deepseek.com/",
                prompt_sel="textarea[placeholder*='Message DeepSeek']", 
                submit_sel="button[data-testid*='send-button']", # Assuming similar test ID
                response_sel="div[class*='markdown']", # Keep general
                manager=manager 
            ),
        ]
        
        try:
            council = CouncilManager(agents, manager)
            responses = await council.propose(proposal)
        except Exception as e:
             logger.error(f"An error occurred during proposal evaluation: {e}", exc_info=True)
             responses = [f"Error evaluating {agent.name}: {e}" for agent in agents]

    logger.info(f"\n📜 Proposal:\n  {proposal}\n")
    logger.info("🤝 Council Web‑Scrape Responses:")
    for resp in responses:
        logger.info(f" - {resp}")

if __name__ == "__main__":
    is_headless = "--headless" in sys.argv
    asyncio.run(main(run_headless=is_headless)) 