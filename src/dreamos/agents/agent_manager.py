"""
Agent Manager module for managing agent lifecycle and coordination.
"""

from typing import Dict, Any, List, Optional, Type, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import logging
import json
import uuid

from ..core.coordination.base_agent import BaseAgent
from ..core.agent_identity import AgentIdentity
from ..utils.common_utils import get_logger


class AgentStatus(Enum):
    """Status of an agent."""
    
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class AgentInfo:
    """Information about an agent."""
    
    agent_id: str
    name: str
    status: AgentStatus
    agent_type: str
    created_at: datetime
    last_heartbeat: Optional[datetime] = None
    current_task: Optional[str] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentManager:
    """Manages agent lifecycle, registration, and coordination."""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_info: Dict[str, AgentInfo] = {}
        self.agent_types: Dict[str, Type[BaseAgent]] = {}
        self.logger = get_logger("AgentManager")
        
        # Agent management settings
        self.heartbeat_interval = 30  # seconds
        self.max_agents = 100
        self.auto_restart_failed = True
        self.max_restart_attempts = 3
        
        # Statistics
        self.stats = {
            "total_agents_created": 0,
            "active_agents": 0,
            "failed_agents": 0,
            "restart_attempts": 0
        }
    
    def register_agent_type(self, agent_type: str, agent_class: Type[BaseAgent]):
        """Register an agent type with its class."""
        self.agent_types[agent_type] = agent_class
        self.logger.info(f"Registered agent type: {agent_type}")
    
    async def create_agent(self, agent_type: str, agent_id: Optional[str] = None,
                          config: Optional[Dict[str, Any]] = None) -> str:
        """Create a new agent of the specified type."""
        if agent_type not in self.agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        if len(self.agents) >= self.max_agents:
            raise RuntimeError(f"Maximum number of agents ({self.max_agents}) reached")
        
        agent_id = agent_id or str(uuid.uuid4())
        
        if agent_id in self.agents:
            raise ValueError(f"Agent with ID {agent_id} already exists")
        
        try:
            # Create agent instance
            agent_class = self.agent_types[agent_type]
            agent = agent_class(config or {})
            
            # Register agent
            self.agents[agent_id] = agent
            
            # Create agent info
            agent_info = AgentInfo(
                agent_id=agent_id,
                name=agent.identity.name,
                status=AgentStatus.INACTIVE,
                agent_type=agent_type,
                created_at=datetime.utcnow(),
                configuration=config or {}
            )
            self.agent_info[agent_id] = agent_info
            
            self.stats["total_agents_created"] += 1
            self.logger.info(f"Created agent {agent_id} of type {agent_type}")
            
            return agent_id
            
        except Exception as e:
            self.logger.error(f"Failed to create agent {agent_id}: {e}")
            raise
    
    async def start_agent(self, agent_id: str) -> bool:
        """Start an agent."""
        if agent_id not in self.agents:
            self.logger.error(f"Agent {agent_id} not found")
            return False
        
        agent = self.agents[agent_id]
        agent_info = self.agent_info[agent_id]
        
        try:
            agent_info.status = AgentStatus.STARTING
            self.logger.info(f"Starting agent {agent_id}")
            
            # Start agent in background
            asyncio.create_task(self._run_agent(agent_id))
            
            return True
            
        except Exception as e:
            agent_info.status = AgentStatus.ERROR
            self.logger.error(f"Failed to start agent {agent_id}: {e}")
            return False
    
    async def stop_agent(self, agent_id: str) -> bool:
        """Stop an agent."""
        if agent_id not in self.agents:
            self.logger.error(f"Agent {agent_id} not found")
            return False
        
        agent = self.agents[agent_id]
        agent_info = self.agent_info[agent_id]
        
        try:
            agent_info.status = AgentStatus.STOPPING
            self.logger.info(f"Stopping agent {agent_id}")
            
            # Stop agent
            agent.stop()
            
            agent_info.status = AgentStatus.STOPPED
            self.logger.info(f"Agent {agent_id} stopped")
            
            return True
            
        except Exception as e:
            agent_info.status = AgentStatus.ERROR
            self.logger.error(f"Failed to stop agent {agent_id}: {e}")
            return False
    
    async def restart_agent(self, agent_id: str) -> bool:
        """Restart an agent."""
        self.logger.info(f"Restarting agent {agent_id}")
        
        # Stop agent
        await self.stop_agent(agent_id)
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Start agent
        return await self.start_agent(agent_id)
    
    async def _run_agent(self, agent_id: str):
        """Run an agent in the background."""
        agent = self.agents[agent_id]
        agent_info = self.agent_info[agent_id]
        
        try:
            agent_info.status = AgentStatus.ACTIVE
            self.stats["active_agents"] += 1
            
            # Start heartbeat monitoring
            asyncio.create_task(self._monitor_agent_heartbeat(agent_id))
            
            # Run agent
            await agent.run()
            
        except Exception as e:
            agent_info.status = AgentStatus.ERROR
            self.stats["failed_agents"] += 1
            self.logger.error(f"Agent {agent_id} failed: {e}")
            
            # Auto-restart if enabled
            if self.auto_restart_failed:
                await self._handle_agent_failure(agent_id)
    
    async def _monitor_agent_heartbeat(self, agent_id: str):
        """Monitor agent heartbeat."""
        agent_info = self.agent_info[agent_id]
        
        while agent_info.status in [AgentStatus.ACTIVE, AgentStatus.BUSY]:
            try:
                # Update heartbeat
                agent_info.last_heartbeat = datetime.utcnow()
                
                # Check if agent is still running
                if not self.agents[agent_id].is_running:
                    break
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"Error monitoring agent {agent_id}: {e}")
                break
        
        # Agent stopped
        if agent_info.status in [AgentStatus.ACTIVE, AgentStatus.BUSY]:
            agent_info.status = AgentStatus.ERROR
            self.stats["active_agents"] -= 1
    
    async def _handle_agent_failure(self, agent_id: str):
        """Handle agent failure with restart logic."""
        agent_info = self.agent_info[agent_id]
        
        restart_count = agent_info.metadata.get("restart_count", 0)
        
        if restart_count < self.max_restart_attempts:
            restart_count += 1
            agent_info.metadata["restart_count"] = restart_count
            self.stats["restart_attempts"] += 1
            
            self.logger.info(f"Restarting agent {agent_id} (attempt {restart_count})")
            
            # Wait before restart
            await asyncio.sleep(5 * restart_count)  # Exponential backoff
            
            # Restart agent
            await self.restart_agent(agent_id)
        else:
            self.logger.error(f"Agent {agent_id} failed after {self.max_restart_attempts} restart attempts")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
    
    def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent information by ID."""
        return self.agent_info.get(agent_id)
    
    def get_agents_by_type(self, agent_type: str) -> List[str]:
        """Get all agent IDs of a specific type."""
        return [agent_id for agent_id, info in self.agent_info.items() 
                if info.agent_type == agent_type]
    
    def get_agents_by_status(self, status: AgentStatus) -> List[str]:
        """Get all agent IDs with a specific status."""
        return [agent_id for agent_id, info in self.agent_info.items() 
                if info.status == status]
    
    async def broadcast_message(self, message: Dict[str, Any], 
                              target_agents: Optional[List[str]] = None) -> Dict[str, Any]:
        """Broadcast a message to agents."""
        if target_agents is None:
            target_agents = list(self.agents.keys())
        
        results = {}
        
        for agent_id in target_agents:
            if agent_id in self.agents:
                try:
                    agent = self.agents[agent_id]
                    if hasattr(agent, 'handle_message'):
                        result = await agent.handle_message(message)
                        results[agent_id] = {"status": "success", "result": result}
                    else:
                        results[agent_id] = {"status": "error", "error": "Agent does not support messaging"}
                except Exception as e:
                    results[agent_id] = {"status": "error", "error": str(e)}
            else:
                results[agent_id] = {"status": "error", "error": "Agent not found"}
        
        return results
    
    async def assign_task(self, task: Dict[str, Any], agent_id: str) -> bool:
        """Assign a task to a specific agent."""
        if agent_id not in self.agents:
            self.logger.error(f"Agent {agent_id} not found")
            return False
        
        agent = self.agents[agent_id]
        agent_info = self.agent_info[agent_id]
        
        try:
            if hasattr(agent, 'assign_task'):
                success = await agent.assign_task(task)
                if success:
                    agent_info.status = AgentStatus.BUSY
                    agent_info.current_task = task.get("task_id")
                    self.logger.info(f"Assigned task to agent {agent_id}")
                return success
            else:
                self.logger.error(f"Agent {agent_id} does not support task assignment")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to assign task to agent {agent_id}: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        status_counts = {}
        for status in AgentStatus:
            status_counts[status.value] = len(self.get_agents_by_status(status))
        
        return {
            "total_agents": len(self.agents),
            "agent_status_counts": status_counts,
            "agent_type_counts": self._get_agent_type_counts(),
            "statistics": self.stats.copy(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_agent_type_counts(self) -> Dict[str, int]:
        """Get counts of agents by type."""
        type_counts = {}
        for info in self.agent_info.values():
            agent_type = info.agent_type
            type_counts[agent_type] = type_counts.get(agent_type, 0) + 1
        return type_counts
    
    async def cleanup_inactive_agents(self, max_age_hours: int = 24):
        """Clean up inactive agents older than specified age."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        agents_to_remove = []
        for agent_id, info in self.agent_info.items():
            if (info.status in [AgentStatus.STOPPED, AgentStatus.ERROR] and 
                info.created_at < cutoff_time):
                agents_to_remove.append(agent_id)
        
        for agent_id in agents_to_remove:
            await self.remove_agent(agent_id)
        
        if agents_to_remove:
            self.logger.info(f"Cleaned up {len(agents_to_remove)} inactive agents")
    
    async def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent completely."""
        if agent_id not in self.agents:
            return False
        
        # Stop agent if running
        if self.agent_info[agent_id].status in [AgentStatus.ACTIVE, AgentStatus.BUSY]:
            await self.stop_agent(agent_id)
        
        # Remove from collections
        del self.agents[agent_id]
        del self.agent_info[agent_id]
        
        self.logger.info(f"Removed agent {agent_id}")
        return True
    
    def export_agent_configurations(self) -> Dict[str, Any]:
        """Export all agent configurations for backup."""
        configurations = {}
        
        for agent_id, info in self.agent_info.items():
            configurations[agent_id] = {
                "agent_type": info.agent_type,
                "configuration": info.configuration,
                "metadata": info.metadata
            }
        
        return {
            "configurations": configurations,
            "export_timestamp": datetime.utcnow().isoformat()
        }
    
    async def import_agent_configurations(self, configurations: Dict[str, Any]) -> List[str]:
        """Import agent configurations from backup."""
        created_agents = []
        
        for agent_id, config_data in configurations.get("configurations", {}).items():
            try:
                agent_type = config_data["agent_type"]
                configuration = config_data.get("configuration", {})
                
                # Create agent
                new_agent_id = await self.create_agent(agent_type, agent_id, configuration)
                
                # Restore metadata
                if "metadata" in config_data:
                    self.agent_info[new_agent_id].metadata = config_data["metadata"]
                
                created_agents.append(new_agent_id)
                
            except Exception as e:
                self.logger.error(f"Failed to import agent {agent_id}: {e}")
        
        self.logger.info(f"Imported {len(created_agents)} agents")
        return created_agents 