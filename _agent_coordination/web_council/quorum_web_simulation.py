# quorum_web_simulation.py

import asyncio
import os
import sys # Import sys
from pathlib import Path # Import Path
from jinja2 import Template
from playwright.async_api import async_playwright, BrowserContext, Page
from typing import List, Optional
import logging
import inspect # Import inspect module

# --- Explicitly add project root to path --- 
PROJECT_ROOT = Path(__file__).resolve().parents[2] # Go up two levels from _agent_coordination/web_council
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT)) # Insert at beginning
# --- End path addition ---

# -- Allow importing from workspace root (D:\15mins) --
workspace_root_for_imports = Path("D:/15mins") # Use forward slashes
if workspace_root_for_imports.is_dir():
    if str(workspace_root_for_imports) not in sys.path:
        sys.path.insert(0, str(workspace_root_for_imports))
        print(f"Added {workspace_root_for_imports} to sys.path for imports.", file=sys.stderr)
else:
    print(f"Warning: Workspace root {workspace_root_for_imports} not found. Imports from 'core' might fail.", file=sys.stderr)
# -- End Import Path Modification --

# -- Basic Logging Setup --
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler() # Ensure output goes to stderr/stdout
    ]
)
logger = logging.getLogger(__name__) # Get root logger or specific one

# Use absolute import now that path is set
from core.login_utils import ensure_login

# -- Inline Jinja prompt templates --
TEMPLATES = {
    "ChatGPT": Template("You are ChatGPT. Provide strategic insights on:\n\n{{ proposal }}"),
    "DeepSeek":  Template("You are DeepSeek. Retrieve context snippets for:\n\n{{ proposal }}"),
}

# --- REMOVED Local Login Functions --- 
# (login_chatgpt and login_deepseek functions deleted)

# -- Base web‑agent interface --
class WebAgent:
    def __init__(self, name: str, url: str, prompt_sel: str, submit_sel: str, response_sel: str, service_name: str):
        self.name = name
        self.url = url
        self.prompt_sel = prompt_sel
        self.submit_sel = submit_sel
        self.response_sel = response_sel
        self.service_name = service_name # Store service name

    async def evaluate(self, proposal: str, context: BrowserContext) -> str:
        prompt_text = TEMPLATES[self.name].render(proposal=proposal)
        page = await context.new_page()
        login_success = True # Assume logged in initially
        try:
            logger.info(f"Agent {self.name}: Navigating to {self.url}")
            await page.goto(self.url, timeout=90000, wait_until='domcontentloaded')

            # Check login status and attempt login using centralized function
            logger.info(f"Agent {self.name}: Ensuring login for service '{self.service_name}'...")
            # Correct keyword argument to match dummy function if import failed
            login_success = await ensure_login(page, service_name=self.service_name) 

            if not login_success:
                 # Log error from dummy function will explain this
                 raise Exception(f"Login failed or required but could not be completed for {self.name} ({self.service_name})")

            # Now proceed with evaluation 
            logger.info(f"Agent {self.name}: Waiting for prompt selector: {self.prompt_sel}")
            await page.wait_for_selector(self.prompt_sel, timeout=90000)
            logger.info(f"Agent {self.name}: Filling prompt.")
            await page.fill(self.prompt_sel, prompt_text)

            # Submit logic - Always clicks submit_sel now
            logger.info(f"Agent {self.name}: Clicking submit selector: {self.submit_sel}")
            # Ensure the button is actually clickable/visible before clicking
            submit_button = page.locator(self.submit_sel)
            await submit_button.wait_for(state="visible", timeout=10000) # Wait max 10s for button
            await submit_button.click()

            logger.info(f"Agent {self.name}: Waiting for response selector: {self.response_sel}")
            await page.wait_for_selector(self.response_sel, timeout=180000)
            
            # Specific handling for DeepSeek: Wait for typing indicator to disappear
            if self.name == "DeepSeek":
                typing_indicator_sel = "div[class*='typing-indicator']" # Selector provided by user
                logger.info(f"Agent {self.name}: Waiting for typing indicator ({typing_indicator_sel}) to disappear...")
                try:
                    await page.wait_for_selector(typing_indicator_sel, state='hidden', timeout=180000) # Wait up to 3 mins for typing to finish
                    logger.info(f"Agent {self.name}: Typing indicator disappeared.")
                except Exception as e:
                    # Timeout waiting for indicator to disappear, assume response might be complete anyway
                    logger.warning(f"Agent {self.name}: Timed out waiting for typing indicator to disappear, proceeding to extract text. Error: {e}") 
            
            # Optional: Add a small consistent delay
            await asyncio.sleep(2)
            
            logger.info(f"Agent {self.name}: Extracting response content from {self.response_sel}.")
            content = await page.inner_text(self.response_sel)
            logger.info(f"Agent {self.name}: Evaluation complete.")
            return f"{self.name}: {content.strip()}"
        except Exception as e:
            logger.error(f"Agent {self.name}: Error during evaluation: {e}", exc_info=True)
            # Optionally capture a screenshot on error
            # screenshot_path = f"{self.name}_error.png"
            # await page.screenshot(path=screenshot_path)
            # logger.info(f"Agent {self.name}: Screenshot saved to {screenshot_path}")
            return f"{self.name}: ERROR - {e}"
        finally:
            # Ensure page is closed even if errors occur
            if page and not page.is_closed():
                await page.close()
                logger.info(f"Agent {self.name}: Page closed.")

# -- Council manager to run all agents --
class CouncilManager:
    def __init__(self, agents: List[WebAgent]):
        self.agents = agents

    async def propose(self, proposal: str, context: BrowserContext) -> List[str]:
        tasks = [agent.evaluate(proposal, context) for agent in self.agents]
        return await asyncio.gather(*tasks)

# Modified get_browser_context to always run headless
async def get_browser_context(playwright, user_data_dir_path: str) -> BrowserContext:
    """Return a BrowserContext using a persistent user data directory, always headless."""
    
    # No more first run / headful logic needed
    print(f"✅ Launching headless browser with user data dir: {user_data_dir_path}")
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir_path,
        headless=True,
    )
    return context

async def main():
    proposal = "Implement v3.0 ONNX vision detector"
    agents = [
        WebAgent(
            name="ChatGPT",
            url="https://chat.openai.com/chat",
            prompt_sel='p[data-placeholder="Ask anything"]',
            submit_sel='#composer-submit-button',
            response_sel="div.prose",
            service_name="chatgpt" # ADDED service_name
        ),
        WebAgent(
            name="DeepSeek",
            url="https://chat.deepseek.com/",
            prompt_sel="textarea[placeholder*='Message DeepSeek']",
            submit_sel="button[data-testid*='send-button']",
            response_sel="div[class*='message-container']:last-child div[class*='markdown']",
            service_name="deepseek" # ADDED service_name
        ),
    ]

    # Use a dedicated directory for user data persistence
    user_data_directory = "council_user_data"
    if not os.path.exists(user_data_directory):
        os.makedirs(user_data_directory)
        print(f"Created user data directory: {user_data_directory}")

    async with async_playwright() as p:
        # Pass the user data directory path
        context = await get_browser_context(p, user_data_directory)
        
        # Check if context is valid before proceeding
        if context is None:
             print("Error: Failed to obtain browser context.")
             return
             
        try:
            council = CouncilManager(agents)
            responses = await council.propose(proposal, context)
        except Exception as e:
             print(f"An error occurred during proposal evaluation: {e}")
             responses = [f"Error evaluating {agent.name}: {e}" for agent in agents]
        finally:
            # Ensure context is closed
            if context:
                 await context.close()
                 print("Browser context closed.")

    print(f"\n📜 Proposal:\n  {proposal}\n")
    print("🤝 Council Web‑Scrape Responses:")
    for resp in responses:
        print(f" - {resp}")

if __name__ == "__main__":
    asyncio.run(main()) 