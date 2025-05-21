#!/usr/bin/env python3
"""
Agent Onboarding Script

This script automates the onboarding process for Dream.OS agents using the cellphone system.
It handles initial activation, coordination setup, and verification of agent capabilities.
"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime
import argparse
from agent_cellphone import AgentCellphone, MessageMode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('agent_onboarding')

class AgentOnboarding:
    def __init__(self):
        self.cellphone = AgentCellphone()
        self.registry_file = Path("runtime/agent_registry.json")
        self.registry = self._load_registry()
        
    def _load_registry(self) -> dict:
        """Load agent registry."""
        try:
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return {}
            
    def _update_registry(self, agent_id: str, status: str = "active"):
        """Update agent status in registry."""
        if agent_id in self.registry:
            self.registry[agent_id]["status"] = status
            self.registry[agent_id]["last_seen"] = datetime.utcnow().isoformat() + "Z"
            
            with open(self.registry_file, 'w') as f:
                json.dump(self.registry, f, indent=4)
                
    def _verify_agent_capabilities(self, agent_id: str) -> bool:
        """Verify agent capabilities based on registry."""
        if agent_id not in self.registry:
            logger.error(f"Agent {agent_id} not found in registry")
            return False
            
        capabilities = self.registry[agent_id].get("capabilities", [])
        if not capabilities:
            logger.error(f"No capabilities defined for {agent_id}")
            return False
            
        return True
        
    def onboard_agent(self, agent_id: str, is_first_agent: bool = False) -> bool:
        """Onboard an agent using the cellphone system."""
        logger.info(f"Starting onboarding process for {agent_id}")
        
        # 1. Verify registry entry
        if not self._verify_agent_capabilities(agent_id):
            return False
            
        # 2. Initial activation
        if is_first_agent:
            # First agent should wake up Agent-1
            logger.info("First agent detected, attempting to wake up Agent-1")
            success = self.cellphone.wake_agent(
                "Agent-1",
                "System initialization request. Please confirm architecture status.",
                MessageMode.WAKE
            )
            if not success:
                logger.error("Failed to wake up Agent-1")
                return False
                
            # Wait for response
            time.sleep(2)
            response = self.cellphone.get_response("Agent-1")
            if not response:
                logger.error("No response from Agent-1")
                return False
                
        else:
            # Regular agent activation
            success = self.cellphone.wake_agent(
                agent_id,
                "Welcome to Dream.OS! Please confirm your capabilities and status.",
                MessageMode.WAKE
            )
            if not success:
                logger.error(f"Failed to wake up {agent_id}")
                return False
                
        # 3. Update registry
        self._update_registry(agent_id)
        
        # 4. Test communication
        success = self.cellphone.message_agent(
            agent_id,
            "Please confirm you can receive and process messages.",
            MessageMode.PING
        )
        if not success:
            logger.error(f"Failed to send test message to {agent_id}")
            return False
            
        # 5. Verify response
        time.sleep(2)
        response = self.cellphone.get_response(agent_id)
        if not response:
            logger.error(f"No response from {agent_id}")
            return False
            
        logger.info(f"Successfully onboarded {agent_id}")
        return True
        
    def verify_system_coordination(self) -> bool:
        """Verify coordination between all active agents."""
        logger.info("Verifying system coordination")
        
        # Send sync message to all agents
        results = self.cellphone.message_all_agents(
            "System coordination check. Please confirm status.",
            MessageMode.SYNC
        )
        
        # Check results
        all_success = all(results.values())
        if not all_success:
            failed_agents = [agent for agent, success in results.items() if not success]
            logger.error(f"Coordination check failed for agents: {failed_agents}")
            return False
            
        logger.info("System coordination verified successfully")
        return True

def main():
    parser = argparse.ArgumentParser(description='Dream.OS Agent Onboarding')
    parser.add_argument('agent_id', help='Agent ID to onboard (e.g., Agent-1)')
    parser.add_argument('--first-agent', action='store_true',
                      help='Indicate this is the first agent being onboarded')
    parser.add_argument('--verify-coordination', action='store_true',
                      help='Verify coordination with all agents after onboarding')
    
    args = parser.parse_args()
    
    onboarding = AgentOnboarding()
    
    # Onboard the agent
    if onboarding.onboard_agent(args.agent_id, args.first_agent):
        logger.info(f"Successfully onboarded {args.agent_id}")
        
        # Verify coordination if requested
        if args.verify_coordination:
            if onboarding.verify_system_coordination():
                logger.info("System coordination verified")
            else:
                logger.error("System coordination verification failed")
    else:
        logger.error(f"Failed to onboard {args.agent_id}")

if __name__ == "__main__":
    main() 