#!/usr/bin/env python3
"""
Dream.OS  ➜  Cursor ↔ THEA Bridge Loop
=====================================

Autonomously:
1.  Injects a prompt into the active Cursor window via PyAutoGUI
2.  Waits (or polls) for THEA to respond in ChatGPT web UI
3.  Scrapes the response with ChatGPTScraper (undetected‑chromedriver)
4.  Stores the response and (optionally) pipes it back into the agent loop
5.  Repeats until the prompt queue is empty or SIGINT received

Drop this in:  `src/dreamos/bridge/run_bridge_loop.py`
Run with:      `python -m dreamos.bridge.run_bridge_loop --agent-id 1 --prompt-file prompts/hello.txt`
"""

import argparse
import json
import signal
import sys
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

print("DEBUG: run_bridge_loop.py - About to import pyautogui", file=sys.stderr, flush=True)
import pyautogui
print("DEBUG: run_bridge_loop.py - Successfully imported pyautogui", file=sys.stderr, flush=True)

from dreamos.core.config import AppConfig, GuiAutomationConfig
from dreamos.services.utils.chatgpt_scraper import ResponseHandler

print("DEBUG: run_bridge_loop.py - About to import CursorInjector", file=sys.stderr, flush=True)
from dreamos.cli.cursor_injector import CursorInjector
print("DEBUG: run_bridge_loop.py - Successfully imported CursorInjector", file=sys.stderr, flush=True)

sys.stderr.write("DEBUG: run_bridge_loop.py EXECUTING\n")
sys.stderr.write(f"DEBUG: run_bridge_loop.py CWD: {os.getcwd()}\n")
sys.stderr.write(f"DEBUG: run_bridge_loop.py sys.path: {sys.path}\n")
sys.stderr.write(f"DEBUG: run_bridge_loop.py PYTHONPATH ENV: {os.environ.get('PYTHONPATH')}\n")
sys.stderr.flush()

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s", stream=sys.stderr)

class BridgeLoop:
    def __init__(
        self,
        app_config: AppConfig,
        agent_id: int,
        prompt_source: Path,
        outbox_dir: Path,
        window_title: str,
        coords_cfg: Path,
        chat_url: str,
        poll_interval: float = 2.5,
        response_timeout: int = 60,
    ):
        self.app_config = app_config
        self.agent_id = agent_id
        self.prompt_source = prompt_source
        self.outbox_dir = outbox_dir
        self.window_title = window_title
        self.poll_interval = poll_interval
        self.response_timeout = response_timeout
        self.chat_url = chat_url

        raw_coords = json.loads(Path(coords_cfg).read_text(encoding='utf-8'))
        agent_key = f"Agent-{agent_id}"

        if agent_key in raw_coords:
            agent_coords = raw_coords[agent_key]
        else:
            raise ValueError(f"Agent '{agent_key}' not found in {coords_cfg}")

        self.coords = {
            "chat_input_field": [agent_coords["input_box"]["x"], agent_coords["input_box"]["y"]],
            "copy_button": [agent_coords["copy_button"]["x"], agent_coords["copy_button"]["y"]],
        }
        self.cursor = CursorInjector(window_title=window_title, coords=self.coords)
        logger.debug("BridgeLoop.__init__ - About to instantiate ResponseHandler")
        self.scraper = ResponseHandler(timeout=response_timeout, poll_interval=poll_interval)
        logger.debug("BridgeLoop.__init__ - Successfully instantiated ResponseHandler")

        self._should_stop = False
        signal.signal(signal.SIGINT, self._sigint_handler)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)

    def _default_queue_fn(self, prompt_text: str):
        """Placeholder function for handling prompts when all models fail."""
        logger.error(f"QUEUE_FN (Default): All models failed. Prompt dropped: {prompt_text[:100]}...")
        # In a real system, this might save to a file, database, or retry queue.

    def run(self) -> None:
        logger.info("BridgeLoop.run() called") 
        try:
            if not self.scraper or not self.scraper.driver:
                logger.error("Scraper or driver not initialized, cannot run bridge loop.")
                return

            logger.info("Ensuring login session (on chatgpt.com)...")
            if not self.scraper.ensure_login_session(): # Uses updated chatgpt.com logic
                logger.error("Login session failed or was not established. Exiting bridge loop.")
                return
            logger.info("Login session established on chatgpt.com.")

            # Ensure we are on the target page (which includes model parameter if provided)
            logger.info(f"Ensuring browser is on target chat page: {self.chat_url}")
            try:
                # ensure_chat_page will navigate if needed (e.g., to specific model URL)
                self.scraper.ensure_chat_page(self.chat_url) 
                logger.info(f"Confirmed browser is on target chat page: {self.chat_url}")
            except Exception as page_e:
                logger.error(f"Failed to navigate/confirm target page {self.chat_url}. Exiting. Error: {page_e}", exc_info=True)
                return

            prompts = self._load_prompts()
            if not prompts:
                logger.warning("No prompts found to process.")
                return

            for prompt_text in prompts:
                if self._should_stop:
                    logger.info("Stop signal received, breaking prompt loop.")
                    break
                
                logger.info(f"--- Processing prompt: {prompt_text[:100]}... ---")
                
                # EDIT START: Switch to direct send_prompt logic (Option B)
                # OPTION A: Use prompt_with_fallback 
                # response = self.scraper.prompt_with_fallback(
                #     prompt=prompt_text,
                #     preferred_models=["GPT-4o", "GPT-4", "GPT-3.5"], # Or determine dynamically
                #     queue_fn=self._default_queue_fn 
                # )

                # OPTION B: Simple send/wait (if URL parameter handles model selection reliably)
                # Assumes ensure_chat_page already navigated to the correct model URL
                logger.info(f"Sending prompt directly (model selected via URL: {self.chat_url})...")
                if not self.scraper.send_prompt(prompt_text):
                     logger.error("Failed to send prompt. Skipping...")
                     response = "<SEND_FAILED>"
                else:
                     logger.info("Prompt sent. Waiting for stable response...")
                     response = self.scraper.wait_for_stable_response()
                # EDIT END

                # Persist the result 
                self._persist_response(prompt_text, response) 
                
                if not response or response == "<SEND_FAILED>": # Assuming prompt_with_fallback might return <SEND_FAILED> or empty on total failure
                     logger.warning("No response received or send failed for this prompt.")

            logger.info("Bridge loop finished processing prompts.")
        
        except Exception as e:
             logger.error(f"Exception during BridgeLoop.run execution: {e}", exc_info=True)

        finally:
            if hasattr(self, 'scraper') and self.scraper is not None:
                logger.info("BridgeLoop.run() finally - Calling scraper.shutdown()")
                self.scraper.shutdown()

    def _load_prompts(self) -> list[str]:
        if self.prompt_source.is_dir():
            files = sorted(self.prompt_source.glob("*.txt"))
            return [f.read_text(encoding='utf-8').strip() for f in files]
        return [self.prompt_source.read_text(encoding='utf-8').strip()]

    def _persist_response(self, prompt: str, resp: Optional[str]) -> None:
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        outfile = self.outbox_dir / f"agent{self.agent_id}_{ts}.json"
        outfile.write_text(
            json.dumps(
                {"prompt": prompt, "response": resp, "timestamp": ts}, indent=2
            ),
            encoding='utf-8'
        )
        logger.info(f"INFO: [Save] Saved → {outfile}")

    def _sigint_handler(self, *_):
        logger.info("\nINFO: [Stop] CTRL‑C detected — stopping after current iteration.")
        self._should_stop = True

def cli() -> None:
    logger.info("run_bridge_loop.py - cli() called")
    try:
        parser = argparse.ArgumentParser(description="Run Cursor ↔ THEA bridge loop")
        parser.add_argument("--agent-id", type=int, required=True, help="Agent numeric ID")
        parser.add_argument("--prompt-file", type=Path, required=True, help="Path to a .txt prompt file OR directory of .txt prompts")
        parser.add_argument("--coords", type=Path, default=Path("runtime/config/cursor_agent_coords.json"), help="JSON file with screen‑coords for Cursor UI elements")
        parser.add_argument("--window-title", default=GuiAutomationConfig().target_window_title, help="Substring of Cursor window title to activate")
        parser.add_argument("--outbox", type=Path, default=Path("runtime/bridge_outbox"), help="Folder to write response JSONs")
        parser.add_argument("--response-timeout", type=int, default=180, help="Seconds to wait for stable response")
        parser.add_argument("--chat-url", type=str, default="https://chat.openai.com/chat", help="Base URL for chat interaction")
        args = parser.parse_args()

        logger.info("run_bridge_loop.py - In cli(), before AppConfig() instantiation.")
        app_config = AppConfig()
        logger.info("run_bridge_loop.py - In cli(), after AppConfig() instantiation.")

        loop = BridgeLoop(
            app_config=app_config,
            agent_id=args.agent_id,
            prompt_source=args.prompt_file,
            outbox_dir=args.outbox,
            window_title=args.window_title,
            coords_cfg=args.coords,
            chat_url=args.chat_url,
            response_timeout=args.response_timeout,
        )
        logger.info("run_bridge_loop.py - BridgeLoop instantiated, calling loop.run()")
        loop.run()
        logger.info("run_bridge_loop.py - loop.run() completed.")
    except Exception as e_cli:
        logger.critical(f"FATAL ERROR in run_bridge_loop.py cli(): {type(e_cli).__name__} - {e_cli}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    logger.info("run_bridge_loop.py - __main__ block executing")
    cli()
    logger.info("run_bridge_loop.py - cli() finished.") 