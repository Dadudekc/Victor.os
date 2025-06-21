"""
Interaction Manager module for managing user interactions and automation workflows.
"""

from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import logging
import json
import time
import uuid

from ..utils.common_utils import get_logger


class InteractionType(Enum):
    """Types of interactions."""
    
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    DRAG = "drag"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    KEY_PRESS = "key_press"
    HOTKEY = "hotkey"
    CUSTOM = "custom"


class InteractionStatus(Enum):
    """Status of an interaction."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class InteractionStep:
    """Represents a single interaction step."""
    
    step_id: str
    interaction_type: InteractionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    status: InteractionStatus = InteractionStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractionWorkflow:
    """Represents a workflow of interactions."""
    
    workflow_id: str
    name: str
    description: str = ""
    steps: List[InteractionStep] = field(default_factory=list)
    status: InteractionStatus = InteractionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class InteractionExecutor:
    """Executes individual interaction steps."""
    
    def __init__(self):
        self.logger = get_logger("InteractionExecutor")
        self.executors: Dict[InteractionType, Callable] = {}
        self._register_default_executors()
        self.interaction_types = {
            "CLICK": "click",
            "TYPE": "type", 
            "SCROLL": "scroll",
            "WAIT": "wait",
            "SCREENSHOT": "screenshot"
        }
        self.current_workflow = None
    
    def _register_default_executors(self):
        """Register default interaction executors."""
        self.executors[InteractionType.CLICK] = self._execute_click
        self.executors[InteractionType.TYPE] = self._execute_type
        self.executors[InteractionType.SCROLL] = self._execute_scroll
        self.executors[InteractionType.DRAG] = self._execute_drag
        self.executors[InteractionType.WAIT] = self._execute_wait
        self.executors[InteractionType.SCREENSHOT] = self._execute_screenshot
        self.executors[InteractionType.KEY_PRESS] = self._execute_key_press
        self.executors[InteractionType.HOTKEY] = self._execute_hotkey
        self.executors[InteractionType.CUSTOM] = self._execute_custom
    
    async def execute_step(self, step: InteractionStep) -> bool:
        """Execute a single interaction step."""
        step.status = InteractionStatus.RUNNING
        start_time = time.time()
        
        try:
            executor = self.executors.get(step.interaction_type)
            if not executor:
                raise ValueError(f"No executor for interaction type: {step.interaction_type}")
            
            # Execute with timeout if specified
            if step.timeout:
                result = await asyncio.wait_for(
                    executor(step.parameters),
                    timeout=step.timeout
                )
            else:
                result = await executor(step.parameters)
            
            # Step completed successfully
            step.status = InteractionStatus.COMPLETED
            step.result = result
            step.execution_time = time.time() - start_time
            step.error = None
            
            self.logger.info(f"Step {step.step_id} completed successfully")
            return True
            
        except asyncio.TimeoutError:
            step.status = InteractionStatus.FAILED
            step.error = f"Step timed out after {step.timeout} seconds"
            step.execution_time = time.time() - start_time
            
        except Exception as e:
            step.status = InteractionStatus.FAILED
            step.error = str(e)
            step.execution_time = time.time() - start_time
        
        # Handle retries
        if step.retry_count < step.max_retries:
            step.retry_count += 1
            step.status = InteractionStatus.PENDING
            self.logger.info(f"Retrying step {step.step_id} (attempt {step.retry_count})")
            return await self.execute_step(step)
        else:
            self.logger.error(f"Step {step.step_id} failed after {step.max_retries} retries")
            return False
    
    # Default executors (placeholders - would integrate with actual automation tools)
    async def _execute_click(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a click interaction."""
        x = parameters.get("x", 0)
        y = parameters.get("y", 0)
        button = parameters.get("button", "left")
        clicks = parameters.get("clicks", 1)
        
        # Simulate click execution
        await asyncio.sleep(0.1)
        
        return {
            "action": "click",
            "position": (x, y),
            "button": button,
            "clicks": clicks,
            "success": True
        }
    
    async def _execute_type(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a typing interaction."""
        text = parameters.get("text", "")
        interval = parameters.get("interval", 0.0)
        
        # Simulate typing
        await asyncio.sleep(len(text) * interval + 0.1)
        
        return {
            "action": "type",
            "text": text,
            "interval": interval,
            "success": True
        }
    
    async def _execute_scroll(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a scroll interaction."""
        clicks = parameters.get("clicks", 0)
        x = parameters.get("x")
        y = parameters.get("y")
        
        # Simulate scroll
        await asyncio.sleep(0.1)
        
        return {
            "action": "scroll",
            "clicks": clicks,
            "position": (x, y),
            "success": True
        }
    
    async def _execute_drag(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a drag interaction."""
        start_x = parameters.get("start_x", 0)
        start_y = parameters.get("start_y", 0)
        end_x = parameters.get("end_x", 0)
        end_y = parameters.get("end_y", 0)
        duration = parameters.get("duration", 0.0)
        
        # Simulate drag
        await asyncio.sleep(duration + 0.1)
        
        return {
            "action": "drag",
            "start": (start_x, start_y),
            "end": (end_x, end_y),
            "duration": duration,
            "success": True
        }
    
    async def _execute_wait(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a wait interaction."""
        seconds = parameters.get("seconds", 1.0)
        
        await asyncio.sleep(seconds)
        
        return {
            "action": "wait",
            "seconds": seconds,
            "success": True
        }
    
    async def _execute_screenshot(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a screenshot interaction."""
        save_path = parameters.get("save_path")
        region = parameters.get("region")
        
        # Simulate screenshot
        await asyncio.sleep(0.2)
        
        return {
            "action": "screenshot",
            "save_path": save_path,
            "region": region,
            "success": True
        }
    
    async def _execute_key_press(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a key press interaction."""
        key = parameters.get("key", "")
        
        # Simulate key press
        await asyncio.sleep(0.1)
        
        return {
            "action": "key_press",
            "key": key,
            "success": True
        }
    
    async def _execute_hotkey(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a hotkey interaction."""
        keys = parameters.get("keys", [])
        
        # Simulate hotkey
        await asyncio.sleep(0.2)
        
        return {
            "action": "hotkey",
            "keys": keys,
            "success": True
        }
    
    async def _execute_custom(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a custom interaction."""
        function_name = parameters.get("function")
        args = parameters.get("args", [])
        kwargs = parameters.get("kwargs", {})
        
        # Simulate custom execution
        await asyncio.sleep(0.1)
        
        return {
            "action": "custom",
            "function": function_name,
            "args": args,
            "kwargs": kwargs,
            "success": True
        }


class InteractionManager:
    """Manages interaction workflows and execution."""
    
    def __init__(self, jarvis=None):
        self.jarvis = jarvis
        self.executor = InteractionExecutor()
        self.workflows: Dict[str, InteractionWorkflow] = {}
        self.logger = get_logger("InteractionManager")
        
        # Statistics
        self.stats = {
            "total_workflows": 0,
            "completed_workflows": 0,
            "failed_workflows": 0,
            "total_steps": 0,
            "completed_steps": 0,
            "failed_steps": 0
        }
    
    def create_workflow(self, name: str, description: str = "") -> str:
        """Create a new interaction workflow."""
        workflow_id = str(uuid.uuid4())
        
        workflow = InteractionWorkflow(
            workflow_id=workflow_id,
            name=name,
            description=description
        )
        
        self.workflows[workflow_id] = workflow
        self.stats["total_workflows"] += 1
        
        self.logger.info(f"Created workflow {workflow_id}: {name}")
        return workflow_id
    
    def add_step(self, workflow_id: str, interaction_type: InteractionType,
                 parameters: Dict[str, Any], description: str = "",
                 timeout: Optional[float] = None, max_retries: int = 3) -> str:
        """Add a step to a workflow."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        step_id = str(uuid.uuid4())
        
        step = InteractionStep(
            step_id=step_id,
            interaction_type=interaction_type,
            parameters=parameters,
            description=description,
            timeout=timeout,
            max_retries=max_retries
        )
        
        self.workflows[workflow_id].steps.append(step)
        self.stats["total_steps"] += 1
        
        self.logger.info(f"Added step {step_id} to workflow {workflow_id}")
        return step_id
    
    def get_workflow(self, workflow_id: str) -> Optional[InteractionWorkflow]:
        """Get a workflow by ID."""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows with basic information."""
        return [
            {
                "workflow_id": workflow.workflow_id,
                "name": workflow.name,
                "description": workflow.description,
                "status": workflow.status.value,
                "steps_count": len(workflow.steps),
                "created_at": workflow.created_at.isoformat()
            }
            for workflow in self.workflows.values()
        ]
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Execute a complete workflow."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow.status = InteractionStatus.RUNNING
        workflow.started_at = datetime.utcnow()
        
        self.logger.info(f"Starting workflow {workflow_id}: {workflow.name}")
        
        results = {
            "workflow_id": workflow_id,
            "workflow_name": workflow.name,
            "total_steps": len(workflow.steps),
            "completed_steps": 0,
            "failed_steps": 0,
            "steps_results": [],
            "success": True
        }
        
        start_time = time.time()
        
        for step in workflow.steps:
            step_result = {
                "step_id": step.step_id,
                "interaction_type": step.interaction_type.value,
                "description": step.description,
                "success": False,
                "execution_time": None,
                "error": None
            }
            
            try:
                success = await self.executor.execute_step(step)
                
                step_result["success"] = success
                step_result["execution_time"] = step.execution_time
                step_result["error"] = step.error
                
                if success:
                    results["completed_steps"] += 1
                    self.stats["completed_steps"] += 1
                else:
                    results["failed_steps"] += 1
                    self.stats["failed_steps"] += 1
                    results["success"] = False
                
            except Exception as e:
                step_result["error"] = str(e)
                results["failed_steps"] += 1
                self.stats["failed_steps"] += 1
                results["success"] = False
                self.logger.error(f"Step {step.step_id} failed: {e}")
            
            results["steps_results"].append(step_result)
        
        # Update workflow status
        if results["success"]:
            workflow.status = InteractionStatus.COMPLETED
            self.stats["completed_workflows"] += 1
        else:
            workflow.status = InteractionStatus.FAILED
            self.stats["failed_workflows"] += 1
        
        workflow.completed_at = datetime.utcnow()
        workflow.total_execution_time = time.time() - start_time
        
        results["total_execution_time"] = workflow.total_execution_time
        results["workflow_status"] = workflow.status.value
        
        self.logger.info(f"Workflow {workflow_id} completed in {workflow.total_execution_time:.2f}s")
        
        return results
    
    async def execute_step_directly(self, interaction_type: InteractionType,
                                  parameters: Dict[str, Any], timeout: Optional[float] = None) -> Dict[str, Any]:
        """Execute a single step directly without creating a workflow."""
        step = InteractionStep(
            step_id=str(uuid.uuid4()),
            interaction_type=interaction_type,
            parameters=parameters,
            timeout=timeout
        )
        
        success = await self.executor.execute_step(step)
        
        return {
            "success": success,
            "result": step.result,
            "error": step.error,
            "execution_time": step.execution_time
        }
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a workflow."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return None
        
        completed_steps = sum(1 for step in workflow.steps if step.status == InteractionStatus.COMPLETED)
        failed_steps = sum(1 for step in workflow.steps if step.status == InteractionStatus.FAILED)
        running_steps = sum(1 for step in workflow.steps if step.status == InteractionStatus.RUNNING)
        
        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "status": workflow.status.value,
            "total_steps": len(workflow.steps),
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "running_steps": running_steps,
            "pending_steps": len(workflow.steps) - completed_steps - failed_steps - running_steps,
            "created_at": workflow.created_at.isoformat(),
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "total_execution_time": workflow.total_execution_time
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get interaction manager statistics."""
        return {
            "workflows": self.stats.copy(),
            "active_workflows": sum(1 for w in self.workflows.values() 
                                  if w.status == InteractionStatus.RUNNING),
            "total_workflows_created": len(self.workflows),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def save_workflow(self, workflow_id: str, file_path: str) -> bool:
        """Save a workflow to a JSON file."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        try:
            workflow_data = {
                "workflow_id": workflow.workflow_id,
                "name": workflow.name,
                "description": workflow.description,
                "steps": [
                    {
                        "interaction_type": step.interaction_type.value,
                        "parameters": step.parameters,
                        "description": step.description,
                        "timeout": step.timeout,
                        "max_retries": step.max_retries
                    }
                    for step in workflow.steps
                ],
                "metadata": workflow.metadata,
                "exported_at": datetime.utcnow().isoformat()
            }
            
            with open(file_path, 'w') as f:
                json.dump(workflow_data, f, indent=2)
            
            self.logger.info(f"Workflow {workflow_id} saved to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save workflow {workflow_id}: {e}")
            return False
    
    def load_workflow(self, file_path: str) -> str:
        """Load a workflow from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                workflow_data = json.load(f)
            
            workflow_id = workflow_data["workflow_id"]
            name = workflow_data["name"]
            description = workflow_data.get("description", "")
            
            # Create workflow
            workflow = InteractionWorkflow(
                workflow_id=workflow_id,
                name=name,
                description=description,
                metadata=workflow_data.get("metadata", {})
            )
            
            # Add steps
            for step_data in workflow_data["steps"]:
                step = InteractionStep(
                    step_id=str(uuid.uuid4()),
                    interaction_type=InteractionType(step_data["interaction_type"]),
                    parameters=step_data["parameters"],
                    description=step_data.get("description", ""),
                    timeout=step_data.get("timeout"),
                    max_retries=step_data.get("max_retries", 3)
                )
                workflow.steps.append(step)
            
            self.workflows[workflow_id] = workflow
            self.stats["total_workflows"] += 1
            self.stats["total_steps"] += len(workflow.steps)
            
            self.logger.info(f"Workflow loaded from {file_path}")
            return workflow_id
            
        except Exception as e:
            raise ValueError(f"Failed to load workflow from {file_path}: {e}")
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id in self.workflows:
            workflow = self.workflows[workflow_id]
            self.stats["total_steps"] -= len(workflow.steps)
            del self.workflows[workflow_id]
            self.logger.info(f"Deleted workflow {workflow_id}")
            return True
        return False 