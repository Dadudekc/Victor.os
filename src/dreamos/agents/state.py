"""
Agent State Management Module

This module provides state management for agents, including:
- Agent state tracking
- State transitions
- State persistence
- State validation
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
import asyncio
from pathlib import Path

from ..utils.common_utils import get_logger


class AgentStatus(Enum):
    """Agent status enumeration."""
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"
    INITIALIZING = "initializing"
    SHUTTING_DOWN = "shutting_down"


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class TaskState:
    """Represents the state of a task."""
    
    task_id: str
    name: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        if self.started_at:
            data["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskState":
        """Create from dictionary."""
        data = data.copy()
        data["status"] = TaskStatus(data["status"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        return cls(**data)


@dataclass
class AgentState:
    """Represents the state of an agent."""
    
    agent_id: str
    name: str
    status: AgentStatus
    created_at: datetime
    last_updated: datetime
    version: str = "1.0.0"
    
    # Current task information
    current_task: Optional[TaskState] = None
    task_queue: List[TaskState] = field(default_factory=list)
    completed_tasks: List[TaskState] = field(default_factory=list)
    
    # Performance metrics
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    average_task_duration: float = 0.0
    uptime_seconds: float = 0.0
    
    # Configuration and capabilities
    capabilities: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    
    # Health and monitoring
    health_score: float = 1.0
    last_heartbeat: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None
    
    # Memory and resource usage
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["last_updated"] = self.last_updated.isoformat()
        if self.last_heartbeat:
            data["last_heartbeat"] = self.last_heartbeat.isoformat()
        if self.current_task:
            data["current_task"] = self.current_task.to_dict()
        data["task_queue"] = [task.to_dict() for task in self.task_queue]
        data["completed_tasks"] = [task.to_dict() for task in self.completed_tasks]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """Create from dictionary."""
        data = data.copy()
        data["status"] = AgentStatus(data["status"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        if data.get("last_heartbeat"):
            data["last_heartbeat"] = datetime.fromisoformat(data["last_heartbeat"])
        if data.get("current_task"):
            data["current_task"] = TaskState.from_dict(data["current_task"])
        data["task_queue"] = [TaskState.from_dict(task) for task in data.get("task_queue", [])]
        data["completed_tasks"] = [TaskState.from_dict(task) for task in data.get("completed_tasks", [])]
        return cls(**data)
    
    def update_status(self, status: AgentStatus):
        """Update agent status."""
        self.status = status
        self.last_updated = datetime.now()
    
    def add_task(self, task: TaskState):
        """Add a task to the queue."""
        self.task_queue.append(task)
        self.last_updated = datetime.now()
    
    def start_task(self, task_id: str) -> bool:
        """Start a task from the queue."""
        for task in self.task_queue:
            if task.task_id == task_id:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                self.current_task = task
                self.task_queue.remove(task)
                self.last_updated = datetime.now()
                return True
        return False
    
    def complete_task(self, task_id: str, result: Any = None, error: Optional[str] = None):
        """Complete a task."""
        if self.current_task and self.current_task.task_id == task_id:
            self.current_task.status = TaskStatus.COMPLETED if error is None else TaskStatus.FAILED
            self.current_task.completed_at = datetime.now()
            self.current_task.result = result
            self.current_task.error = error
            
            # Update metrics
            if error is None:
                self.total_tasks_completed += 1
            else:
                self.total_tasks_failed += 1
                self.error_count += 1
                self.last_error = error
            
            # Calculate average task duration
            if self.current_task.started_at and self.current_task.completed_at:
                duration = (self.current_task.completed_at - self.current_task.started_at).total_seconds()
                total_tasks = self.total_tasks_completed + self.total_tasks_failed
                if total_tasks > 0:
                    self.average_task_duration = (
                        (self.average_task_duration * (total_tasks - 1) + duration) / total_tasks
                    )
            
            # Move to completed tasks
            self.completed_tasks.append(self.current_task)
            self.current_task = None
            self.last_updated = datetime.now()
    
    def update_health(self, health_score: float, memory_usage: float = 0.0, cpu_usage: float = 0.0):
        """Update health metrics."""
        self.health_score = max(0.0, min(1.0, health_score))
        self.memory_usage_mb = memory_usage
        self.cpu_usage_percent = cpu_usage
        self.last_heartbeat = datetime.now()
        self.last_updated = datetime.now()
    
    def is_healthy(self) -> bool:
        """Check if agent is healthy."""
        return self.health_score > 0.5 and self.status != AgentStatus.ERROR
    
    def get_uptime(self) -> timedelta:
        """Get agent uptime."""
        return datetime.now() - self.created_at


class AgentStateManager:
    """Manages agent state persistence and retrieval."""
    
    def __init__(self, storage_dir: str = "runtime/agent_states"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("AgentStateManager")
        self._states: Dict[str, AgentState] = {}
        self._lock = asyncio.Lock()
    
    async def save_state(self, state: AgentState) -> bool:
        """Save agent state to storage."""
        try:
            async with self._lock:
                file_path = self.storage_dir / f"{state.agent_id}.json"
                state_data = state.to_dict()
                
                with open(file_path, 'w') as f:
                    json.dump(state_data, f, indent=2)
                
                self._states[state.agent_id] = state
                self.logger.debug(f"Saved state for agent {state.agent_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save state for agent {state.agent_id}: {e}")
            return False
    
    async def load_state(self, agent_id: str) -> Optional[AgentState]:
        """Load agent state from storage."""
        try:
            async with self._lock:
                # Check cache first
                if agent_id in self._states:
                    return self._states[agent_id]
                
                file_path = self.storage_dir / f"{agent_id}.json"
                if not file_path.exists():
                    return None
                
                with open(file_path, 'r') as f:
                    state_data = json.load(f)
                
                state = AgentState.from_dict(state_data)
                self._states[agent_id] = state
                self.logger.debug(f"Loaded state for agent {agent_id}")
                return state
                
        except Exception as e:
            self.logger.error(f"Failed to load state for agent {agent_id}: {e}")
            return None
    
    async def delete_state(self, agent_id: str) -> bool:
        """Delete agent state from storage."""
        try:
            async with self._lock:
                file_path = self.storage_dir / f"{agent_id}.json"
                if file_path.exists():
                    file_path.unlink()
                
                if agent_id in self._states:
                    del self._states[agent_id]
                
                self.logger.debug(f"Deleted state for agent {agent_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to delete state for agent {agent_id}: {e}")
            return False
    
    async def list_agents(self) -> List[str]:
        """List all agent IDs with stored states."""
        try:
            async with self._lock:
                agent_ids = []
                for file_path in self.storage_dir.glob("*.json"):
                    agent_id = file_path.stem
                    agent_ids.append(agent_id)
                return agent_ids
                
        except Exception as e:
            self.logger.error(f"Failed to list agents: {e}")
            return []
    
    async def get_all_states(self) -> Dict[str, AgentState]:
        """Get all agent states."""
        try:
            async with self._lock:
                agent_ids = await self.list_agents()
                states = {}
                for agent_id in agent_ids:
                    state = await self.load_state(agent_id)
                    if state:
                        states[agent_id] = state
                return states
                
        except Exception as e:
            self.logger.error(f"Failed to get all states: {e}")
            return {}
    
    async def cleanup_old_states(self, max_age_hours: int = 24) -> int:
        """Clean up old agent states."""
        try:
            async with self._lock:
                cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
                cleaned_count = 0
                
                for file_path in self.storage_dir.glob("*.json"):
                    try:
                        with open(file_path, 'r') as f:
                            state_data = json.load(f)
                        
                        last_updated = datetime.fromisoformat(state_data["last_updated"])
                        if last_updated < cutoff_time:
                            file_path.unlink()
                            agent_id = file_path.stem
                            if agent_id in self._states:
                                del self._states[agent_id]
                            cleaned_count += 1
                            
                    except Exception as e:
                        self.logger.warning(f"Failed to process {file_path}: {e}")
                
                self.logger.info(f"Cleaned up {cleaned_count} old agent states")
                return cleaned_count
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old states: {e}")
            return 0 