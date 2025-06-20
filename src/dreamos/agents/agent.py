"""
Base Agent module for the Dream.OS system.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
import asyncio
import logging
import json
import uuid

from ..core.coordination.base_agent import BaseAgent
from ..core.agent_identity import AgentIdentity
from ..utils.common_utils import get_logger


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    
    agent_id: str
    name: str
    role: str
    capabilities: List[str] = field(default_factory=list)
    personality_traits: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Agent(BaseAgent):
    """
    Base Agent class for the Dream.OS system.
    
    This is a simplified version that extends the BaseAgent from coordination.
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(
            identity=AgentIdentity(
                agent_id=config.agent_id,
                name=config.name,
                role=config.role,
                capabilities=config.capabilities,
                personality_traits=config.personality_traits
            ),
            config=config.settings
        )
        
        self.config = config
        self.logger = get_logger(f"Agent_{config.agent_id}")
        
        # Agent-specific state
        self.state: Dict[str, Any] = {}
        self.memory: List[Dict[str, Any]] = []
        self.tasks: List[Dict[str, Any]] = []
        
        # Performance metrics
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_runtime": 0.0,
            "last_activity": datetime.utcnow().isoformat()
        }
    
    async def initialize(self) -> bool:
        """Initialize the agent."""
        try:
            self.logger.info(f"Initializing agent {self.config.name}")
            # Add any agent-specific initialization here
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize agent: {e}")
            return False
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task."""
        try:
            self.logger.info(f"Processing task: {task.get('task_id', 'unknown')}")
            
            # Update metrics
            self.metrics["last_activity"] = datetime.utcnow().isoformat()
            
            # Process the task (implement in subclasses)
            result = await self._execute_task(task)
            
            if result.get("success", False):
                self.metrics["tasks_completed"] += 1
            else:
                self.metrics["tasks_failed"] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"Task processing failed: {e}")
            self.metrics["tasks_failed"] += 1
            return {"success": False, "error": str(e)}
    
    async def _execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific task. Override in subclasses."""
        return {"success": True, "message": "Task executed successfully"}
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "agent_id": self.config.agent_id,
            "name": self.config.name,
            "role": self.config.role,
            "status": "active" if self.is_running else "inactive",
            "metrics": self.metrics.copy(),
            "memory_size": len(self.memory),
            "pending_tasks": len(self.tasks),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def add_to_memory(self, item: Dict[str, Any]):
        """Add an item to agent memory."""
        item["timestamp"] = datetime.utcnow().isoformat()
        self.memory.append(item)
        
        # Limit memory size
        if len(self.memory) > 1000:
            self.memory = self.memory[-500:]  # Keep last 500 items
    
    def get_memory(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get agent memory."""
        if limit:
            return self.memory[-limit:]
        return self.memory.copy()
    
    def clear_memory(self):
        """Clear agent memory."""
        self.memory.clear()
        self.logger.info("Memory cleared")
    
    async def run(self):
        """Main agent run loop."""
        self.logger.info(f"Starting agent {self.config.name}")
        
        # Initialize agent
        if not await self.initialize():
            self.logger.error("Agent initialization failed")
            return
        
        while self.is_running:
            try:
                # Process any pending tasks
                if self.tasks:
                    task = self.tasks.pop(0)
                    await self.process_task(task)
                
                # Agent-specific processing (implement in subclasses)
                await self._agent_loop()
                
                # Sleep to prevent busy waiting
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in agent loop: {e}")
                await asyncio.sleep(5)  # Longer sleep on error
    
    async def _agent_loop(self):
        """Agent-specific processing loop. Override in subclasses."""
        pass  # Default implementation does nothing
    
    def stop(self):
        """Stop the agent."""
        self.logger.info(f"Stopping agent {self.config.name}")
        super().stop()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary representation."""
        return {
            "agent_id": self.config.agent_id,
            "name": self.config.name,
            "role": self.config.role,
            "capabilities": self.config.capabilities,
            "personality_traits": self.config.personality_traits,
            "settings": self.config.settings,
            "metadata": self.config.metadata,
            "state": self.state,
            "metrics": self.metrics,
            "is_running": self.is_running
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Agent':
        """Create agent from dictionary representation."""
        config = AgentConfig(
            agent_id=data["agent_id"],
            name=data["name"],
            role=data["role"],
            capabilities=data.get("capabilities", []),
            personality_traits=data.get("personality_traits", []),
            settings=data.get("settings", {}),
            metadata=data.get("metadata", {})
        )
        
        agent = cls(config)
        agent.state = data.get("state", {})
        agent.metrics = data.get("metrics", agent.metrics)
        agent.is_running = data.get("is_running", False)
        
        return agent 