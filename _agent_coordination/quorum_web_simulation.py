# quorum_web_simulation.py

import asyncio
import os
import sys
from pathlib import Path
import random # Added for delays
from jinja2 import Template
from typing import List, Optional
import logging
import asyncio.subprocess # <--- Add subprocess import

# --- Selenium Imports --- 
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys # <--- Import Keys

# -- Allow importing from the directory containing the real UnifiedDriverManager --
real_manager_dir = Path("D:/Dream.os/social/digital_dreamscape/dreamscape_generator/src")
if real_manager_dir.is_dir():
    if str(real_manager_dir) not in sys.path:
        sys.path.insert(0, str(real_manager_dir))
        print(f"Added {real_manager_dir} to sys.path for imports.", file=sys.stderr)
else:
    print(f"CRITICAL WARNING: Directory for UnifiedDriverManager ({real_manager_dir}) not found. Imports will fail.", file=sys.stderr)
# -- End Import Path Modification --

# Attempt to import the real UnifiedDriverManager and Locators
try:
    from unified_chrome_driver import UnifiedDriverManager, setup_logger 
    from chatgpt_locators import ChatGPTLocators # <--- Import Locators
    print("Successfully imported UnifiedDriverManager and ChatGPTLocators.", file=sys.stderr)
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
        prompt_text = prompt_text.replace('\n', ' ')
        try:
            logger.info(f"Agent {self.name}: Navigating to {self.url}")
            driver.get(self.url)
            await asyncio.sleep(1) # Short sleep after navigation

            # Assumes driver is already logged in by the manager
            wait = WebDriverWait(driver, 30)

            logger.info(f"Agent {self.name}: Waiting for prompt element: {self.prompt_sel}")
            prompt_element = wait.until(
                EC.element_to_be_clickable(self.prompt_sel)
            )
            logger.info(f"Agent {self.name}: Filling prompt.")
            prompt_element.click()
            prompt_element.clear()
            prompt_element.send_keys(prompt_text)
            prompt_element.send_keys(Keys.ENTER)

            logger.info(f"Agent {self.name}: Prompt submitted via Enter key. Waiting for response element: {self.response_sel}")
            response_element = wait.until(
                EC.presence_of_element_located(self.response_sel)
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
                    current_response_element = driver.find_element(*self.response_sel)
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

# -- Ollama CLI Agent --
class OllamaAgent:
    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model
        # Simple template lookup for Ollama, assuming similar persona needs
        # Could be made more specific if needed
        self.template = TEMPLATES.get(name.split()[0], Template("{{ proposal }}")) # Fallback to just proposal

    async def evaluate(self, proposal: str) -> str:
        prompt_text = self.template.render(proposal=proposal)
        prompt_text = prompt_text.replace('\n', ' ')
        command = ["ollama", "run", self.model, prompt_text]
        logger.info(f"Agent {self.name}: Running Ollama command: {' '.join(command[:3])} 'prompt...' ")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                response = stdout.decode('utf-8').strip()
                logger.info(f"Agent {self.name}: Evaluation complete.")
                return f"{self.name}: {response}"
            else:
                error_message = stderr.decode('utf-8').strip()
                logger.error(f"Agent {self.name}: Ollama CLI error (Code: {process.returncode}): {error_message}")
                return f"{self.name}: ERROR - Ollama CLI failed: {error_message}"
        except FileNotFoundError:
            logger.error(f"Agent {self.name}: Ollama command not found. Is Ollama installed and in PATH?")
            return f"{self.name}: ERROR - Ollama command not found."
        except Exception as e:
            logger.error(f"Agent {self.name}: Error running Ollama command: {e}", exc_info=True)
            return f"{self.name}: ERROR - {type(e).__name__}: {e}"

# -- Council manager --
class CouncilManager:
    def __init__(self, agents: List[WebAgent | OllamaAgent]): # Allow mixed agent types
        self.agents = agents

    async def propose(self, proposal: str, driver) -> List[str]: # Driver still needed for WebAgents
        if not driver and any(isinstance(agent, WebAgent) for agent in self.agents):
             logger.warning("WebDriver instance not provided, but WebAgents are present. WebAgents will fail.")
             # Don't return immediately, let Ollama agents run
        
        responses = []
        for agent in self.agents:
             logger.info(f"--- Starting evaluation for agent: {agent.name} ---")
             if isinstance(agent, WebAgent):
                 if driver:
                     response = await agent.evaluate(proposal, driver)
                 else:
                     response = f"{agent.name}: ERROR - WebDriver not available"
             elif isinstance(agent, OllamaAgent):
                 response = await agent.evaluate(proposal)
             else:
                 logger.warning(f"Unknown agent type: {type(agent)}. Skipping.")
                 response = f"{agent.name}: ERROR - Unknown agent type"
             
             responses.append(response)
             logger.info(f"--- Finished evaluation for agent: {agent.name} ---")
             await asyncio.sleep(random.uniform(1, 3))
             
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

            # ---> Restore interactive login check <--- 
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
                    prompt_sel=ChatGPTLocators.TEXT_INPUT_AREA, 
                    submit_sel=ChatGPTLocators.SEND_BUTTON, 
                    response_sel=ChatGPTLocators.ASSISTANT_MESSAGE_SELECTOR 
                ),
                OllamaAgent(
                    name="Ollama Mistral", # Update name to reflect model
                    model="mistral:latest" # Use an available model from ollama list
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

    logger.info(f"\nProposal:\n  {proposal}\n")
    logger.info("Council Web-Scrape Responses:")
    for resp in responses:
        logger.info(f" - {resp}")

if __name__ == "__main__":
    is_headless = "--headless" in sys.argv
    asyncio.run(main(run_headless=is_headless)) 
