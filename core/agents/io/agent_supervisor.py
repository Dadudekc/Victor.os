import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class AgentSupervisor:
    """Supervisor tool for managing agent states and operations."""
    
    def __init__(self, base_path: str = "runtime/agent_comms/agent_mailboxes"):
        self.base_path = Path(base_path)
        self.agent_paths = self._get_agent_paths()
        
    def _get_agent_paths(self) -> Dict[str, Path]:
        """Get paths for all agent mailboxes."""
        return {
            agent_dir.name: agent_dir 
            for agent_dir in self.base_path.iterdir() 
            if agent_dir.is_dir() and agent_dir.name.startswith("Agent-")
        }
    
    def reset_agent_onboarding(self, agent_id: str) -> bool:
        """
        Reset an agent's onboarding state to incomplete.
        
        Args:
            agent_id: The ID of the agent to reset (e.g., "Agent-1")
            
        Returns:
            bool: True if reset was successful, False otherwise
        """
        try:
            if agent_id not in self.agent_paths:
                logger.error(f"Agent {agent_id} not found")
                return False
                
            agent_path = self.agent_paths[agent_id]
            
            # Reset status.json
            status_file = agent_path / "status.json"
            if status_file.exists():
                status_data = {
                    "status": "AGENT_ONBOARDING_INCOMPLETE",
                    "last_updated": datetime.utcnow().isoformat() + "Z",
                    "cycle_count": 0,
                    "operation_state": "UNINITIALIZED"
                }
                with open(status_file, 'w') as f:
                    json.dump(status_data, f, indent=2)
            
            # Reset state directory
            state_dir = agent_path / "state"
            if state_dir.exists():
                for file in state_dir.iterdir():
                    file.unlink()
            
            # Reset operation state
            operation_state = {
                "cycle_count": 0,
                "last_cycle": None,
                "operation_state": "UNINITIALIZED",
                "onboarding_complete": False,
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
            
            state_file = state_dir / "operation_state.json"
            with open(state_file, 'w') as f:
                json.dump(operation_state, f, indent=2)
            
            # Update devlog
            devlog_file = agent_path / "devlog.md"
            if devlog_file.exists():
                with open(devlog_file, 'a') as f:
                    f.write(f"\n## Onboarding Reset - {datetime.utcnow().isoformat()}Z\n")
                    f.write("Agent onboarding state has been reset to incomplete.\n")
            
            logger.info(f"Successfully reset onboarding state for {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting agent {agent_id}: {str(e)}")
            return False
    
    def reset_all_agents(self) -> Dict[str, bool]:
        """
        Reset onboarding state for all agents.
        
        Returns:
            Dict[str, bool]: Dictionary mapping agent IDs to reset success status
        """
        results = {}
        for agent_id in self.agent_paths:
            results[agent_id] = self.reset_agent_onboarding(agent_id)
        return results
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of an agent.
        
        Args:
            agent_id: The ID of the agent to check
            
        Returns:
            Optional[Dict[str, Any]]: Agent status data if available
        """
        try:
            if agent_id not in self.agent_paths:
                return None
                
            status_file = self.agent_paths[agent_id] / "status.json"
            if not status_file.exists():
                return None
                
            with open(status_file) as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Error getting status for agent {agent_id}: {str(e)}")
            return None
    
    def get_all_agent_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status for all agents.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping agent IDs to their status data
        """
        return {
            agent_id: self.get_agent_status(agent_id)
            for agent_id in self.agent_paths
        }

# Example usage:
if __name__ == "__main__":
    supervisor = AgentSupervisor()
    
    # Reset a specific agent
    supervisor.reset_agent_onboarding("Agent-1")
    
    # Reset all agents
    results = supervisor.reset_all_agents()
    print("Reset results:", results)
    
    # Get status of all agents
    statuses = supervisor.get_all_agent_statuses()
    print("Agent statuses:", statuses) 