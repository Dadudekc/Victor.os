import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgentRegistry:
    def __init__(self):
        self.registry_file = Path("runtime/agent_registry.json")
        self.registry = self._load_registry()
        
    def _load_registry(self) -> Dict[str, Any]:
        """Load the agent registry from file"""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r') as f:
                    return json.load(f)
            
            # Create default registry if it doesn't exist
            default_registry = {
                f"Agent-{i}": {
                    "status": "inactive",
                    "last_seen": None,
                    "capabilities": [],
                    "state": {
                        "context": None,
                        "backup_points": [],
                        "last_verified": None
                    }
                } for i in range(1, 9)
            }
            
            # Create directory if it doesn't exist
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save default registry
            with open(self.registry_file, 'w') as f:
                json.dump(default_registry, f, indent=2)
                
            return default_registry
            
        except Exception as e:
            logger.error(f"Error loading registry: {e}")
            return {}
            
    def _save_registry(self):
        """Save the registry to file"""
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(self.registry, f, indent=2)
            logger.debug("Registry saved successfully")
        except Exception as e:
            logger.error(f"Error saving registry: {e}")
            raise
            
    def register_agent(self, agent_id: str):
        """Register or update an agent in the registry"""
        try:
            if agent_id not in self.registry:
                self.registry[agent_id] = {
                    "status": "active",
                    "last_seen": datetime.now(timezone.utc).isoformat(),
                    "capabilities": [],
                    "state": {
                        "context": None,
                        "backup_points": [],
                        "last_verified": None
                    }
                }
            else:
                self.registry[agent_id].update({
                    "status": "active",
                    "last_seen": datetime.now(timezone.utc).isoformat()
                })
            
            self._save_registry()
            logger.info(f"Registered agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Error registering agent {agent_id}: {e}")
            raise
            
    def update_agent_state(self, agent_id: str, state_data: Dict[str, Any]):
        """Update an agent's state"""
        try:
            if agent_id not in self.registry:
                raise ValueError(f"Agent {agent_id} not found in registry")
                
            self.registry[agent_id]["state"].update(state_data)
            self.registry[agent_id]["last_seen"] = datetime.now(timezone.utc).isoformat()
            
            self._save_registry()
            logger.info(f"Updated state for agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Error updating agent state: {e}")
            raise
            
    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Get an agent's current state"""
        try:
            if agent_id not in self.registry:
                raise ValueError(f"Agent {agent_id} not found in registry")
                
            return self.registry[agent_id]["state"]
            
        except Exception as e:
            logger.error(f"Error getting agent state: {e}")
            raise
            
    def add_backup_point(self, agent_id: str, backup_data: Dict[str, Any]):
        """Add a backup point for an agent"""
        try:
            if agent_id not in self.registry:
                raise ValueError(f"Agent {agent_id} not found in registry")
                
            backup_point = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": backup_data
            }
            
            self.registry[agent_id]["state"]["backup_points"].append(backup_point)
            self._save_registry()
            
            logger.info(f"Added backup point for agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Error adding backup point: {e}")
            raise 