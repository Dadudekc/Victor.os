"""
Runtime Manager module for managing system runtime.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import logging
import threading
import time


@dataclass
class RuntimeMetrics:
    """Runtime performance metrics."""
    
    cpu_usage: float
    memory_usage: float
    active_agents: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    uptime_seconds: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "active_agents": self.active_agents,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "uptime_seconds": self.uptime_seconds,
            "timestamp": self.timestamp.isoformat()
        }


class RuntimeManager:
    """Manages system runtime and performance monitoring."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, pbm=None):
        self.config = config or {
            "monitoring_interval": 5,  # seconds
            "max_agents": 100,
            "max_memory_usage": 0.9,  # 90%
            "max_cpu_usage": 0.8,     # 80%
            "auto_scale": True
        }
        self.pbm = pbm  # Project Board Manager
        
        self.start_time = datetime.utcnow()
        self.is_running = False
        self.metrics_history: List[RuntimeMetrics] = []
        self.active_agents: Dict[str, Any] = {}
        self.task_queue: List[Dict[str, Any]] = []
        self.completed_tasks = 0
        self.failed_tasks = 0
        
        self.logger = logging.getLogger("RuntimeManager")
        self.monitoring_task = None
        self.lock = threading.Lock()
    
    async def start(self):
        """Start the runtime manager."""
        self.is_running = True
        self.logger.info("Starting Runtime Manager")
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Start task processing
        asyncio.create_task(self._task_processing_loop())
    
    async def stop(self):
        """Stop the runtime manager."""
        self.is_running = False
        self.logger.info("Stopping Runtime Manager")
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_running:
            try:
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # Keep only recent metrics
                if len(self.metrics_history) > 1000:
                    self.metrics_history = self.metrics_history[-1000:]
                
                # Check for resource constraints
                await self._check_resource_constraints(metrics)
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self.config["monitoring_interval"])
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(1)
    
    async def _collect_metrics(self) -> RuntimeMetrics:
        """Collect current runtime metrics."""
        # This is a simplified implementation
        # In a real system, you'd collect actual system metrics
        
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return RuntimeMetrics(
            cpu_usage=0.5,  # Placeholder
            memory_usage=0.3,  # Placeholder
            active_agents=len(self.active_agents),
            total_tasks=len(self.task_queue) + self.completed_tasks + self.failed_tasks,
            completed_tasks=self.completed_tasks,
            failed_tasks=self.failed_tasks,
            uptime_seconds=uptime,
            timestamp=datetime.utcnow()
        )
    
    async def _check_resource_constraints(self, metrics: RuntimeMetrics):
        """Check for resource constraints and take action."""
        if metrics.memory_usage > self.config["max_memory_usage"]:
            self.logger.warning(f"High memory usage: {metrics.memory_usage:.2%}")
            await self._handle_high_memory()
        
        if metrics.cpu_usage > self.config["max_cpu_usage"]:
            self.logger.warning(f"High CPU usage: {metrics.cpu_usage:.2%}")
            await self._handle_high_cpu()
    
    async def _handle_high_memory(self):
        """Handle high memory usage."""
        # Implement memory management strategies
        self.logger.info("Implementing memory management strategies")
    
    async def _handle_high_cpu(self):
        """Handle high CPU usage."""
        # Implement CPU management strategies
        self.logger.info("Implementing CPU management strategies")
    
    async def _task_processing_loop(self):
        """Process tasks in the queue."""
        while self.is_running:
            try:
                if self.task_queue:
                    task = self.task_queue.pop(0)
                    await self._process_task(task)
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Error in task processing: {e}")
                await asyncio.sleep(1)
    
    async def _process_task(self, task: Dict[str, Any]):
        """Process a single task."""
        try:
            # Simulate task processing
            await asyncio.sleep(0.1)
            
            # Mark task as completed
            with self.lock:
                self.completed_tasks += 1
            
            self.logger.debug(f"Completed task: {task.get('id', 'unknown')}")
            
        except Exception as e:
            with self.lock:
                self.failed_tasks += 1
            
            self.logger.error(f"Failed to process task: {e}")
    
    def add_task(self, task: Dict[str, Any]):
        """Add a task to the processing queue."""
        with self.lock:
            self.task_queue.append(task)
    
    def register_agent(self, agent_id: str, agent_info: Dict[str, Any]):
        """Register an active agent."""
        with self.lock:
            self.active_agents[agent_id] = {
                "info": agent_info,
                "registered_at": datetime.utcnow(),
                "last_seen": datetime.utcnow()
            }
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent."""
        with self.lock:
            if agent_id in self.active_agents:
                del self.active_agents[agent_id]
    
    def update_agent_status(self, agent_id: str, status: Dict[str, Any]):
        """Update agent status."""
        with self.lock:
            if agent_id in self.active_agents:
                self.active_agents[agent_id]["last_seen"] = datetime.utcnow()
                self.active_agents[agent_id]["status"] = status
    
    def get_metrics(self, time_window: Optional[timedelta] = None) -> List[RuntimeMetrics]:
        """Get metrics within a time window."""
        if not time_window:
            return self.metrics_history[-100:]  # Last 100 metrics
        
        cutoff_time = datetime.utcnow() - time_window
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]
    
    def get_current_metrics(self) -> Optional[RuntimeMetrics]:
        """Get the most recent metrics."""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        current_metrics = self.get_current_metrics()
        if not current_metrics:
            return {"status": "unknown", "message": "No metrics available"}
        
        # Determine health status
        if current_metrics.memory_usage > self.config["max_memory_usage"]:
            status = "critical"
        elif current_metrics.cpu_usage > self.config["max_cpu_usage"]:
            status = "warning"
        elif current_metrics.failed_tasks > current_metrics.completed_tasks * 0.1:
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "uptime_seconds": current_metrics.uptime_seconds,
            "active_agents": current_metrics.active_agents,
            "task_success_rate": current_metrics.completed_tasks / max(1, current_metrics.completed_tasks + current_metrics.failed_tasks),
            "resource_usage": {
                "cpu": current_metrics.cpu_usage,
                "memory": current_metrics.memory_usage
            }
        } 