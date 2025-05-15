"""
Dream.OS Agent Onboarding Script

This script handles onboarding for all agents (1-8) by:
1. Creating necessary directories and files
2. Setting up initial state
3. Sending onboarding messages
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .config import AgentConfig, validate_agent_id
from .messaging import create_seed_inbox
from .validation import validate_all_files

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Agent charters
AGENT_CHARTERS = {
    "Agent-1": "SYSTEM ARCHITECTURE",
    "Agent-2": "ESCALATION WATCH",
    "Agent-3": "CREATIVE SOLUTIONS",
    "Agent-4": "USER INTERACTION",
    "Agent-5": "KNOWLEDGE INTEGRATION",
    "Agent-6": "STRATEGIC PLANNING",
    "Agent-7": "IMPLEMENTATION",
    "Agent-8": "GOVERNANCE & ETHICS"
}

async def onboard_agent(agent_id: str) -> bool:
    """
    Onboard a single agent.
    
    Args:
        agent_id: Agent ID to onboard
        
    Returns:
        bool: True if onboarding was successful
    """
    try:
        logger.info(f"Starting onboarding for {agent_id}")
        
        # Create agent config
        config = AgentConfig(agent_id=agent_id)
        
        # Create directories
        config._ensure_directories()
        logger.info(f"Created directories for {agent_id}")
        
        # Create initial state file
        create_seed_inbox(logger, config)
        logger.info(f"Created initial state file for {agent_id}")
        
        # Validate setup
        await asyncio.sleep(5)  # Allow files to be created
        validation = validate_all_files(logger, config)
        if not validation.passed:
            logger.error(f"Validation failed: {validation.error}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to onboard {agent_id}: {e}")
        return False

async def onboard_all_agents(agents: Optional[List[str]] = None) -> bool:
    """
    Onboard all agents or specific agents.
    
    Args:
        agents: List of agent IDs to onboard, or None for all agents
        
    Returns:
        bool: True if all agents were onboarded successfully
    """
    try:
        logger.info("Starting onboarding sequence in 10 seconds...")
        await asyncio.sleep(10)
        
        # Get list of agents to onboard
        if agents:
            agent_list = agents
        else:
            agent_list = [f"Agent-{i}" for i in range(1, 9)]  # Agents 1-8
            
        # Onboard each agent
        results = {}
        for agent_id in agent_list:
            if not validate_agent_id(agent_id):
                logger.error(f"Invalid agent ID: {agent_id}")
                continue
                
            success = await onboard_agent(agent_id)
            results[agent_id] = success
            
            if not success:
                logger.error(f"Failed to onboard {agent_id}")
                logger.error("Stopping onboarding sequence due to failure")
                break
                
        # Print results
        logger.info("\nOnboarding Results:")
        logger.info("--------------------")
        for agent_id, success in results.items():
            status = "✅ Success" if success else "❌ Failed"
            logger.info(f"{agent_id}: {status}")
            
        return all(results.values())
        
    except Exception as e:
        logger.error(f"Onboarding sequence failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Dream.OS Agent Onboarding")
    parser.add_argument(
        "--agents",
        nargs="+",
        help="Specific agents to onboard (e.g. Agent-1 Agent-2)"
    )
    args = parser.parse_args()
    
    try:
        asyncio.run(onboard_all_agents(args.agents))
    except KeyboardInterrupt:
        logger.info("\nOnboarding interrupted by user")
        sys.exit(1) 