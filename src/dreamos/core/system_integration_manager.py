"""
System Integration Manager

This module implements the SystemIntegrationManager class for coordinating
interactions between core system components and ensuring proper integration.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from .agent_registry import AgentRegistry
from .checkpoint_manager import CheckpointManager
from .recovery_system import RecoverySystem
from .agent_loop import AgentLoop

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dreamos.core.system_integration_manager")

class SystemIntegrationManager:
    """
    Manager for coordinating system component integration and ensuring
    proper interaction between core components.
    """
    
    def __init__(self, workspace_root: str):
        """
        Initialize the system integration manager.
        
        Args:
            workspace_root: Root directory for the workspace
        """
        self.workspace_root = Path(workspace_root)
        self.registry = AgentRegistry()
        self.active_agents: Dict[str, Dict[str, Any]] = {}
        self.integration_status: Dict[str, Any] = {
            "last_verified": None,
            "component_status": {},
            "integration_points": {},
            "error_count": 0
        }
        
    def initialize_agent(self, agent_id: str) -> bool:
        """
        Initialize an agent with all required components.
        
        Args:
            agent_id: Identifier of the agent to initialize
            
        Returns:
            bool: True if initialization successful
        """
        try:
            # Register agent
            self.registry.register_agent(agent_id)
            
            # Initialize components
            checkpoint_manager = CheckpointManager(agent_id)
            recovery_system = RecoverySystem(agent_id, str(self.workspace_root))
            agent_loop = AgentLoop(agent_id, str(self.workspace_root))
            
            # Create initial checkpoint
            checkpoint_manager.create_checkpoint("initialization")
            
            # Store agent components
            self.active_agents[agent_id] = {
                "checkpoint_manager": checkpoint_manager,
                "recovery_system": recovery_system,
                "agent_loop": agent_loop,
                "last_verified": datetime.now(timezone.utc).isoformat()
            }
            
            # Update integration status
            self._update_component_status(agent_id, "initialized")
            
            logger.info(f"Successfully initialized agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize agent {agent_id}: {e}")
            return False
            
    def verify_integration(self, agent_id: str) -> bool:
        """
        Verify integration between components for an agent.
        
        Args:
            agent_id: Identifier of the agent to verify
            
        Returns:
            bool: True if integration is valid
        """
        try:
            if agent_id not in self.active_agents:
                raise ValueError(f"Agent {agent_id} not initialized")
                
            components = self.active_agents[agent_id]
            
            # Verify registry state
            agent_state = self.registry.get_agent_state(agent_id)
            if not agent_state:
                raise ValueError("Agent not registered")
                
            # Verify checkpoint system
            latest_checkpoint = components["checkpoint_manager"].get_latest_checkpoint()
            if not latest_checkpoint:
                raise ValueError("No checkpoints found")
                
            # Verify recovery system
            recovery_status = components["recovery_system"].get_recovery_status()
            if not recovery_status["has_last_good_state"]:
                raise ValueError("No recovery state available")
                
            # Update verification timestamp
            self.active_agents[agent_id]["last_verified"] = datetime.now(timezone.utc).isoformat()
            self.integration_status["last_verified"] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Successfully verified integration for agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Integration verification failed for agent {agent_id}: {e}")
            self.integration_status["error_count"] += 1
            return False
            
    def _update_component_status(self, agent_id: str, status: str):
        """
        Update the status of a component in the integration status.
        
        Args:
            agent_id: Identifier of the agent
            status: New status to set
        """
        self.integration_status["component_status"][agent_id] = {
            "status": status,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
    def get_integration_status(self) -> Dict[str, Any]:
        """
        Get the current integration status.
        
        Returns:
            Dict containing integration status information
        """
        return {
            "last_verified": self.integration_status["last_verified"],
            "active_agents": list(self.active_agents.keys()),
            "component_status": self.integration_status["component_status"],
            "error_count": self.integration_status["error_count"]
        }
        
    def cleanup_agent(self, agent_id: str) -> bool:
        """
        Clean up an agent's components and remove from active agents.
        
        Args:
            agent_id: Identifier of the agent to clean up
            
        Returns:
            bool: True if cleanup successful
        """
        try:
            if agent_id not in self.active_agents:
                return True
                
            # Create final checkpoint
            components = self.active_agents[agent_id]
            components["checkpoint_manager"].create_checkpoint("cleanup")
            
            # Remove from active agents
            del self.active_agents[agent_id]
            
            # Update integration status
            self._update_component_status(agent_id, "cleaned_up")
            
            logger.info(f"Successfully cleaned up agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clean up agent {agent_id}: {e}")
            return False 