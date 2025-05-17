#!/usr/bin/env python3
"""
Dream.OS Universal Agent Bootstrap Runner – Refactored

• Cleaner structure & typing
• Centralised constants
• Robust logging (no duplicate handlers)
• Async-friendly shutdown
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import json

from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.utils.gui.injector import CursorInjector
from dreamos.utils.gui.retriever import ResponseRetriever
from .validation import validate_all_files

################################################################################
# CONFIG
################################################################################

RUNTIME_DIR          = Path("runtime")
PROMPT_DIR_DEFAULT   = RUNTIME_DIR / "prompts"
MAILBOX_ROOT         = RUNTIME_DIR / "agent_comms" / "agent_mailboxes"
DEVLOG_DIR           = RUNTIME_DIR / "devlog" / "agents"

HEARTBEAT_SEC        = int(os.getenv("AGENT_HEARTBEAT_SEC", 30))
LOOP_DELAY_SEC       = int(os.getenv("AGENT_LOOP_DELAY_SEC", 5))
RESPONSE_WAIT_SEC    = int(os.getenv("AGENT_RESPONSE_WAIT_SEC", 15))
RETRIEVE_RETRIES     = int(os.getenv("AGENT_RETRIEVE_RETRIES", 3))
RETRY_DELAY_SEC      = int(os.getenv("AGENT_RETRY_DELAY_SEC", 2))
STARTUP_DELAY_SEC    = int(os.getenv("AGENT_STARTUP_DELAY_SEC", 30))

################################################################################
# LOGGING
################################################################################

logging.basicConfig(
    level=os.getenv("AGENT_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
ROOT_LOG = logging.getLogger("bootstrap")


def init_agent_logger(agent_id: str) -> logging.Logger:
    """Return a logger unique to this agent with its own FileHandler."""
    logger = logging.getLogger(f"Agent.{agent_id}")
    if any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        return logger  # already initialised

    DEVLOG_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(DEVLOG_DIR / f"{agent_id.lower()}.log")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    logger.setLevel(os.getenv(f"AGENT_LOG_LEVEL_{agent_id.upper()}", "INFO"))
    return logger


################################################################################
# DATA CLASSES
################################################################################

# Define AGENT_STATE_FILE path globally for the new function
AGENT_STATE_FILE = Path("runtime/state/agent_last_activity.json")

def update_agent_activity(agent_id: str, logger_instance: logging.Logger):
    """Update the agent's last activity timestamp in a central JSON file."""
    try:
        AGENT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if AGENT_STATE_FILE.exists():
            try:
                with open(AGENT_STATE_FILE, "r") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                logger_instance.warning(f"Could not decode {AGENT_STATE_FILE}, initializing new state.")
                data = {}
        else:
            data = {}
        
        data[agent_id] = datetime.now(timezone.utc).isoformat()
        
        with open(AGENT_STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)
        logger_instance.debug(f"Updated last activity for {agent_id} in {AGENT_STATE_FILE}")
    except Exception as e:
        logger_instance.error(f"Failed to update agent activity for {agent_id}: {e}")


@dataclass(slots=True)
class AgentConfig:
    agent_id: str
    prompt: Optional[str] = None
    prompt_file: Optional[str] = None
    prompt_dir: Path = PROMPT_DIR_DEFAULT
    heartbeat_sec: int = HEARTBEAT_SEC
    loop_delay_sec: int = LOOP_DELAY_SEC
    response_wait_sec: int = RESPONSE_WAIT_SEC
    retrieve_retries: int = RETRIEVE_RETRIES
    retry_delay_sec: int = RETRY_DELAY_SEC
    startup_delay_sec: int = STARTUP_DELAY_SEC

    @property
    def num(self) -> str:
        return self.agent_id.split("-")[1]

    @property
    def traits(self) -> Dict[str, List[str]]:
        traits_map = {
            "1": ["Analytical", "Logical", "Methodical", "Precise"],
            "2": ["Vigilant", "Proactive", "Methodical", "Protective"],
            "3": ["Creative", "Innovative", "Intuitive", "Exploratory"],
            "4": ["Communicative", "Empathetic", "Diplomatic", "Persuasive"],
            "5": ["Knowledgeable", "Scholarly", "Thorough", "Informative"],
            "6": ["Strategic", "Visionary", "Decisive", "Forward-thinking"],
            "7": ["Adaptive", "Resilient", "Practical", "Resourceful"],
            "8": ["Ethical", "Balanced", "Principled", "Thoughtful"],
        }
        return {"traits": traits_map.get(self.num, [])}


################################################################################
# RUNNER
################################################################################

class AgentBootstrapRunner:
    def __init__(self, cfg: AgentConfig):
        self.cfg       = cfg
        self.logger    = init_agent_logger(cfg.agent_id)
        self.bus       = AgentBus()
        self.injector  = CursorInjector(cfg.agent_id)
        self.retriever = ResponseRetriever(cfg.agent_id)

        # paths
        self.agent_dir     = MAILBOX_ROOT / cfg.agent_id
        self.inbox_dir     = self.agent_dir / "inbox"
        self.processed_dir = self.agent_dir / "processed"
        self.state_dir     = self.agent_dir / "state"
        self.archive_dir   = self.agent_dir / "archive"

        for d in (self.inbox_dir, self.processed_dir, self.state_dir, self.archive_dir):
            d.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------------- utils
    async def _validate(self):
        res = validate_all_files(self.logger, self.cfg, is_onboarding=True)
        if not res.passed:
            raise RuntimeError(f"Validation failed: {res.error}")

    async def _load_prompt(self) -> str:
        if self.cfg.prompt:
            return self.cfg.prompt

        p_file = Path(self.cfg.prompt_file) if self.cfg.prompt_file else \
                 self.cfg.prompt_dir / f"{self.cfg.agent_id.lower()}.txt"

        if not p_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {p_file}")
        return p_file.read_text(encoding="utf-8").strip()

    # ------------------------------------------------------------------- cycle
    async def _cycle(self):
        try:
            prompt = await self._load_prompt()
            self.logger.info("Injecting prompt (%s chars)", len(prompt))
            # The very first injection to an agent window uses the
            # *initial* coordinates captured during calibration.
            await self.injector.inject_text(prompt, is_initial_prompt=True)
            self.logger.info("Prompt injected. Waiting for response...")


            response = await self.retriever.get_response()
            self.logger.info("Response %s", "received" if response else "not found")

            if response:
                ts   = int(datetime.now(timezone.utc).timestamp())
                path = self.processed_dir / f"response.{ts}.txt"
                path.write_text(response, encoding="utf-8")

                await self.bus.publish("agent.response", {
                    "agent_id": self.cfg.agent_id,
                    "timestamp": ts,
                    "response_file": str(path),
                })

            # Add the call to update_agent_activity here
            update_agent_activity(self.cfg.agent_id, self.logger)

        except Exception as e:
            self.logger.error("Cycle error: %s", e, exc_info=True)
            await self.bus.publish("agent.error", {
                "agent_id": self.cfg.agent_id,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).timestamp(),
            })

    # -------------------------------------------------------------------- main
    async def run(self, once: bool = False):
        await self._validate()

        if not once and self.cfg.startup_delay_sec:
            self.logger.info("Startup delay %ss", self.cfg.startup_delay_sec)
            await asyncio.sleep(self.cfg.startup_delay_sec)

        try:
            while True:
                await self._cycle()
                if once:
                    return
                await asyncio.sleep(self.cfg.loop_delay_sec)
        except asyncio.CancelledError:
            self.logger.info("Runner cancelled – shutting down.")


################################################################################
# CLI / ENTRY
################################################################################

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("Dream.OS Agent Runner")
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument("--agent", help="Run single agent e.g. Agent-3")
    g.add_argument("--all-agents", action="store_true", help="Run Agents 1-8 once")
    p.add_argument("--once", action="store_true", help="Single cycle then exit")
    p.add_argument("--no-delay", action="store_true", help="Skip startup delay")
    p.add_argument("--prompt", help="Override prompt text")
    p.add_argument("--prompt-file")
    p.add_argument("--prompt-dir", default=str(PROMPT_DIR_DEFAULT))
    p.add_argument("--list-prompts", action="store_true")
    return p.parse_args()


async def orchestrate(agent_id: str, args: argparse.Namespace, once: bool):
    # EDIT START: Determine the effective prompt file (copied from previous version)
    effective_prompt_file = args.prompt_file
    if not args.prompt and not args.prompt_file: # Neither direct prompt nor specific file provided
        # Default to the standard onboarding prompt
        # Ensure PROMPT_DIR_DEFAULT is used here as args.prompt_dir might be different
        # if user explicitly changes it but doesn't provide a specific prompt file.
        # However, the AgentConfig will use args.prompt_dir anyway.
        # This logic is primarily to decide if we *force* default_onboarding.txt.
        default_onboarding_path = PROMPT_DIR_DEFAULT / "default_onboarding.txt"
        if default_onboarding_path.exists():
            effective_prompt_file = str(default_onboarding_path)
            # Use ROOT_LOG here as agent-specific logger isn't created yet
            ROOT_LOG.info(f"No specific prompt or prompt file given for {agent_id}, using default onboarding: {effective_prompt_file}")
        else:
            ROOT_LOG.warning(f"Default onboarding prompt {default_onboarding_path} not found for {agent_id}. Agent may not follow standard EP03 activation.")
    # EDIT END

    cfg = AgentConfig(
        agent_id      = agent_id,
        prompt        = args.prompt,
        prompt_file   = effective_prompt_file, # MODIFIED: Use effective_prompt_file
        prompt_dir    = Path(args.prompt_dir), # Ensure this is Path
        startup_delay_sec = 0 if args.no_delay else STARTUP_DELAY_SEC,
    )
    runner = AgentBootstrapRunner(cfg)
    # Log the prompt source decision (copied from previous version for clarity)
    prompt_source_msg = "direct" if cfg.prompt else (f"file {cfg.prompt_file}" if cfg.prompt_file else f"default dir ({cfg.prompt_dir})")
    runner.logger.info(f"Orchestrated run for {agent_id} with run_once={once}. Prompt source: {prompt_source_msg}")
    await runner.run(once=once)


async def main_async():
    args = parse_args()

    # Default to --all-agents --once if no specific agent mode is selected
    if not args.agent and not args.all_agents and not args.list_prompts:
        ROOT_LOG.info("No specific agent or mode selected, defaulting to --all-agents --once.")
        args.all_agents = True
        args.once = True # Defaulting to all_agents should also imply once for safety/clarity

    if args.list_prompts:
        p_dir = Path(args.prompt_dir)
        ROOT_LOG.info("Prompt files in %s:", p_dir)
        for f in p_dir.glob("*.txt"):
            print(" •", f.name)
        return

    if args.all_agents:
        ROOT_LOG.info("Bootstrapping Agents 1-8...")
        for i in range(1, 9):
            aid = f"Agent-{i}"
            ROOT_LOG.info(">>> %s", aid)
            # When --all-agents is specified (or defaulted to), always run once.
            await orchestrate(aid, args, once=True) 
            if i < 8:
                await asyncio.sleep(5)
    else: # This means args.agent must be set due to mutually_exclusive_group
        # Add a check for args.agent, as it's no longer guaranteed by required=True
        if args.agent:
            await orchestrate(args.agent, args, once=args.once)
        # If neither all_agents nor agent is specified, and not list_prompts, 
        # it implies we already defaulted to all_agents, so this else branch might not be hit
        # in that specific default scenario if list_prompts was also false. The top check handles it.


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        ROOT_LOG.info("Terminated by user.")
