"""
Agent 001 - Core Coordination Agent
Responsible for orchestrating other agents and managing system-wide coordination.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging
import json
import uuid

from ..core.coordination.base_agent import BaseAgent
from ..core.agent_identity import AgentIdentity
from ..core.empathy_scoring import EmpathyScorer
from ..utils.common_utils import get_logger


@dataclass
class CoordinationTask:
    """Represents a coordination task."""
    
    task_id: str
    task_type: str
    priority: int
    description: str
    assigned_agents: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Agent001(BaseAgent):
    """
    Agent 001 - Core Coordination Agent
    
    Responsibilities:
    - Orchestrate other agents
    - Manage task distribution
    - Monitor system health
    - Coordinate complex workflows
    - Handle agent communication
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            identity=AgentIdentity(
                agent_id="agent_001",
                name="Coordination Agent",
                role="System Coordinator",
                capabilities=["task_orchestration", "agent_management", "workflow_coordination"],
                personality_traits=["organized", "analytical", "empathetic"]
            ),
            config=config or {}
        )
        
        self.logger = get_logger("Agent001")
        self.tasks: Dict[str, CoordinationTask] = {}
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.workflow_templates: Dict[str, Dict[str, Any]] = {}
        self.empathy_scorer = EmpathyScorer()
        
        # Initialize coordination capabilities
        self._initialize_coordination_system()
    
    def _initialize_coordination_system(self):
        """Initialize the coordination system components."""
        self.logger.info("Initializing coordination system")
        
        # Load workflow templates
        self._load_workflow_templates()
        
        # Initialize agent registry
        self._initialize_agent_registry()
        
        # Set up monitoring
        self._setup_monitoring()
    
    def _load_workflow_templates(self):
        """Load predefined workflow templates."""
        self.workflow_templates = {
            "data_processing": {
                "steps": ["data_collection", "data_validation", "data_processing", "result_analysis"],
                "required_agents": ["agent_002", "agent_003"],
                "estimated_duration": 300,  # seconds
                "priority_levels": {"data_collection": 1, "data_validation": 2, "data_processing": 3, "result_analysis": 4}
            },
            "system_maintenance": {
                "steps": ["health_check", "cleanup", "optimization", "verification"],
                "required_agents": ["agent_004", "agent_005"],
                "estimated_duration": 180,
                "priority_levels": {"health_check": 1, "cleanup": 2, "optimization": 3, "verification": 4}
            },
            "user_interaction": {
                "steps": ["request_analysis", "agent_selection", "task_execution", "response_generation"],
                "required_agents": ["agent_006", "agent_007"],
                "estimated_duration": 60,
                "priority_levels": {"request_analysis": 1, "agent_selection": 2, "task_execution": 3, "response_generation": 4}
            }
        }
    
    def _initialize_agent_registry(self):
        """Initialize the agent registry with known agents."""
        self.agent_registry = {
            "agent_002": {
                "name": "Data Processing Agent",
                "capabilities": ["data_processing", "validation"],
                "status": "available",
                "current_task": None,
                "performance_metrics": {"success_rate": 0.95, "avg_response_time": 2.5}
            },
            "agent_003": {
                "name": "Analysis Agent",
                "capabilities": ["analysis", "reporting"],
                "status": "available",
                "current_task": None,
                "performance_metrics": {"success_rate": 0.92, "avg_response_time": 5.0}
            },
            "agent_004": {
                "name": "Maintenance Agent",
                "capabilities": ["system_maintenance", "optimization"],
                "status": "available",
                "current_task": None,
                "performance_metrics": {"success_rate": 0.88, "avg_response_time": 10.0}
            },
            "agent_005": {
                "name": "Monitoring Agent",
                "capabilities": ["monitoring", "alerting"],
                "status": "available",
                "current_task": None,
                "performance_metrics": {"success_rate": 0.96, "avg_response_time": 1.0}
            }
        }
    
    def _setup_monitoring(self):
        """Set up system monitoring capabilities."""
        self.logger.info("Setting up system monitoring")
        # In a real implementation, this would set up monitoring hooks
        # For now, we'll use a simple status tracking system
    
    async def create_coordination_task(self, task_type: str, description: str, 
                                     priority: int = 1, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new coordination task."""
        task_id = str(uuid.uuid4())
        
        task = CoordinationTask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            description=description,
            metadata=metadata or {}
        )
        
        self.tasks[task_id] = task
        self.logger.info(f"Created coordination task {task_id}: {description}")
        
        # Automatically assign agents if workflow template exists
        if task_type in self.workflow_templates:
            template = self.workflow_templates[task_type]
            task.assigned_agents = template["required_agents"].copy()
            self.logger.info(f"Assigned agents {task.assigned_agents} to task {task_id}")
        
        return task_id
    
    async def assign_task_to_agent(self, task_id: str, agent_id: str) -> bool:
        """Assign a task to a specific agent."""
        if task_id not in self.tasks:
            self.logger.error(f"Task {task_id} not found")
            return False
        
        if agent_id not in self.agent_registry:
            self.logger.error(f"Agent {agent_id} not found in registry")
            return False
        
        task = self.tasks[task_id]
        if agent_id not in task.assigned_agents:
            task.assigned_agents.append(agent_id)
        
        # Update agent status
        self.agent_registry[agent_id]["current_task"] = task_id
        self.agent_registry[agent_id]["status"] = "busy"
        
        self.logger.info(f"Assigned task {task_id} to agent {agent_id}")
        return True
    
    async def execute_workflow(self, workflow_type: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Execute a predefined workflow."""
        if workflow_type not in self.workflow_templates:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
        
        template = self.workflow_templates[workflow_type]
        description = f"Execute {workflow_type} workflow"
        
        task_id = await self.create_coordination_task(
            task_type=workflow_type,
            description=description,
            priority=1,
            metadata={"workflow_parameters": parameters or {}}
        )
        
        # Assign all required agents
        for agent_id in template["required_agents"]:
            await self.assign_task_to_agent(task_id, agent_id)
        
        self.logger.info(f"Started workflow {workflow_type} with task {task_id}")
        return task_id
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        available_agents = sum(1 for agent in self.agent_registry.values() if agent["status"] == "available")
        total_agents = len(self.agent_registry)
        active_tasks = sum(1 for task in self.tasks.values() if task.status == "active")
        
        # Calculate empathy scores for agent interactions
        empathy_scores = {}
        for agent_id, agent_data in self.agent_registry.items():
            if agent_data["current_task"]:
                empathy_scores[agent_id] = self.empathy_scorer.calculate_empathy_score(
                    agent_data["personality_traits"] if "personality_traits" in agent_data else [],
                    "task_execution"
                )
        
        return {
            "total_agents": total_agents,
            "available_agents": available_agents,
            "busy_agents": total_agents - available_agents,
            "active_tasks": active_tasks,
            "total_tasks": len(self.tasks),
            "system_health": "healthy" if available_agents > total_agents // 2 else "degraded",
            "empathy_scores": empathy_scores,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def coordinate_agents(self, task_id: str) -> Dict[str, Any]:
        """Coordinate multiple agents for a specific task."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.tasks[task_id]
        coordination_result = {
            "task_id": task_id,
            "status": "coordinating",
            "assigned_agents": task.assigned_agents,
            "coordination_steps": []
        }
        
        # Simulate coordination steps
        for agent_id in task.assigned_agents:
            if agent_id in self.agent_registry:
                agent_data = self.agent_registry[agent_id]
                step = {
                    "agent_id": agent_id,
                    "agent_name": agent_data["name"],
                    "action": "task_assignment",
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat()
                }
                coordination_result["coordination_steps"].append(step)
        
        task.status = "active"
        self.logger.info(f"Coordinated {len(task.assigned_agents)} agents for task {task_id}")
        
        return coordination_result
    
    async def handle_agent_communication(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle communication between agents."""
        sender_id = message.get("sender_id")
        recipient_id = message.get("recipient_id")
        message_type = message.get("message_type")
        content = message.get("content", {})
        
        self.logger.info(f"Handling communication from {sender_id} to {recipient_id}: {message_type}")
        
        # Route message based on type
        if message_type == "task_completion":
            return await self._handle_task_completion(sender_id, content)
        elif message_type == "task_request":
            return await self._handle_task_request(sender_id, content)
        elif message_type == "status_update":
            return await self._handle_status_update(sender_id, content)
        else:
            return {"status": "unknown_message_type", "message": "Unsupported message type"}
    
    async def _handle_task_completion(self, agent_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task completion notification from an agent."""
        task_id = content.get("task_id")
        
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            
            # Update agent status
            if agent_id in self.agent_registry:
                self.agent_registry[agent_id]["current_task"] = None
                self.agent_registry[agent_id]["status"] = "available"
            
            self.logger.info(f"Task {task_id} completed by agent {agent_id}")
            return {"status": "success", "task_status": "completed"}
        
        return {"status": "error", "message": "Task not found"}
    
    async def _handle_task_request(self, agent_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task request from an agent."""
        task_type = content.get("task_type")
        priority = content.get("priority", 1)
        
        # Find available task or create new one
        available_task = None
        for task in self.tasks.values():
            if task.task_type == task_type and task.status == "pending":
                available_task = task
                break
        
        if not available_task:
            # Create new task
            task_id = await self.create_coordination_task(
                task_type=task_type,
                description=f"Task requested by {agent_id}",
                priority=priority
            )
            available_task = self.tasks[task_id]
        
        # Assign task to requesting agent
        await self.assign_task_to_agent(available_task.task_id, agent_id)
        
        return {
            "status": "success",
            "task_id": available_task.task_id,
            "task_description": available_task.description
        }
    
    async def _handle_status_update(self, agent_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status update from an agent."""
        if agent_id in self.agent_registry:
            self.agent_registry[agent_id].update(content)
            self.logger.info(f"Updated status for agent {agent_id}")
            return {"status": "success", "message": "Status updated"}
        
        return {"status": "error", "message": "Agent not found"}
    
    async def get_agent_performance_report(self) -> Dict[str, Any]:
        """Generate a performance report for all agents."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "agents": {},
            "summary": {
                "total_agents": len(self.agent_registry),
                "average_success_rate": 0.0,
                "average_response_time": 0.0
            }
        }
        
        total_success_rate = 0.0
        total_response_time = 0.0
        agent_count = 0
        
        for agent_id, agent_data in self.agent_registry.items():
            metrics = agent_data.get("performance_metrics", {})
            success_rate = metrics.get("success_rate", 0.0)
            response_time = metrics.get("avg_response_time", 0.0)
            
            report["agents"][agent_id] = {
                "name": agent_data["name"],
                "status": agent_data["status"],
                "current_task": agent_data["current_task"],
                "success_rate": success_rate,
                "avg_response_time": response_time
            }
            
            total_success_rate += success_rate
            total_response_time += response_time
            agent_count += 1
        
        if agent_count > 0:
            report["summary"]["average_success_rate"] = total_success_rate / agent_count
            report["summary"]["average_response_time"] = total_response_time / agent_count
        
        return report
    
    async def run(self):
        """Main run loop for the coordination agent."""
        self.logger.info("Starting Agent 001 - Coordination Agent")
        
        while self.is_running:
            try:
                # Monitor system status
                status = await self.get_system_status()
                
                # Handle pending tasks
                pending_tasks = [task for task in self.tasks.values() if task.status == "pending"]
                for task in pending_tasks:
                    if task.assigned_agents:
                        await self.coordinate_agents(task.task_id)
                
                # Generate periodic reports
                if self._should_generate_report():
                    report = await self.get_agent_performance_report()
                    self.logger.info(f"Performance report generated: {report['summary']}")
                
                # Sleep before next iteration
                await asyncio.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error in coordination loop: {e}")
                await asyncio.sleep(10)  # Longer sleep on error
    
    def _should_generate_report(self) -> bool:
        """Determine if it's time to generate a report."""
        # Generate report every 5 minutes (300 seconds)
        current_time = datetime.utcnow()
        if not hasattr(self, '_last_report_time'):
            self._last_report_time = current_time
            return True
        
        time_diff = (current_time - self._last_report_time).total_seconds()
        if time_diff >= 300:
            self._last_report_time = current_time
            return True
        
        return False 