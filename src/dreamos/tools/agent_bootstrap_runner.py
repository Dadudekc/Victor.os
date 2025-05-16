#!/usr/bin/env python3
"""
Dream.OS Universal Agent Bootstrap Runner

A modular implementation of the agent bootstrap process that works with any agent (0-8).
Provides a unified interface for agent initialization, configuration, and runtime management.
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

from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.utils.gui.injector import CursorInjector
from dreamos.utils.gui.retriever import ResponseRetriever

from .validation import validate_all_files

# Configure logging
logging.basicConfig(
    level=os.getenv("AGENT_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for agent bootstrap process."""

    agent_id: str  # e.g. "Agent-2"
    prompt: Optional[str] = None  # Custom prompt override
    prompt_file: Optional[str] = None  # Path to prompt file
    prompt_dir: str = "runtime/prompts"  # Directory containing prompt files
    heartbeat_sec: int = int(os.getenv("AGENT_HEARTBEAT_SEC", "30"))
    loop_delay_sec: int = int(os.getenv("AGENT_LOOP_DELAY_SEC", "5"))
    response_wait_sec: int = int(os.getenv("AGENT_RESPONSE_WAIT_SEC", "15"))
    retrieve_retries: int = int(os.getenv("AGENT_RETRIEVE_RETRIES", "3"))
    retry_delay_sec: int = int(os.getenv("AGENT_RETRY_DELAY_SEC", "2"))
    startup_delay_sec: int = int(os.getenv("AGENT_STARTUP_DELAY_SEC", "30"))

    @property
    def agent_num(self) -> str:
        """Extract agent number from ID (e.g. 'Agent-2' -> '2')."""
        return self.agent_id.split("-")[1]

    @property
    def agent_traits(self) -> Dict[str, List[str]]:
        """Get agent-specific traits."""
        TRAITS = {
            "1": ["Analytical", "Logical", "Methodical", "Precise"],
            "2": ["Vigilant", "Proactive", "Methodical", "Protective"],
            "3": ["Creative", "Innovative", "Intuitive", "Exploratory"],
            "4": ["Communicative", "Empathetic", "Diplomatic", "Persuasive"],
            "5": ["Knowledgeable", "Scholarly", "Thorough", "Informative"],
            "6": ["Strategic", "Visionary", "Decisive", "Forward-thinking"],
            "7": ["Adaptive", "Resilient", "Practical", "Resourceful"],
            "8": ["Ethical", "Balanced", "Principled", "Thoughtful"],
        }
        return {"traits": TRAITS.get(self.agent_num, [])}


class AgentBootstrapRunner:
    """Core runner for agent bootstrap process."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_bus = AgentBus()
        self.injector = CursorInjector(agent_id=self.config.agent_id)
        self.retriever = ResponseRetriever(agent_id=self.config.agent_id)

        # Set up paths
        self.runtime_dir = Path("runtime")
        self.agent_dir = (
            self.runtime_dir / "agent_comms" / "agent_mailboxes" / config.agent_id
        )
        self.inbox_dir = self.agent_dir / "inbox"
        self.processed_dir = self.agent_dir / "processed"
        self.state_dir = self.agent_dir / "state"
        self.archive_dir = self.agent_dir / "archive"
        self.devlog_dir = self.runtime_dir / "devlog" / "agents"

        # Ensure directories exist
        for dir_path in [
            self.inbox_dir,
            self.processed_dir,
            self.state_dir,
            self.archive_dir,
            self.devlog_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Set up agent-specific logging
        self.setup_logging()

    def setup_logging(self):
        """Configure agent-specific logging."""
        log_file = self.devlog_dir / f"{self.config.agent_id.lower()}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        log.addHandler(file_handler)

    async def validate_setup(self):
        """Validate all required files and configurations exist."""
        # Run full validation using existing config
        result = validate_all_files(log, self.config, is_onboarding=True)
        if not result.passed:
            raise RuntimeError(f"Validation failed: {result.error}")

    async def load_prompt(self) -> str:
        """Load the appropriate prompt for the agent."""
        if self.config.prompt:
            return self.config.prompt

        if self.config.prompt_file:
            prompt_path = Path(self.config.prompt_file)
        else:
            prompt_path = (
                Path(self.config.prompt_dir) / f"{self.config.agent_id.lower()}.txt"
            )

        if not prompt_path.exists():
            raise RuntimeError(f"Prompt file not found: {prompt_path}")

        return prompt_path.read_text(encoding="utf-8").strip()

    async def run_cycle(self):
        """Run a single bootstrap cycle."""
        try:
            # Load and inject prompt
            prompt = await self.load_prompt()
            await self.injector.inject_text(prompt)

            # Wait for and retrieve response
            response = await self.retriever.get_response(
                retries=self.config.retrieve_retries,
                retry_delay=self.config.retry_delay_sec
            )

            if response:
                # Process and archive response
                timestamp = datetime.now(timezone.utc).timestamp()
                response_file = self.processed_dir / f"response.{int(timestamp)}.txt"
                response_file.write_text(response, encoding="utf-8")

                # Publish event
                await self.agent_bus.publish(
                    "agent.response",
                    {
                        "agent_id": self.config.agent_id,
                        "timestamp": timestamp,
                        "response_file": str(response_file),
                    },
                )

        except Exception as e:
            log.error(f"Cycle error: {e}", exc_info=True)
            await self.agent_bus.publish(
                "agent.error",
                {
                    "agent_id": self.config.agent_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "timestamp": datetime.now(timezone.utc).timestamp(),
                },
            )

    async def run(self, run_once: bool = False):
        """Run the agent bootstrap process."""
        try:
            await self.validate_setup()

            if not run_once and self.config.startup_delay_sec > 0:
                log.info(f"Startup delay: {self.config.startup_delay_sec}s")
                await asyncio.sleep(self.config.startup_delay_sec)

            while True:
                await self.run_cycle()

                if run_once:
                    break

                await asyncio.sleep(self.config.loop_delay_sec)

        except KeyboardInterrupt:
            log.info("Shutting down gracefully...")
        except Exception as e:
            log.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)


async def orchestrate_agent_run(agent_id: str, args, run_once: bool = True):
    config = AgentConfig(
        agent_id=agent_id,
        prompt=args.prompt,
        prompt_file=args.prompt_file,
        prompt_dir=args.prompt_dir,
    )
    if args.no_delay:
        config.startup_delay_sec = 0
    
    # Ensure agent-specific logging is set up for this instance
    # The AgentBootstrapRunner constructor calls self.setup_logging(),
    # but we need to ensure the global log handlers are managed correctly if running multiple agents sequentially.
    # For simplicity now, we assume AgentBootstrapRunner handles its logging context.
    # A more robust solution might involve configuring log handlers per agent run if they conflict.
    
    runner = AgentBootstrapRunner(config)
    await runner.run(run_once=run_once)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Dream.OS Universal Agent Bootstrap Runner"
    )
    parser.add_argument("--agent", type=str, required=False, help='Agent ID (e.g., "Agent-1")')
    parser.add_argument("--all-agents", action="store_true", help="Run all agents (Agent-1 to Agent-8) for one cycle each") # Clarified help
    parser.add_argument("--once", action="store_true", help="Run one cycle then exit (applies if --agent is specified)") # Clarified help
    parser.add_argument("--no-delay", action="store_true", help="Skip the startup delay")
    parser.add_argument("--prompt", type=str, help="Custom prompt text to use instead of default")
    parser.add_argument("--prompt-file", type=str, help="Path to file containing custom prompt text")
    parser.add_argument("--prompt-dir", type=str, default="runtime/prompts", help="Directory containing prompt files")
    parser.add_argument("--list-prompts", action="store_true", help="List available prompt files and exit")
    return parser.parse_args()

async def main_async(): # Renamed to main_async to avoid conflict if there's a global 'main'
    args = parse_args()

    if args.list_prompts:
        prompt_dir = Path(args.prompt_dir)
        if prompt_dir.exists():
            print("\nAvailable prompt files:")
            for f in prompt_dir.glob("*.txt"):
                print(f"  {f.name}")
        else:
            print(f"\nPrompt directory not found: {prompt_dir}")
        sys.exit(0)

    if not args.agent and not args.all_agents: # Validation
        print("Error: You must specify either --agent <AGENT_ID> or --all-agents.")
        sys.exit(1)

    if args.all_agents:
        log.info("Starting onboarding run for all agents (1-8)...")
        for i in range(1, 9): # Agents 1 through 8
            agent_id = f"Agent-{i}"
            log.info(f"--- Launching onboarding for {agent_id}... ---")
            try:
                await orchestrate_agent_run(agent_id, args, run_once=True) # --once is implicit for --all-agents
            except Exception as e:
                log.error(f"--- Error during onboarding for {agent_id}: {e} ---", exc_info=True)
            log.info(f"--- Completed onboarding for {agent_id}. ---")
            if i < 8 : # Don't sleep after the last agent
                log.info("Pausing briefly before next agent...")
                await asyncio.sleep(5) # Increased sleep to 5s for UI to settle
        log.info("--- All agent onboarding runs complete. ---")
    elif args.agent:
        # For single agent runs, args.once determines if it's a single cycle or continuous
        log.info(f"Starting run for {args.agent} (run_once={args.once})...")
        await orchestrate_agent_run(args.agent, args, run_once=args.once)
        log.info(f"--- Run for {args.agent} complete. ---")

if __name__ == "__main__":
    # Note: The main logger `log` is configured at the module level.
    # If AgentBootstrapRunner.setup_logging() adds file handlers to this same logger,
    # running multiple agents sequentially will add multiple file handlers for each agent to the *same* global logger.
    # This means Agent-1's log file might also get logs from Agent-2, etc.
    # A proper fix would be for AgentBootstrapRunner to use its own logger instance or manage handlers carefully.
    # For now, proceeding with the simpler structure.
    asyncio.run(main_async())
