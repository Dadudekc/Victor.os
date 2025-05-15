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
import traceback
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from ..core.config import AppConfig
from ..agents.utils.agent_utils import format_agent_report
from .cursor_orchestrator import CursorOrchestrator
from .response_retriever import ResponseRetriever
from .jarvis_core import JarvisCore
from .interaction import InteractionManager

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

def process_with_jarvis(prompt: str, agent_id: str, jarvis: JarvisCore, 
                        interaction_manager: InteractionManager) -> Tuple[Dict[str, Any], bool]:
    """Process agent prompt with JARVIS.
    
    Args:
        prompt: The prompt to process
        agent_id: ID of the agent
        jarvis: JARVIS core instance
        interaction_manager: Interaction manager instance
        
    Returns:
        Tuple of (JARVIS response, success flag)
    """
    try:
        if not jarvis.is_active:
            logger.warning("JARVIS is not active, activating...")
            jarvis.activate()
            
        # Create a task for JARVIS to coordinate with the agent
        task = {
            "id": f"task_{int(time.time())}",
            "type": "agent_coordination",
            "agent_id": agent_id,
            "message": prompt,
            "description": f"Coordinate with {agent_id}"
        }
        
        # Execute the task
        result = jarvis.execute_task(task)
        
        # Process the prompt through interaction patterns
        response = interaction_manager.process_input(prompt, source=agent_id)
        
        # Combine task result and interaction response
        combined_response = {
            "task_result": result,
            "interaction_response": response,
            "timestamp": datetime.now().isoformat()
        }
        
        return combined_response, True
        
    except Exception as e:
        logger.error(f"Error processing with JARVIS: {str(e)}")
        logger.debug(f"JARVIS error details: {traceback.format_exc()}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "fallback": "Using classic response pipeline"
        }, False

def run_episode5_loop(jarvis: Optional[JarvisCore] = None, 
                      interaction_manager: Optional[InteractionManager] = None,
                      dry_run: bool = False):
    """Main loop for Episode 5 automation.
    
    Args:
        jarvis: Optional JARVIS core instance
        interaction_manager: Optional interaction manager instance
        dry_run: If True, only test connections but don't perform actions
    """
    logger.info("Starting Episode 5 automation loop...")
    
    if dry_run:
        logger.info("Running in DRY RUN mode - no actions will be performed")
    
    config = AppConfig.load()
    orchestrator = CursorOrchestrator(config)
    retriever = ResponseRetriever(config)
    
    # Initialize JARVIS if not provided
    jarvis_available = False
    if jarvis is None:
        try:
            jarvis = JarvisCore()
            jarvis.activate()
            jarvis_available = True
            logger.info("JARVIS initialized and activated successfully")
        except Exception as e:
            logger.error(f"Failed to initialize JARVIS: {str(e)}")
            jarvis_available = False
    else:
        jarvis_available = jarvis.is_active
        
    # Initialize interaction manager if not provided
    if interaction_manager is None and jarvis_available:
        try:
            interaction_manager = InteractionManager(jarvis)
            logger.info("InteractionManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize InteractionManager: {str(e)}")
            jarvis_available = False

    if dry_run:
        # In dry run mode, just verify connections and exit
        logger.info(f"JARVIS available: {jarvis_available}")
        if jarvis_available:
            logger.info(f"JARVIS status: {jarvis._get_system_state()}")
            
        # Test loading a prompt
        for agent_id in AGENT_IDS[:1]:  # Just test the first agent
            prompt = load_agent_prompt(agent_id)
            logger.info(f"Agent {agent_id} prompt available: {bool(prompt)}")
            
            if jarvis_available and prompt:
                # Test JARVIS processing
                try:
                    response, success = process_with_jarvis(
                        prompt, agent_id, jarvis, interaction_manager)
                    logger.info(f"JARVIS processing test: {'Success' if success else 'Failed'}")
                except Exception as e:
                    logger.error(f"JARVIS processing test failed: {str(e)}")
        
        logger.info("Dry run completed")
        return
    
    try:
        for agent_id in AGENT_IDS:
            try:
                prompt = load_agent_prompt(agent_id)
                if not prompt:
                    logger.debug(f"No prompt found for {agent_id}")
                    continue

                logger.info(f"Processing task for {agent_id}")
                
                # Process with JARVIS if available
                jarvis_response = None
                jarvis_success = False
                
                if jarvis_available:
                    try:
                        jarvis_response, jarvis_success = process_with_jarvis(
                            prompt, agent_id, jarvis, interaction_manager)
                        if jarvis_success:
                            logger.info(f"JARVIS processed prompt for {agent_id}")
                        else:
                            logger.warning(f"JARVIS failed to process prompt for {agent_id}, falling back to classic pipeline")
                    except Exception as e:
                        logger.error(f"Error in JARVIS processing: {str(e)}")
                        jarvis_success = False
                
                # Continue with normal orchestration (always run as fallback)
                orchestrator.injection_task(agent_id, prompt)
                time.sleep(3)  # Brief wait before retrieval
                
                response = retriever.retrieve_agent_response(agent_id)
                if response:
                    # Enhance response with JARVIS insights if available
                    enhanced_response = response
                    if jarvis_success and jarvis_response:
                        jarvis_content = jarvis_response.get("interaction_response", {}).get("content", "")
                        if jarvis_content:
                            enhanced_response = f"{response}\n\nJARVIS insights: {jarvis_content}"
                    
                    save_agent_output(agent_id, enhanced_response)
                    log_reflection(agent_id, prompt, enhanced_response)
                    logger.info(f"[{agent_id}] Cycle complete")
                else:
                    logger.warning(f"No response retrieved for {agent_id}")

            except Exception as e:
                logger.error(f"[{agent_id}] Error during episode5 loop: {e}", exc_info=True)
                # Continue processing other agents despite errors

        time.sleep(LOOP_INTERVAL)
        
    except Exception as e:
        logger.error(f"Error in episode5 loop: {e}", exc_info=True)
        
        # Ensure JARVIS stays active if it was working
        if jarvis and jarvis_available and not jarvis.is_active:
            try:
                jarvis.activate()
            except:
                pass

def run_episode5_loop_with_fallback(max_retries: int = 3, dry_run: bool = False):
    """Run the episode5 loop with fallback and retry logic.
    
    Args:
        max_retries: Maximum number of retries for JARVIS initialization
        dry_run: If True, only test connections but don't perform actions
    """
    jarvis = None
    interaction_manager = None
    retry_count = 0
    
    if dry_run:
        # For dry run, just run once without retries
        try:
            jarvis = JarvisCore()
            jarvis.activate()
            interaction_manager = InteractionManager(jarvis)
            run_episode5_loop(jarvis, interaction_manager, dry_run=True)
        except Exception as e:
            logger.error(f"Dry run failed: {str(e)}")
        return
    
    while retry_count < max_retries:
        try:
            # Try to initialize JARVIS
            if jarvis is None:
                jarvis = JarvisCore()
                jarvis.activate()
                interaction_manager = InteractionManager(jarvis)
                logger.info("Successfully initialized JARVIS for episode5 loop")
                
            # Run the main loop
            run_episode5_loop(jarvis, interaction_manager)
            retry_count = 0  # Reset retry count on success
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Episode5 loop failed (retry {retry_count}/{max_retries}): {str(e)}")
            
            # Try to recover JARVIS
            if jarvis:
                try:
                    if jarvis.is_active:
                        jarvis.deactivate()
                    jarvis.activate()
                    logger.info("Recovered JARVIS after failure")
                except:
                    logger.error("Failed to recover JARVIS, will retry with new instance")
                    jarvis = None
                    interaction_manager = None
            
            # Wait before retrying
            time.sleep(5)
            
            # On last retry, run without JARVIS
            if retry_count >= max_retries:
                logger.warning(f"Maximum retries ({max_retries}) reached, running without JARVIS")
                run_episode5_loop(None, None)
                retry_count = 0  # Reset for next iteration

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Episode 5 automation loop')
    parser.add_argument('--dry-run', action='store_true', help='Test connections without performing actions')
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    run_episode5_loop_with_fallback(dry_run=args.dry_run) 