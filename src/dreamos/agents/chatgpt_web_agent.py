# chatgpt_web_agent.py

import json
import logging
import time
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
)

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
        simulate: bool = False,
    ):
        """
        Initializes the ChatGPT Web Agent.

        Args:
            config: The central application configuration object.
            agent_id: The unique ID for this agent instance (e.g., specific conversation ID).
            conversation_url: The URL of the ChatGPT conversation to monitor.
            simulate: If True, runs in simulation mode without browser interaction.
        """  # noqa: E501
        self.config = config
        self.agent_id = agent_id
        self.conversation_url = conversation_url
        self.simulate = simulate

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

        # Initialize TaskNexus - Get Path from central config
        # task_list_path = getattr(config.paths, 'tasks', Path("runtime/task_list.json")) # Simplified access below  # noqa: E501
        task_list_path = getattr(
            config,
            "services.task_nexus.task_file",
            Path("runtime/task_list.json"),
        )
        self.nexus = TaskNexus(
            task_file=task_list_path
        )  # TaskNexus likely wants string path
        # Track which results have been injected into ChatGPT UI
        self.injected_result_ids = set()
        # Cache to store previously pulled results for batching
        self._cached_results = []

        # Flag to ensure onboarding prompt is only sent once
        self.onboarded = False

        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        if not self.inbox_file.exists():
            self._save_pending_responses([])

        self.task_nexus = TaskNexus()  # Assuming nexus handles its own path
        self.agent_bus = AgentBus()

        # --- Runtime Paths & State ---
        # EDIT START: Resolve paths relative to configured root
        runtime_path = config.paths.resolve_relative_path("runtime")
        self.pending_responses_path = (
            runtime_path / "agent_state" / f"{self.agent_id}_pending_responses.json"
        )
        self.processed_cache_path = (
            runtime_path / "agent_state" / f"{self.agent_id}_processed_cache.json"
        )
        # EDIT START: Update path to new location
        # self.onboarding_path = Path("runtime/_agent_coordination/onboarding")
        self.onboarding_path = runtime_path / "governance" / "onboarding"
        # EDIT END
        # Ensure state directories exist
        self.pending_responses_path.parent.mkdir(parents=True, exist_ok=True)
        self.processed_cache_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_pending_responses(self):
        try:
            if self.inbox_file.exists():
                return json.loads(self.inbox_file.read_text(encoding="utf-8"))
            return []
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Failed to load inbox: {e}")
            return []

    def _save_pending_responses(self, responses):
        try:
            self.inbox_file.write_text(
                json.dumps(responses, indent=2), encoding="utf-8"
            )
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

    def inject_response(self, message: str) -> None:
        """Inject a response into the ChatGPT UI textarea and send it."""
        from selenium.webdriver.common.by import By

        input_box = self.driver.find_element(
            By.XPATH, "//textarea[contains(@placeholder, 'Send a message')]"
        )
        input_box.clear()
        input_box.send_keys(message)
        time.sleep(1)
        input_box.send_keys("\n")
        logger.info(f"[{self.agent_id}] 🛰️ Injected swarm response into ChatGPT UI.")

    def _get_and_cache_results(self) -> list:
        """Fetch and cache results to avoid redundant pull_results calls."""
        results = self.channel.pull_results()
        previous = getattr(self, "_results_cache", [])
        new_results = [r for r in results if r not in previous]
        self._results_cache = results
        return new_results

    def run_cycle(self):
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
                self.nexus.add_task({"task_id": task_id, "payload": sim_payload})
            return

        if not self.driver and not self._initialize_browser():
            return

        # Allow reset of onboarding prompt on each cycle if flag from config is set
        if self.reset_onboarding_flag:
            logger.info(f"[{self.agent_id}] Resetting onboarding flag based on config.")
            self.onboarded = False

        # Send onboarding start prompt on first cycle if available
        if not self.onboarded:
            prompt_path = self.onboarding_prompt_path  # Use path from config
            if prompt_path.exists():
                try:
                    start_prompt = prompt_path.read_text(encoding="utf-8")
                    self.inject_response(start_prompt)
                    logger.info(
                        f"[{self.agent_id}] Sent onboarding start prompt from {prompt_path}."  # noqa: E501
                    )
                except Exception as e:
                    logger.error(
                        f"[{self.agent_id}] Failed to inject start prompt from {prompt_path}: {e}",  # noqa: E501
                        exc_info=True,
                    )
            else:
                logger.warning(
                    f"[{self.agent_id}] Onboarding prompt file not found at configured path: {prompt_path}"  # noqa: E501
                )
            self.onboarded = True  # Mark as onboarded even if prompt fails/missing

        logger.info(f"[{self.agent_id}] 🔍 Checking for ChatGPT reply...")
        try:
            reply = extract_latest_reply(self.driver)

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
                inbox = self._load_pending_responses()
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

                self._save_pending_responses(inbox)
                # Add parsed task to TaskNexus
                try:
                    self.nexus.add_task(parsed)
                    logger.info(
                        f"[{self.agent_id}] Dispatched task to TaskNexus: {parsed.get('task_id')}"  # noqa: E501
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
                        self.inject_response(content)
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

    def close(self):
        """Close the browser session."""
        close_browser()


async def run_loop(agent_id: str):
    """Main loop for the ChatGPTWebAgent."""
    logger.info(f"Starting run_loop for agent: {agent_id}")
    # EDIT: Instantiate config directly
    config = AppConfig()
    # agent = ChatGPTWebAgent(config=get_config(), agent_id=agent_id)
    agent = ChatGPTWebAgent(config=config, agent_id=agent_id)
    await agent.run()


# ... (rest of file, __main__ block etc.) ...
