# chatgpt_web_agent.py

import time
import json
import logging
from pathlib import Path
from dream_mode.utils.browser import launch_browser, navigate_to_page, wait_for_login, close_browser
from dream_mode.utils.html_parser import extract_latest_reply
from dream_mode.utils.task_parser import extract_task_metadata

from dream_mode.local_blob_channel import LocalBlobChannel
from dream_mode.task_nexus.task_nexus import TaskNexus
import os  # for environment variables
from typing import Dict
from _agent_coordination.tools.file_lock_manager import read_json, write_json

logger = logging.getLogger("ChatGPTWebAgent")
logger.setLevel(logging.INFO)

DEFAULT_INTERVAL = 10  # seconds between scrape attempts
AGENT_SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = AGENT_SCRIPT_DIR.parent / "config" / "dream_mode_config.json"
INBOX_ROOT = AGENT_SCRIPT_DIR.parent / "inbox"

class ChatGPTWebAgent:
    def __init__(self, agent_id: str, conversation_url: str, simulate: bool = False):
        self.agent_id = agent_id
        self.conversation_url = conversation_url
        self.simulate = simulate
        self.inbox_dir = INBOX_ROOT / agent_id
        self.inbox_file = self.inbox_dir / "pending_responses.json"
        self.last_seen = None
        self.driver = None

        # Initialize C2 channel (Local only)
        self.channel = LocalBlobChannel()
        # Initialize TaskNexus for coordinating tasks
        self.nexus = TaskNexus(task_file="runtime/task_list.json")
        # Track which results have been injected into ChatGPT UI
        self.injected_result_ids = set()
        # Cache to store previously pulled results for batching
        self._cached_results = []

        # Flag to ensure onboarding prompt is only sent once
        self.onboarded = False

        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        if not self.inbox_file.exists():
            self._save_pending_responses([])

    def _load_pending_responses(self):
        try:
            data = read_json(self.inbox_file)
            return data if data else []
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Failed to load inbox with lock: {e}")
            return []

    def _save_pending_responses(self, responses):
        try:
            write_json(self.inbox_file, responses)
        except Exception as e:
            logger.error(f"[{self.agent_id}] Failed to write inbox with lock: {e}")

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

    def inject_response(self, message: str) -> None:
        """Inject a response into the ChatGPT UI textarea and send it."""
        from selenium.webdriver.common.by import By

        input_box = self.driver.find_element(By.XPATH, "//textarea[contains(@placeholder, 'Send a message')]")
        input_box.clear()
        input_box.send_keys(message)
        time.sleep(1)
        input_box.send_keys("\n")
        logger.info(f"[{self.agent_id}] 🛰️ Injected swarm response into ChatGPT UI.")

    def _get_and_cache_results(self) -> list:
        """Fetch and cache results to avoid redundant pull_results calls."""
        results = self.channel.pull_results()
        previous = getattr(self, '_results_cache', [])
        new_results = [r for r in results if r not in previous]
        self._results_cache = results
        return new_results

    def run_cycle(self):
        # Simulation mode: auto-generate tasks without browser interaction
        if getattr(self, 'simulate', False):
            tasks = self.channel.pull_tasks()
            for task in tasks:
                task_id = task.get("task_id") or task.get("id")
                logger.info(f"[{self.agent_id}] 🛠️ Simulating response for {task_id}")
                sim_payload = f"Simulated response payload for task {task_id}"
                # Push simulation result back to LocalBlobChannel
                self.channel.push_result({"id": task_id, "content": sim_payload})
                # Also push to TaskNexus for Cursor workers
                self.nexus.add_task({"task_id": task_id, "payload": sim_payload})
            return

        if not self.driver and not self._initialize_browser():
            return

        # Allow reset of onboarding prompt on each cycle if env var is set
        if os.getenv("RESET_ONBOARDING") == "1":
            self.onboarded = False

        # Send onboarding start prompt on first cycle if available
        if not self.onboarded:
            prompt_path = Path(os.getcwd()) / "_agent_coordination" / "onboarding" / self.agent_id / "start_prompt.md"
            if prompt_path.exists():
                try:
                    start_prompt = prompt_path.read_text(encoding="utf-8")
                    self.inject_response(start_prompt)
                    logger.info(f"[{self.agent_id}] Sent onboarding start prompt.")
                except Exception as e:
                    logger.error(f"[{self.agent_id}] Failed to inject start prompt: {e}", exc_info=True)
            self.onboarded = True

        logger.info(f"[{self.agent_id}] 🔍 Checking for ChatGPT reply...")
        try:
            reply = extract_latest_reply(self.driver)
            
            # Case 1: Reply is None (means assistant is still generating)
            if reply is None:
                # Let the html_parser log handle the specific reason (generating vs. error)
                logger.debug(f"[{self.agent_id}] Reply not ready or assistant generating.")
                return # Wait for next cycle
                
            # Case 2: Reply is same as last seen
            if reply == self.last_seen:
                logger.debug(f"[{self.agent_id}] No new message detected since last cycle.")
                return # Wait for next cycle

            # Case 3: New, complete reply detected
            self.last_seen = reply
            logger.info(f"[{self.agent_id}] ✨ New response detected (processing):")
            logger.debug(f"[{self.agent_id}] Raw Reply Snippet: {reply[:150]}...")
            
            parsed = extract_task_metadata(reply)

            # Check if parsing was successful (TaskParser logs errors internally)
            if parsed and parsed.get("feedback"): # Check for core feedback key
                # Add timestamp if not already present (might be from JSON)
                parsed.setdefault("timestamp", time.time())
                # Ensure raw_reply is present (parser adds it for regex, check for JSON)
                parsed.setdefault("raw_reply", reply)
                
                # Add/Update in inbox
                inbox = self._load_pending_responses()
                task_id_to_match = parsed.get("task_id")
                
                # Use task_id for matching if available
                if task_id_to_match:
                    existing = next((r for r in inbox if r.get("task_id") == task_id_to_match), None)
                    if existing:
                        logger.info(f"[{self.agent_id}] Updating feedback for Task ID: {task_id_to_match}")
                        # Replace existing entry
                        inbox = [parsed if r["task_id"] == task_id_to_match else r for r in inbox]
                    else:
                        logger.info(f"[{self.agent_id}] Adding new feedback for Task ID: {task_id_to_match}")
                        inbox.append(parsed)
                else:
                    # If no task_id, maybe append anyway? Or log warning?
                    # For now, let's assume task_id is required for routing.
                    logger.warning(f"[{self.agent_id}] Parsed feedback lacks task_id. Cannot route reliably. Discarding.")
                    logger.debug(f"Discarded feedback: {parsed}")
                    return # Skip saving

                self._save_pending_responses(inbox)
                # Add parsed task to TaskNexus
                try:
                    self.nexus.add_task(parsed)
                    logger.info(f"[{self.agent_id}] Dispatched task to TaskNexus: {parsed.get('task_id')}")
                except Exception as e:
                    logger.error(f"[{self.agent_id}] Failed to add task to TaskNexus: {e}", exc_info=True)
            else:
                # Parsing failed (TaskParser already logged error)
                logger.warning(f"[{self.agent_id}] Failed to parse structured metadata from the new response.")
                # No further action needed here, wait for next cycle or manual check

        except Exception as e:
            logger.error(f"[{self.agent_id}] Error during agent cycle: {e}", exc_info=True)
        # Pull all results once and filter new ones not yet injected
        try:
            results = self._get_and_cache_results()
            for res in results:
                if not self._is_result_injected(res):
                    content = res.get("raw_reply") or res.get("content") or json.dumps(res)
                    try:
                        self.inject_response(content)
                        self._mark_result_injected(res)
                    except Exception as ie:
                        logger.error(f"[{self.agent_id}] ❌ Failed to inject result: {ie}", exc_info=True)
            # Update cache (if needed for future logic)
            self._cached_results = results
        except Exception as ce:
            logger.error(f"[{self.agent_id}] Error pulling/injecting results: {ce}", exc_info=True)

    def close(self):
        """Close the browser session."""
        close_browser()

def run_loop(shutdown_event):
    logger.info("🧠 ChatGPT Web Agent started.")

    # Load configuration
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        agents = config.get("agents", {})
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    instances = {}

    while not shutdown_event.is_set():
        for agent_id, info in agents.items():
            if shutdown_event.is_set():
                break
            if agent_id not in instances:
                logger.info(f"Spawning WebAgent for: {agent_id}")
                instances[agent_id] = ChatGPTWebAgent(agent_id, info["conversation_url"])
            try:
                instances[agent_id].run_cycle()
            except Exception as e:
                logger.error(f"[{agent_id}] Agent cycle error: {e}", exc_info=True)

        if shutdown_event.wait(DEFAULT_INTERVAL):
            break

    logger.info("Web Agent loop exiting.")
    for inst in instances.values():
        inst.close() 
