#!/usr/bin/env python3
"""Episode 5 automation script for autonomous agent coordination.

This script implements a closed-loop automation system that:
1. Loads each agent's self-generated tasks
2. Injects prompts via coordinate mapping
3. Copies responses back
4. Stores reflections
5. Runs autonomously in a continuous loop
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..core.config import AppConfig
from ..agents.utils.agent_utils import format_agent_report
from .cursor_orchestrator import CursorOrchestrator
from .response_retriever import ResponseRetriever

# Configure logging
logger = logging.getLogger(__name__)

# Constants
AGENT_IDS = [f"Agent-{i}" for i in range(1, 9)]
INBOX_BASE = Path("runtime/agent_comms/agent_mailboxes")
OUTBOX_BASE = Path("runtime/bridge_outbox")
REFLECTION_LOG = Path("runtime/devlog/agent_reflections.log")
LOOP_INTERVAL = 15  # seconds

def load_agent_prompt(agent_id: str) -> str:
    """Load the latest prompt from an agent's inbox."""
    inbox_path = INBOX_BASE / agent_id / "inbox.json"
    if inbox_path.exists():
        try:
            with open(inbox_path) as f:
                data = json.load(f)
                if data:
                    return data[0].get("prompt") or data[0].get("description", "")
        except Exception as e:
            logger.error(f"Error loading prompt for {agent_id}: {e}")
    return ""

def save_agent_output(agent_id: str, response: str):
    """Save agent's response to the outbox."""
    outbox_path = OUTBOX_BASE / f"{agent_id}_response.json"
    outbox_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(outbox_path, "w") as f:
            json.dump({
                "agent": agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "response": response
            }, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving output for {agent_id}: {e}")

def log_reflection(agent_id: str, prompt: str, response: str):
    """Log agent's reflection to the devlog."""
    try:
        reflection = format_agent_report(
            agent_id=agent_id,
            task=prompt,
            status="✅ Complete",
            action=f"Processed response: {response[:100]}..."
        )
        with open(REFLECTION_LOG, "a") as log_file:
            log_file.write(f"\n--- {datetime.utcnow().isoformat()} ---\n")
            log_file.write(reflection + "\n")
    except Exception as e:
        logger.error(f"Error logging reflection for {agent_id}: {e}")

def run_episode5_loop():
    """Main loop for Episode 5 automation."""
    logger.info("Starting Episode 5 automation loop...")
    
    config = AppConfig.load()
    orchestrator = CursorOrchestrator(config)
    retriever = ResponseRetriever(config)

    while True:
        for agent_id in AGENT_IDS:
            try:
                prompt = load_agent_prompt(agent_id)
                if not prompt:
                    logger.debug(f"No prompt found for {agent_id}")
                    continue

                logger.info(f"Processing task for {agent_id}")
                orchestrator.injection_task(agent_id, prompt)
                time.sleep(3)  # Brief wait before retrieval
                
                response = retriever.retrieve_agent_response(agent_id)
                if response:
                    save_agent_output(agent_id, response)
                    log_reflection(agent_id, prompt, response)
                    logger.info(f"[{agent_id}] Cycle complete")
                else:
                    logger.warning(f"No response retrieved for {agent_id}")

            except Exception as e:
                logger.error(f"[{agent_id}] Error during episode5 loop: {e}", exc_info=True)

        time.sleep(LOOP_INTERVAL)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    run_episode5_loop() 