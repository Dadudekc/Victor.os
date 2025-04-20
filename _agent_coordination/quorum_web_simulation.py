# quorum_web_simulation.py

import asyncio
import os
import sys
from pathlib import Path
import random # Added for delays
from jinja2 import Template
from typing import List, Optional
import logging

# --- Selenium Imports --- 
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -- Allow importing from the directory containing the real UnifiedDriverManager --
real_manager_dir = Path("D:/Dream.os/social/digital_dreamscape/dreamscape_generator/src")
if real_manager_dir.is_dir():
    if str(real_manager_dir) not in sys.path:
        sys.path.insert(0, str(real_manager_dir))
        print(f"Added {real_manager_dir} to sys.path for imports.", file=sys.stderr)
else:
    print(f"CRITICAL WARNING: Directory for UnifiedDriverManager ({real_manager_dir}) not found. Imports will fail.", file=sys.stderr)
# -- End Import Path Modification --

# Attempt to import the real UnifiedDriverManager
try:
    from unified_chrome_driver import UnifiedDriverManager, setup_logger # Import setup_logger too if needed
    print("Successfully imported UnifiedDriverManager from unified_chrome_driver.", file=sys.stderr)
    # Setup logger using the manager's setup function
    logger = setup_logger(name="QuorumWebSim")
except ImportError as e:
    # Fallback logging if setup_logger fails or manager doesn't import
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger = logging.getLogger("QuorumWebSim_Fallback")
    logger.error(f"CRITICAL: Failed to import UnifiedDriverManager or setup_logger. Check path and file existence. Error: {e}", exc_info=True)
    # Exit or define a very basic dummy to prevent downstream crashes? Exit might be safer.
    sys.exit("Failed to load critical UnifiedDriverManager component.") 

# -- Inline Jinja prompt templates --
TEMPLATES = {
    "ChatGPT": Template("You are ChatGPT. Provide strategic insights on:\n\n{{ proposal }}"),
    "DeepSeq":  Template("You are DeepSeq. Retrieve context snippets for:\n\n{{ proposal }}"),
}

# -- Base web‑agent interface (Using Selenium) --
class WebAgent:
    # Removed manager from init
    def __init__(self, name: str, url: str, prompt_sel: str, submit_sel: str, response_sel: str):
        self.name = name
        self.url = url
        self.prompt_sel = prompt_sel
        self.submit_sel = submit_sel
        self.response_sel = response_sel

    # Evaluate expects a ready driver (logged in)
    async def evaluate(self, proposal: str, driver) -> str: 
        prompt_text = TEMPLATES[self.name].render(proposal=proposal)
        try:
            logger.info(f"Agent {self.name}: Navigating to {self.url}")
            driver.get(self.url)
            await asyncio.sleep(1) # Short sleep after navigation

            # Assumes driver is already logged in by the manager
            wait = WebDriverWait(driver, 30)

            logger.info(f"Agent {self.name}: Waiting for prompt element: {self.prompt_sel}")
            prompt_element = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.prompt_sel)) # Wait for clickable
            )
            logger.info(f"Agent {self.name}: Filling prompt.")
            prompt_element.clear()
            prompt_element.send_keys(prompt_text)
            await asyncio.sleep(0.5)

            logger.info(f"Agent {self.name}: Clicking submit selector: {self.submit_sel}")
            submit_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.submit_sel))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            await asyncio.sleep(0.5)
            submit_button.click()

            logger.info(f"Agent {self.name}: Waiting for response element: {self.response_sel}")
            response_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.response_sel))
            )
            
            logger.info(f"Agent {self.name}: Waiting for response text to appear/stabilize...")
            await asyncio.sleep(5) 
            last_text = ""
            stable_count = 0
            max_stable = 3 
            max_wait_time = 180 
            start_wait = asyncio.get_event_loop().time()
            content = "" # Initialize content
            while asyncio.get_event_loop().time() - start_wait < max_wait_time:
                try:
                    current_response_element = driver.find_element(By.CSS_SELECTOR, self.response_sel)
                    current_text = current_response_element.text.strip()
                    content = current_text 
                    if current_text and current_text == last_text:
                        stable_count += 1
                        if stable_count >= max_stable:
                             logger.info("Response stabilized.")
                             break
                    elif current_text:
                        stable_count = 0 
                        last_text = current_text
                except NoSuchElementException:
                    stable_count = 0
                    pass 
                await asyncio.sleep(2) 
            else:
                 logger.warning(f"Agent {self.name}: Response stabilization timed out. Returning last seen text.")

            logger.info(f"Agent {self.name}: Evaluation complete.")
            return f"{self.name}: {content}"
        
        except TimeoutException as e:
            logger.error(f"Agent {self.name}: Timeout waiting for element: {e}", exc_info=False)
            return f"{self.name}: ERROR - TimeoutException: Check selectors/page load."
        except NoSuchElementException as e:
             logger.error(f"Agent {self.name}: Element not found: {e}", exc_info=False)
             return f"{self.name}: ERROR - NoSuchElementException: Check selectors."
        except Exception as e:
            logger.error(f"Agent {self.name}: Error during evaluation: {e}", exc_info=True)
            return f"{self.name}: ERROR - {type(e).__name__}: {e}"

# -- Council manager --
class CouncilManager:
    # Removed manager from init
    def __init__(self, agents: List[WebAgent]):
        self.agents = agents
        # self.manager = manager # Removed

    # Propose now takes driver
    async def propose(self, proposal: str, driver) -> List[str]:
        # driver = self.manager.get_driver() # Removed
        if not driver:
             logger.error("WebDriver instance not provided to propose method.")
             return [f"{agent.name}: ERROR - WebDriver not available" for agent in self.agents]
        
        responses = []
        # Run evaluations sequentially with Selenium driver
        for agent in self.agents:
             logger.info(f"--- Starting evaluation for agent: {agent.name} ---")
             response = await agent.evaluate(proposal, driver)
             responses.append(response)
             logger.info(f"--- Finished evaluation for agent: {agent.name} ---")
             await asyncio.sleep(random.uniform(1, 3)) # Delay between agents
             
        return responses

# Removed Playwright get_browser_context

# Updated main to use the real UnifiedDriverManager
async def main(run_headless: bool):
    proposal = "Implement v3.0 ONNX vision detector"
    responses = [] # Initialize responses
    
    # --- Use UnifiedDriverManager as context manager --- 
    try:
        # Configure manager: use persistent profile if not headless
        profile_path = os.path.join(os.getcwd(), "chrome_profile", "council") if not run_headless else None
        cookie_path = os.path.join(os.getcwd(), "cookies", "council_cookies.pkl") if not run_headless else None
        
        logger.info(f"Initializing UnifiedDriverManager (Headless: {run_headless})")
        with UnifiedDriverManager(headless=run_headless, profile_dir=profile_path, cookie_file=cookie_path) as manager:
            logger.info("Getting WebDriver...")
            driver = manager.get_driver()
            if not driver:
                 raise Exception("Failed to initialize WebDriver from UnifiedDriverManager")

            # Handle login/cookies (only really makes sense for non-headless)
            if not run_headless:
                 logger.info("Attempting to load cookies...")
                 loaded = manager.load_cookies() 
                 if loaded and manager.is_logged_in():
                     logger.info("Cookie load successful and login verified.")
                 else:
                     logger.warning("Cookie load failed or login not verified. Manual login might be required.")
                     # Go to login page and wait for manual intervention
                     driver.get(manager.CHATGPT_URL) # Go to a known site
                     input(f"ACTION REQUIRED: Please log in manually in the browser, then press ENTER here to continue and save cookies...\n(Profile: {profile_path}, Cookies: {cookie_path})\n")
                     manager.save_cookies()
                     if not manager.is_logged_in():
                          logger.error("Manual login attempt failed or was not completed correctly.")
                          # Decide whether to raise error or continue without login?
                          # raise Exception("Manual login failed.")
                     else:
                          logger.info("Login confirmed after manual intervention.")
            else:
                 logger.info("Running headless, skipping interactive cookie/login check.")
                 # Headless assumes clean state or correct automated login if manager supported it

            # --- Setup Agents and Council --- 
            logger.info("Setting up agents...")
            agents = [
                WebAgent(
                    name="ChatGPT",
                    url="https://chat.openai.com/",
                    prompt_sel='textarea[id="prompt-textarea"]', 
                    submit_sel='button[data-testid="send-button"]', 
                    response_sel='div[class*="markdown prose"]'
                    # Removed manager=manager 
                ),
                WebAgent(
                    name="DeepSeq",
                    url="https://chat.deepseek.com/",
                    prompt_sel="textarea[placeholder*='Message DeepSeek']", 
                    submit_sel="button[data-testid*='send-button']",
                    response_sel="div[class*='markdown']" 
                    # Removed manager=manager 
                ),
            ]
            
            council = CouncilManager(agents)
            logger.info(f"Executing proposal: {proposal}")
            responses = await council.propose(proposal, driver)
    
    except ImportError as e:
         # Handle case where UnifiedDriverManager failed to import initially
         logger.critical(f"ImportError encountered: {e}. Cannot proceed.")
         responses = [f"CRITICAL ERROR: Failed to load UnifiedDriverManager: {e}"]
    except Exception as e:
         logger.error(f"An error occurred during the main process: {e}", exc_info=True)
         responses = [f"Error during main execution: {e}"]
    # Manager cleanup is handled by the `with` statement (__exit__)

    logger.info(f"\n📜 Proposal:\n  {proposal}\n")
    logger.info("🤝 Council Web‑Scrape Responses:")
    for resp in responses:
        logger.info(f" - {resp}")

if __name__ == "__main__":
    is_headless = "--headless" in sys.argv
    asyncio.run(main(run_headless=is_headless)) 