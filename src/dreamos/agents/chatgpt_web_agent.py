# chatgpt_web_agent.py
"""
Defines the ChatGPTWebAgent, an agent responsible for interacting with a 
ChatGPT conversation via a web browser. It can scrape responses, inject prompts/
results, and manage tasks using TaskNexus. Includes optional PyAutoGUI for GUI 
automation and a simulation mode.
"""

import json
import logging
import time
import asyncio
from pathlib import Path
from typing import Dict

from dreamos.core.config import AppConfig
from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.core.tasks.nexus.task_nexus import TaskNexus
from dreamos.utils.dream_mode_utils.html_parser import extract_latest_reply
from dreamos.utils.dream_mode_utils.task_parser import extract_task_metadata
from dreamos.utils.gui_utils import (
    close_browser,
    launch_browser,
    navigate_to_page,
    wait_for_login,
    is_window_focused,
    wait_for_element,
    PYAUTOGUI_AVAILABLE
)

if PYAUTOGUI_AVAILABLE:
    import pyautogui
    # Attempt to import pygetwindow for window activation, fail gracefully
    try:
        import pygetwindow
    except ImportError:
        pygetwindow = None
        logger.info("pygetwindow not found, window activation capabilities will be limited.")
else:
    pyautogui = None
    pygetwindow = None

logger = logging.getLogger("ChatGPTWebAgent")
logger.setLevel(logging.INFO)

DEFAULT_INTERVAL = 10  # seconds between scrape attempts
# AGENT_SCRIPT_DIR = Path(__file__).parent # Not needed if paths come from config
# INBOX_ROOT = AGENT_SCRIPT_DIR.parent / "inbox" # Define path relative to configured paths  # noqa: E501


class ChatGPTWebAgent:
    def __init__(
        self,
        config: AppConfig,
        agent_id: str,
        conversation_url: str,
        task_nexus: TaskNexus,
        simulate: bool = False,
    ):
        """
        Initializes the ChatGPT Web Agent.

        Args:
            config: The central application configuration object.
            agent_id: The unique ID for this agent instance (e.g., specific conversation ID).
            conversation_url: The URL of the ChatGPT conversation to monitor.
            task_nexus: The task nexus for task management.
            simulate: If True, runs in simulation mode without browser interaction.
        """  # noqa: E501
        self.config = config
        self.agent_id = agent_id
        self.conversation_url = conversation_url
        self.simulate = simulate
        self.task_nexus = task_nexus

        # --- Configuration Loading from AppConfig ---
        # Get agent-specific settings (assuming nested structure)
        agent_settings = getattr(
            config, "chat_agent", {}
        )  # Use getattr for safe access
        paths_settings = getattr(config, "paths", {})

        # Inbox Directory (Example: config.paths.agent_inboxes)
        inbox_root_config = getattr(
            paths_settings,
            "agent_inboxes",
            Path("runtime/agent_inboxes"),
        )
        self.inbox_dir = Path(inbox_root_config) / agent_id  # Ensure Path object
        self.inbox_file = self.inbox_dir / "pending_responses.json"

        # Scrape Interval (Example: config.chat_agent.scrape_interval)
        self.interval = getattr(
            config,
            f"agents.chatgpt_web.{self.agent_id}.scrape_interval",
            getattr(
                config,
                "agents.chatgpt_web.default_scrape_interval",
                DEFAULT_INTERVAL,
            ),
        )

        # Onboarding Prompt Path (Example: config.paths.onboarding_prompts)
        onboarding_base_path_config = getattr(
            paths_settings,
            "onboarding_prompts",
            Path("runtime/_agent_coordination/onboarding"),
        )
        self.onboarding_prompt_path = (
            Path(onboarding_base_path_config) / self.agent_id / "start_prompt.md"
        )

        # Reset Onboarding Flag (Example: config.chat_agent.reset_onboarding)
        self.reset_onboarding_flag = getattr(
            agent_settings, "reset_onboarding", False
        )  # Default to False
        # --- End Configuration Loading ---

        self.last_seen = None
        self.driver = None

        # Initialize C2 channel (e.g., LocalBlobChannel, RedisChannel)
        c2_channel_type = getattr(
            config,
            "agents.chatgpt_web.c2_channel.type",
            "LocalBlobChannel",
        )
        # TODO: Instantiate channel based on type (requires importing channel classes) -> REMOVED TODO  # noqa: E501
        # NOTE: To add support for other channel types, import them and add conditions below.  # noqa: E501
        if c2_channel_type == "LocalBlobChannel":
            from dreamos.core.c2.local_blob_channel import (  # Import here
                LocalBlobChannel,
            )

            self.channel = LocalBlobChannel()
        # Example for another type:
        # elif c2_channel_type == "RedisChannel":
        #     from dreamos.core.c2.redis_channel import RedisChannel # Import (if exists)  # noqa: E501
        #     redis_config = get_config("c2.redis", config_obj=self.config) # Get specific config  # noqa: E501
        #     self.channel = RedisChannel(**redis_config)
        else:
            logger.error(f"Unsupported C2 Channel type configured: {c2_channel_type}")
            raise ValueError(f"Unsupported C2 Channel type: {c2_channel_type}")

        # Track which results have been injected into ChatGPT UI
        self.injected_result_ids = set()
        # Cache to store previously pulled results for batching
        self._cached_results = []

        # Flag to ensure onboarding prompt is only sent once
        self.onboarded = False

        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        if not self.inbox_file.exists():
            self._save_pending_responses([])

        # --- Runtime Paths & State ---
        runtime_path = config.paths.resolve_relative_path("runtime")
        self.pending_responses_path = (
            runtime_path / "agent_state" / f"{self.agent_id}_pending_responses.json"
        )
        self.processed_cache_path = (
            runtime_path / "agent_state" / f"{self.agent_id}_processed_cache.json"
        )
        self.onboarding_path = runtime_path / "governance" / "onboarding"
        # Ensure state directories exist
        self.pending_responses_path.parent.mkdir(parents=True, exist_ok=True)
        self.processed_cache_path.parent.mkdir(parents=True, exist_ok=True)

    async def _load_pending_responses(self):
        try:
            # Define sync function
            def sync_read():
                if self.inbox_file.exists():
                    return json.loads(self.inbox_file.read_text(encoding="utf-8"))
                return []
            # Run in thread
            return await asyncio.to_thread(sync_read)
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Failed to load inbox: {e}")
            return []

    async def _save_pending_responses(self, responses):
        try:
            # Define sync function
            def sync_write():
                self.inbox_file.write_text(
                    json.dumps(responses, indent=2), encoding="utf-8"
                )
            # Run in thread
            await asyncio.to_thread(sync_write)
        except Exception as e:
            logger.error(f"[{self.agent_id}] Failed to write inbox: {e}")

    def _initialize_browser(self):
        self.driver = launch_browser()
        if not self.driver:
            logger.error("Browser not launched.")
            return False

        navigate_to_page(self.conversation_url)
        if not wait_for_login():
            logger.error("Login verification failed.")
            return False

        return True

    def _is_result_injected(self, result: Dict) -> bool:
        """Return True if this result (by task_id) was already injected."""
        return result.get("task_id") in self.injected_result_ids

    def _mark_result_injected(self, result: Dict) -> None:
        """Mark this result as injected to avoid duplicates."""
        task_id = result.get("task_id")
        if task_id:
            self.injected_result_ids.add(task_id)

    async def inject_response(self, message: str) -> None:
        """Inject a response into the ChatGPT UI textarea and send it."""
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, TimeoutException

        # --- PyAutoGUI Configuration (from AppConfig ideally) ---
        CHATGPT_WINDOW_TITLE_SUBSTRING = getattr(self.config, 'agents.chatgpt_web.window_title_substring', "ChatGPT") 
        SEND_BUTTON_IMAGE_PATH = getattr(self.config, 'agents.chatgpt_web.send_button_image_path', "assets/gui_elements/chatgpt_send_button.png")
        # Fallback image path if the primary one is not found or configured
        FALLBACK_SEND_BUTTON_IMAGE_PATH = "assets/gui_elements/fallback_chatgpt_send_button.png" # Example
        USE_PYAUTOGUI_FOCUS_CHECK = getattr(self.config, 'agents.chatgpt_web.use_pyautogui_focus_check', True)
        USE_PYAUTOGUI_SEND_FALLBACK = getattr(self.config, 'agents.chatgpt_web.use_pyautogui_send_fallback', True)
        SELENIUM_SEND_BUTTON_XPATH = getattr(self.config, 'agents.chatgpt_web.selenium_send_button_xpath', "//button[contains(@class, 'send-button') or @data-testid='send-button']") # Example common XPaths
        TEXTAREA_XPATH = "//textarea[contains(@placeholder, 'Send a message') or @id='prompt-textarea']"
        # --- End PyAutoGUI Configuration ---

        # 1. Check window focus (Optional, using PyAutoGUI/pygetwindow)
        if PYAUTOGUI_AVAILABLE and USE_PYAUTOGUI_FOCUS_CHECK and pygetwindow:
            logger.debug(f"[{self.agent_id}] Checking window focus for title substring: '{CHATGPT_WINDOW_TITLE_SUBSTRING}'")
            if not is_window_focused(CHATGPT_WINDOW_TITLE_SUBSTRING):
                logger.warning(
                    f"[{self.agent_id}] Target window '{CHATGPT_WINDOW_TITLE_SUBSTRING}' does not appear to be focused. Attempting to activate."
                )
                try:
                    target_windows = pygetwindow.getWindowsWithTitle(CHATGPT_WINDOW_TITLE_SUBSTRING)
                    if target_windows:
                        target_window = target_windows[0]
                        if target_window.isMinimized:
                            target_window.restore()
                        target_window.activate()
                        await asyncio.sleep(0.75) # Give time for focus to shift
                        logger.info(f"[{self.agent_id}] Attempted to activate window: {target_window.title}")
                        if not is_window_focused(CHATGPT_WINDOW_TITLE_SUBSTRING):
                            logger.warning(f"[{self.agent_id}] Failed to confirm focus on target window after activation attempt.")
                    else:
                        logger.warning(f"[{self.agent_id}] No window found with title substring '{CHATGPT_WINDOW_TITLE_SUBSTRING}' to activate.")
                except Exception as e_focus:
                    logger.error(f"[{self.agent_id}] Error during window activation attempt: {e_focus}")
            else:
                logger.debug(f"[{self.agent_id}] Target window '{CHATGPT_WINDOW_TITLE_SUBSTRING}' is focused.")

        # Wrapped Selenium actions in a sync function for asyncio.to_thread
        def sync_inject_and_selenium_send():
            selenium_sent_successfully = False
            try:
                input_box = self.driver.find_element(By.XPATH, TEXTAREA_XPATH)
                # Consider wait_for_element here for robustness
                # input_box = wait_for_element(self.driver, By.XPATH, TEXTAREA_XPATH, timeout=10)
                # if not input_box:
                #     logger.error(f"[{self.agent_id}] Textarea not found with XPATH: {TEXTAREA_XPATH}")
                #     return False
                
                input_box.clear()
                input_box.send_keys(message)
                # Attempt to click the send button via Selenium first
                try:
                    send_button = self.driver.find_element(By.XPATH, SELENIUM_SEND_BUTTON_XPATH)
                    if send_button.is_displayed() and send_button.is_enabled():
                        send_button.click()
                        selenium_sent_successfully = True
                        logger.info(f"[{self.agent_id}] Successfully sent message via Selenium button click.")
                    else:
                        logger.warning(f"[{self.agent_id}] Selenium send button found but not interactable. Will try newline.")
                except NoSuchElementException:
                    logger.warning(f"[{self.agent_id}] Selenium send button not found by XPATH '{SELENIUM_SEND_BUTTON_XPATH}'. Will try newline.")
                
                if not selenium_sent_successfully:
                    logger.info(f"[{self.agent_id}] Attempting to send by sending newline character to textarea.")
                    input_box.send_keys("\n")
                    selenium_sent_successfully = True # Assume newline works if no immediate error
                    logger.info(f"[{self.agent_id}] Successfully sent message via Selenium newline.")
                return selenium_sent_successfully
            except (NoSuchElementException, ElementNotInteractableException, TimeoutException) as e_selenium:
                logger.error(f"[{self.agent_id}] Selenium error during injection/send: {e_selenium}")
                return False # Selenium failed
            except Exception as e_general_selenium:
                logger.error(f"[{self.agent_id}] Unexpected Selenium error: {e_general_selenium}", exc_info=True)
                return False

        selenium_send_success = False
        try:
            selenium_send_success = await asyncio.to_thread(sync_inject_and_selenium_send)
            await asyncio.sleep(0.5) # Brief pause after Selenium attempt

            if selenium_send_success:
                logger.info(f"[{self.agent_id}] 🛰️ Message injection via Selenium presumed successful.")
            else:
                logger.warning(f"[{self.agent_id}] Selenium send failed or was inconclusive.")
                if PYAUTOGUI_AVAILABLE and USE_PYAUTOGUI_SEND_FALLBACK:
                    logger.info(f"[{self.agent_id}] Attempting PyAutoGUI fallback for sending message...")
                    try:
                        # Ensure textarea still has the message or re-type if necessary (safer to re-type)
                        # For simplicity, assume message is still there or Selenium clear/send_keys part worked.
                        # A more robust PyAutoGUI fallback would re-focus element, re-type, then send.
                        
                        # Try clicking send button by image first
                        send_button_location = None
                        try:
                            send_button_location = pyautogui.locateCenterOnScreen(SEND_BUTTON_IMAGE_PATH, confidence=0.8)
                        except Exception as e_locate_primary: # pyautogui.ImageNotFoundException might not be raised if confidence fails
                            logger.warning(f"[{self.agent_id}] Primary send button image '{SEND_BUTTON_IMAGE_PATH}' not found ({e_locate_primary}). Trying fallback image.")
                            try:
                                send_button_location = pyautogui.locateCenterOnScreen(FALLBACK_SEND_BUTTON_IMAGE_PATH, confidence=0.8)
                            except Exception as e_locate_fallback:
                                logger.warning(f"[{self.agent_id}] Fallback send button image '{FALLBACK_SEND_BUTTON_IMAGE_PATH}' not found ({e_locate_fallback}). Will try Enter key.")
                        
                        if send_button_location:
                            pyautogui.click(send_button_location)
                            logger.info(f"[{self.agent_id}] 🛰️ Message sent via PyAutoGUI image click.")
                        else:
                            logger.info(f"[{self.agent_id}] PyAutoGUI send button image not found. Attempting to send with Enter key.")
                            pyautogui.press('enter')
                            logger.info(f"[{self.agent_id}] 🛰️ Message sent via PyAutoGUI Enter key press.")
                        await asyncio.sleep(1) # Pause after PyAutoGUI action
                    except Exception as e_pyauto:
                        logger.error(f"[{self.agent_id}] PyAutoGUI fallback send failed: {e_pyauto}", exc_info=True)
                        # If both Selenium and PyAutoGUI fail, this is a hard failure for injection.
                        raise ElementNotInteractableException("Both Selenium and PyAutoGUI failed to send message.")
                elif not PYAUTOGUI_AVAILABLE and USE_PYAUTOGUI_SEND_FALLBACK:
                    logger.warning(f"[{self.agent_id}] PyAutoGUI fallback requested but PyAutoGUI is not available.")
                    raise ElementNotInteractableException("Selenium send failed and PyAutoGUI is not available for fallback.")
                else: # Selenium failed and PyAutoGUI fallback not used/requested
                     raise ElementNotInteractableException("Selenium send failed and PyAutoGUI fallback not configured.")
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Overall failure in inject_response: {e}", exc_info=True)
            # Re-raise critical errors or handle them to prevent agent crashing
            # For now, re-raising to indicate failure to the caller.
            raise

    def _get_and_cache_results(self) -> list:
        """Fetches results from the C2 channel and attempts to identify new ones.

        FIXME: The current caching logic might be flawed. It compares the current
               full pull of results against the previous full pull. If results can be
               removed from the channel by other consumers or if order is not guaranteed,
               this won't reliably identify only 'new' results. A more robust approach
               would be to track processed result IDs.
        """
        results = self.channel.pull_results()
        previous = getattr(self, "_results_cache", [])
        new_results = [r for r in results if r not in previous]
        self._results_cache = results
        return new_results

    async def _scrape_latest_response(self, attempts=3, delay_seconds=5):
        """Scrapes the latest response from the ChatGPT UI, with retries.

        Uses a synchronous scrape function run in a separate thread.
        Compares against `self.last_seen` to detect new responses.

        Args:
            attempts: Number of times to try scraping.
            delay_seconds: Delay between scrape attempts.

        Returns:
            The latest response text if a new one is found, otherwise None.
        """
        from selenium.webdriver.common.by import By # Ensure By is imported

        def sync_scrape():
            # Wait for a new response to appear after injection
            # This might need a more robust check than just time.sleep
            # Example: Wait for a specific element indicating new content, or change in response count
            time.sleep(delay_seconds) # Initial wait for response generation

            page_source = self.driver.page_source
            # logger.debug(f"Page source for scraping: {page_source[:500]}")
            latest_reply_text, _ = extract_latest_reply(page_source)
            return latest_reply_text

        for attempt in range(attempts):
            try:
                logger.info(f"[{self.agent_id}] Attempt {attempt + 1} to scrape response.")
                latest_reply = await asyncio.to_thread(sync_scrape)
                if latest_reply and (not self.last_seen or latest_reply != self.last_seen):
                    self.last_seen = latest_reply
                    logger.info(f"[{self.agent_id}] Successfully scraped new response: {latest_reply[:100]}...")
                    return latest_reply
                else:
                    logger.info(f"[{self.agent_id}] No new response or response unchanged. Last seen: {self.last_seen[:100]}...")
            except Exception as e:
                logger.error(f"[{self.agent_id}] Error during scrape attempt {attempt + 1}: {e}", exc_info=True)
            
            if attempt < attempts - 1:
                logger.info(f"[{self.agent_id}] Waiting {delay_seconds}s before next scrape attempt.")
                await asyncio.sleep(delay_seconds)
        
        logger.warning(f"[{self.agent_id}] Failed to scrape a new response after {attempts} attempts.")
        return None

    async def process_prompt_via_ui(self, prompt_text: str) -> str | None:
        """Handles a single prompt end-to-end: injects, sends, and scrapes response via UI.

        In simulation mode, it returns a simulated response.
        Otherwise, it initializes the browser if needed, injects the prompt,
        and attempts to scrape the resulting response.

        Args:
            prompt_text: The text to inject as a prompt.

        Returns:
            The scraped response text, or None if processing fails or no response is found.
        """
        if self.simulate:
            logger.info(f"[{self.agent_id}] Simulating UI processing for prompt: {prompt_text[:100]}...")
            # Simple simulation: echo prompt with a prefix
            return f"Simulated UI response to: {prompt_text}"

        if not self.driver:
            logger.info(f"[{self.agent_id}] Browser not initialized. Initializing now for UI processing.")
            if not self._initialize_browser():
                logger.error(f"[{self.agent_id}] Failed to initialize browser. Cannot process prompt.")
                return None
        
        try:
            logger.info(f"[{self.agent_id}] Injecting prompt into UI: {prompt_text[:100]}...")
            await self.inject_response(prompt_text)
            
            logger.info(f"[{self.agent_id}] Attempting to scrape response from UI.")
            response = await self._scrape_latest_response()
            
            if response:
                logger.info(f"[{self.agent_id}] Successfully processed prompt via UI. Response: {response[:100]}...")
            else:
                logger.warning(f"[{self.agent_id}] Did not get a response from UI after processing prompt.")
            return response
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error during UI processing of prompt '{prompt_text[:50]}...': {e}", exc_info=True)
            return None

    async def run_cycle(self):
        """Executes one operational cycle of the ChatGPTWebAgent.

        In simulation mode, it processes tasks from the C2 channel and simulates responses.
        In normal mode, it handles onboarding prompts, scrapes for new ChatGPT replies,
        parses them for task metadata, and (presumably in later code) acts on them.
        """
        # Simulation mode: auto-generate tasks without browser interaction
        if getattr(self, "simulate", False):
            tasks = self.channel.pull_tasks()
            for task in tasks:
                task_id = task.get("task_id") or task.get("id")
                logger.info(f"[{self.agent_id}] 🛠️ Simulating response for {task_id}")
                sim_payload = f"Simulated response payload for task {task_id}"
                # Push simulation result back to LocalBlobChannel
                self.channel.push_result({"id": task_id, "content": sim_payload})
                # Also push to TaskNexus for Cursor workers
                self.task_nexus.add_task({"task_id": task_id, "payload": sim_payload})
            return

        if not self.driver and not self._initialize_browser():
            return

        # Allow reset of onboarding prompt on each cycle if flag from config is set
        if self.reset_onboarding_flag:
            logger.info(f"[{self.agent_id}] Resetting onboarding flag based on config.")
            self.onboarded = False

        # Send onboarding start prompt on first cycle if available
        if not self.onboarded:
            prompt_path = self.onboarding_prompt_path
            # Define sync read
            def sync_read_prompt():
                if prompt_path.exists():
                    return prompt_path.read_text(encoding="utf-8")
                return None
            
            start_prompt = await asyncio.to_thread(sync_read_prompt)

            if start_prompt:
                try:
                    await self.inject_response(start_prompt)
                    logger.info(
                        f"[{self.agent_id}] Sent onboarding start prompt from {prompt_path}."
                    )
                except Exception as e:
                    logger.error(
                        f"[{self.agent_id}] Failed to inject start prompt from {prompt_path}: {e}",
                        exc_info=True,
                    )
            else:
                logger.warning(
                    f"[{self.agent_id}] Onboarding prompt file not found at configured path: {prompt_path}"
                )
            self.onboarded = True

        logger.info(f"[{self.agent_id}] 🔍 Checking for ChatGPT reply...")
        try:
            # Assuming extract_latest_reply uses selenium, wrap it
            def sync_scrape():
                return extract_latest_reply(self.driver)
            reply = await asyncio.to_thread(sync_scrape)

            # Case 1: Reply is None (means assistant is still generating)
            if reply is None:
                # Let the html_parser log handle the specific reason (generating vs. error)  # noqa: E501
                logger.debug(
                    f"[{self.agent_id}] Reply not ready or assistant generating."
                )
                return  # Wait for next cycle

            # Case 2: Reply is same as last seen
            if reply == self.last_seen:
                logger.debug(
                    f"[{self.agent_id}] No new message detected since last cycle."
                )
                return  # Wait for next cycle

            # Case 3: New, complete reply detected
            self.last_seen = reply
            logger.info(f"[{self.agent_id}] ✨ New response detected (processing):")
            logger.debug(f"[{self.agent_id}] Raw Reply Snippet: {reply[:150]}...")

            parsed = extract_task_metadata(reply)

            # Check if parsing was successful (TaskParser logs errors internally)
            if parsed and parsed.get("feedback"):  # Check for core feedback key
                # Add timestamp if not already present (might be from JSON)
                parsed.setdefault("timestamp", time.time())
                # Ensure raw_reply is present (parser adds it for regex, check for JSON)
                parsed.setdefault("raw_reply", reply)

                # Add/Update in inbox
                inbox = await self._load_pending_responses()
                task_id_to_match = parsed.get("task_id")

                # Use task_id for matching if available
                if task_id_to_match:
                    existing = next(
                        (r for r in inbox if r.get("task_id") == task_id_to_match), None
                    )
                    if existing:
                        logger.info(
                            f"[{self.agent_id}] Updating feedback for Task ID: {task_id_to_match}"  # noqa: E501
                        )
                        # Replace existing entry
                        inbox = [
                            parsed if r["task_id"] == task_id_to_match else r
                            for r in inbox
                        ]
                    else:
                        logger.info(
                            f"[{self.agent_id}] Adding new feedback for Task ID: {task_id_to_match}"  # noqa: E501
                        )
                        inbox.append(parsed)
                else:
                    # If no task_id, maybe append anyway? Or log warning?
                    # For now, let's assume task_id is required for routing.
                    logger.warning(
                        f"[{self.agent_id}] Parsed feedback lacks task_id. Cannot route reliably. Discarding."  # noqa: E501
                    )
                    logger.debug(f"Discarded feedback: {parsed}")
                    return  # Skip saving

                await self._save_pending_responses(inbox)
                # Add parsed task to TaskNexus
                try:
                    await asyncio.to_thread(self.task_nexus.add_task, parsed)
                    logger.info(
                        f"[{self.agent_id}] Dispatched task to TaskNexus: {parsed.get('task_id')}"
                    )
                except Exception as e:
                    logger.error(
                        f"[{self.agent_id}] Failed to add task to TaskNexus: {e}",
                        exc_info=True,
                    )
            else:
                # Parsing failed (TaskParser already logged error)
                logger.warning(
                    f"[{self.agent_id}] Failed to parse structured metadata from the new response."  # noqa: E501
                )
                # No further action needed here, wait for next cycle or manual check

        except Exception as e:
            logger.error(
                f"[{self.agent_id}] Error during agent cycle: {e}", exc_info=True
            )
        # Pull all results once and filter new ones not yet injected
        try:
            results = self._get_and_cache_results()
            for res in results:
                if not self._is_result_injected(res):
                    content = (
                        res.get("raw_reply") or res.get("content") or json.dumps(res)
                    )
                    try:
                        await self.inject_response(content)
                        self._mark_result_injected(res)
                    except Exception as ie:
                        logger.error(
                            f"[{self.agent_id}] ❌ Failed to inject result: {ie}",
                            exc_info=True,
                        )
            # Update cache (if needed for future logic)
            self._cached_results = results
        except Exception as ce:
            logger.error(
                f"[{self.agent_id}] Error pulling/injecting results: {ce}",
                exc_info=True,
            )
            # FIXME: The _get_and_cache_results and subsequent _cached_results update
            #        might need review. If _get_and_cache_results correctly identifies
            #        *new* results to process, simply processing those should be sufficient.
            #        The role of self._cached_results after this block needs clarification.

    async def process_external_prompt(self, prompt_text: str) -> str | None:
        """Processes an externally provided prompt via the ChatGPT UI.

        This method injects the prompt, attempts to scrape the reply, and returns it.
        It's designed for use by other system components needing direct interaction.
        Handles browser initialization and navigation if necessary.

        Args:
            prompt_text: The prompt text to inject.

        Returns:
            The scraped reply text if successful, an empty string if no new reply
            is detected, or None if an error occurs during processing.
        """
        logger.info(f"[{self.agent_id}] Received external prompt: {prompt_text[:100]}...")

        if self.simulate:
            logger.info(f"[{self.agent_id}] Simulating external prompt processing for: {prompt_text[:50]}...")
            # Simple echo simulation for external prompts
            await asyncio.sleep(0.1) # Simulate some processing time
            return f"Simulated echo response to: {prompt_text}"

        if not self.driver:
            logger.info(f"[{self.agent_id}] Browser not initialized for external prompt. Initializing...")
            if not await asyncio.to_thread(self._initialize_browser): # _initialize_browser is sync
                logger.error(f"[{self.agent_id}] Critical: Browser initialization failed. Cannot process external prompt.")
                return None
            logger.info(f"[{self.agent_id}] Browser initialized successfully.")
        
        try:
            # Ensure we are on the conversation page (might have navigated away or session expired)
            # This might be overly cautious or could be part of _initialize_browser's login check
            current_url = await asyncio.to_thread(lambda: self.driver.current_url)
            if self.conversation_url not in current_url:
                logger.warning(f"[{self.agent_id}] Not on conversation URL ({current_url}). Navigating...")
                await asyncio.to_thread(navigate_to_page, self.conversation_url)
                # Potentially re-verify login if navigation happens, though wait_for_login in _initialize_browser should cover initial login

            logger.info(f"[{self.agent_id}] Injecting external prompt into UI...")
            await self.inject_response(prompt_text) # inject_response is already async
            
            # Wait a bit for the response to appear after injection.
            # Using a fixed delay here. More sophisticated waiting logic (e.g., for a specific element change) would be more robust.
            # This delay should be less than self.interval to avoid overlapping with a potential main run_cycle scrape.
            external_processing_delay = getattr(self.config, "agents.chatgpt_web.external_prompt_delay", self.interval / 2)
            logger.info(f"[{self.agent_id}] Waiting {external_processing_delay}s for reply to external prompt...")
            await asyncio.sleep(external_processing_delay)

            logger.info(f"[{self.agent_id}] Scraping reply for external prompt...")
            page_source = await asyncio.to_thread(lambda: self.driver.page_source)
            # Ensure extract_latest_reply can be called safely if page_source is None or driver died
            if not page_source:
                logger.error(f"[{self.agent_id}] Failed to get page source for scraping external reply.")
                return None

            latest_reply, _ = extract_latest_reply(page_source, self.last_seen) # extract_latest_reply is sync
            
            if latest_reply:
                self.last_seen = latest_reply # IMPORTANT: Update last_seen with the new reply
                logger.info(f"[{self.agent_id}] Successfully scraped reply for external prompt: {latest_reply[:100]}...")
                return latest_reply
            else:
                logger.warning(f"[{self.agent_id}] No new reply found after injecting external prompt.")
                # It's important to distinguish no reply from an error.
                # Returning an empty string or a special marker might be better than None if no reply is a valid outcome.
                return "" # Indicate no new reply was found

        except Exception as e:
            logger.error(f"[{self.agent_id}] Error processing external prompt: {e}", exc_info=True)
            # Consider re-initializing browser on certain errors, e.g., WebDriverException
            return None # Indicates an error occurred

    async def run(self):
        """Main asynchronous execution loop for the ChatGPTWebAgent.
        
        Continuously runs the agent's operational cycle (`run_cycle`) at a configured
        interval. This loop is expected to be run as an asyncio task.
        """
        logger.info(f"Agent {self.agent_id} starting run loop.")
        while True: # Basic loop, add termination logic if needed
            await self.run_cycle()
            await asyncio.sleep(self.interval) # Use interval from config

    async def close(self):
        """Closes the browser session asynchronously.
        
        Uses asyncio.to_thread to run the synchronous close_browser utility.
        """
        # Assume close_browser is sync
        def sync_close():
            close_browser() # This is the global gui_utils.close_browser
        
        logger.info(f"[{self.agent_id}] Attempting to close browser session...")
        try:
            await asyncio.to_thread(sync_close)
            logger.info(f"[{self.agent_id}] Browser close command issued.")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error during browser close: {e}", exc_info=True)


async def run_loop(agent_id: str):
    """Main loop for the ChatGPTWebAgent."""
    logger.info(f"Starting run_loop for agent: {agent_id}")
    # EDIT: Instantiate config directly
    config = AppConfig()
    # agent = ChatGPTWebAgent(config=get_config(), agent_id=agent_id)
    nexus = TaskNexus()
    agent = ChatGPTWebAgent(config=config, agent_id=agent_id, task_nexus=nexus)
    try:
        await agent.run()
    finally:
        agent.close()


# ... (rest of file, __main__ block etc.) ...
