# chatgpt_web_agent.py

import time
import json
import logging
from pathlib import Path
from utils import browser, html_parser, task_parser

logger = logging.getLogger("ChatGPTWebAgent")
logger.setLevel(logging.INFO)

DEFAULT_INTERVAL = 10  # seconds between scrape attempts
AGENT_SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = AGENT_SCRIPT_DIR.parent / "config" / "dream_mode_config.json"
INBOX_ROOT = AGENT_SCRIPT_DIR.parent / "inbox"

class ChatGPTWebAgent:
    def __init__(self, agent_id: str, conversation_url: str):
        self.agent_id = agent_id
        self.conversation_url = conversation_url
        self.inbox_dir = INBOX_ROOT / agent_id
        self.inbox_file = self.inbox_dir / "pending_responses.json"
        self.last_seen = None
        self.driver = None

        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        if not self.inbox_file.exists():
            self._save_pending_responses([])

    def _load_pending_responses(self):
        try:
            with open(self.inbox_file, 'r', encoding='utf-8') as f:
                content = f.read()
                return json.loads(content) if content.strip() else []
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Failed to load inbox: {e}")
            return []

    def _save_pending_responses(self, responses):
        try:
            with open(self.inbox_file, 'w', encoding='utf-8') as f:
                json.dump(responses, f, indent=2)
        except Exception as e:
            logger.error(f"[{self.agent_id}] Failed to write inbox file: {e}")

    def _initialize_browser(self):
        self.driver = browser.launch_browser()
        if not self.driver:
            logger.error("Browser not launched.")
            return False

        browser.navigate_to_page(self.conversation_url)
        if not browser.wait_for_login():
            logger.error("Login verification failed.")
            return False

        return True

    def run_cycle(self):
        if not self.driver and not self._initialize_browser():
            return

        logger.info(f"[{self.agent_id}] 🔍 Checking for ChatGPT reply...")
        try:
            reply = html_parser.extract_latest_reply(self.driver)
            
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
            
            parsed = task_parser.extract_task_metadata(reply)

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
            else:
                # Parsing failed (TaskParser already logged error)
                logger.warning(f"[{self.agent_id}] Failed to parse structured metadata from the new response.")
                # No further action needed here, wait for next cycle or manual check

        except Exception as e:
            logger.error(f"[{self.agent_id}] Error during agent cycle: {e}", exc_info=True)

    def close(self):
        browser.close_browser()

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