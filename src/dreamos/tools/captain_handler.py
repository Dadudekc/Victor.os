#!/usr/bin/env python3
"""
Captain Handler (Agent-1)

This script provides basic coordination capabilities for Agent-1 (the captain).
It focuses on status monitoring and emergency alerts, while leaving actual
coordination to Cursor's native agent capabilities.
"""

import json
import logging
import time
from pathlib import Path
import argparse
from typing import Optional, Dict
from agent_cellphone import AgentCellphone, MessageMode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('captain_handler')

class CaptainHandler:
    def __init__(self):
        self.cellphone = AgentCellphone()
        self.registry_file = Path("runtime/agent_registry.json")
        self.registry = self._load_registry()
        
    def _load_registry(self) -> dict:
        """Load agent registry."""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return {}
            
    def _update_agent_status(self, agent_id: str, status: str):
        """Update agent status in registry."""
        if agent_id in self.registry:
            self.registry[agent_id]["status"] = status
            self.registry[agent_id]["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            with open(self.registry_file, 'w') as f:
                json.dump(self.registry, f, indent=2)
                
    def check_agent_status(self, agent_id: str) -> bool:
        """Check if an agent is responsive."""
        success = self.cellphone.message_agent(
            agent_id,
            "Status check",
            MessageMode.PING
        )
        
        if success:
            self._update_agent_status(agent_id, "active")
        else:
            self._update_agent_status(agent_id, "unresponsive")
            
        return success
        
    def alert_emergency(self, message: str):
        """Send emergency alert to all agents."""
        logger.warning(f"Emergency situation detected: {message}")
        
        # Alert all agents
        self.cellphone.message_all_agents(
            f"EMERGENCY: {message}",
            MessageMode.DEBUG
        )
        
        # Update registry status
        for agent_id in self.registry:
            self._update_agent_status(agent_id, "emergency")
            
    def request_sync(self) -> bool:
        """Request system-wide synchronization."""
        logger.info("Requesting system synchronization")
        
        # Send sync message to all agents
        results = self.cellphone.message_all_agents(
            "System synchronization requested",
            MessageMode.SYNC
        )
        
        # Check results
        all_success = all(results.values())
        if not all_success:
            failed_agents = [agent for agent, success in results.items() if not success]
            logger.error(f"Sync failed for agents: {failed_agents}")
            return False
            
        logger.info("System synchronization completed")
        return True

def main():
    parser = argparse.ArgumentParser(description='Dream.OS Captain Status Monitor')
    parser.add_argument('--check-agent', help='Check status of specific agent')
    parser.add_argument('--emergency', help='Send emergency alert')
    parser.add_argument('--sync', action='store_true',
                      help='Request system synchronization')
    
    args = parser.parse_args()
    
    captain = CaptainHandler()
    
    if args.check_agent:
        success = captain.check_agent_status(args.check_agent)
        print(f"Agent {args.check_agent} is {'responsive' if success else 'unresponsive'}")
    elif args.emergency:
        captain.alert_emergency(args.emergency)
    elif args.sync:
        success = captain.request_sync()
        print(f"System sync {'succeeded' if success else 'failed'}")

if __name__ == "__main__":
    main() 