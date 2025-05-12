"""
DreamOS Agent Loop Implementation
Provides the core loop functionality for all agents with validation enforcement.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from dreamos.automation.validation_utils import ImprovementValidator, ValidationStatus, ValidationResult
from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.core.coordination.base_agent import BaseAgent
from dreamos.core.config import AppConfig
from dreamos.core.project_board import ProjectBoardManager

logger = logging.getLogger(__name__)

class AgentLoop:
    """Core loop implementation for DreamOS agents with validation enforcement."""
    
    def __init__(
        self,
        agent: BaseAgent,
        config: AppConfig,
        pbm: ProjectBoardManager,
        agent_bus: Optional[AgentBus] = None,
        validation_state_dir: str = "runtime/state"
    ):
        """Initialize the agent loop.
        
        Args:
            agent: The agent instance to run the loop for
            config: Application configuration
            pbm: Project Board Manager instance
            agent_bus: Optional AgentBus instance for communication
            validation_state_dir: Directory for validation state storage
        """
        self.agent = agent
        self.config = config
        self.pbm = pbm
        self.agent_bus = agent_bus
        self.validator = ImprovementValidator(state_dir=validation_state_dir)
        self.cycle_count = 0
        self._running = False
        self.logger = logging.getLogger(f"{agent.agent_id}.loop")

    async def run_cycle(self) -> None:
        """Execute a single cycle of the agent loop with validation enforcement."""
        try:
            self.cycle_count += 1
            self.logger.debug(f"Starting cycle {self.cycle_count}")

            # 1. Check mailbox for new messages
            await self._check_mailbox()

            # 2. Process current task if any
            if self.agent._active_tasks:
                await self._process_active_tasks()

            # 3. Check for new tasks
            await self._check_new_tasks()

            # 4. Validate any completed tasks
            await self._validate_completed_tasks()

            self.logger.debug(f"Completed cycle {self.cycle_count}")

        except Exception as e:
            self.logger.error(f"Error in agent loop cycle: {e}", exc_info=True)
            await self._handle_cycle_error(e)

    async def _check_mailbox(self) -> None:
        """Check agent's mailbox for new messages."""
        # Implementation depends on mailbox system
        pass

    async def _process_active_tasks(self) -> None:
        """Process currently active tasks."""
        for task_id, task in self.agent._active_tasks.items():
            try:
                # Execute task
                result = await self.agent.execute_task(task)
                
                # If task is marked complete, validate it
                if result.get("status") == "completed":
                    await self._validate_task_completion(task_id, task, result)
                    
            except Exception as e:
                self.logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
                await self._handle_task_error(task_id, e)

    async def _check_new_tasks(self) -> None:
        """Check for and claim new tasks."""
        # Implementation depends on task management system
        pass

    async def _validate_completed_tasks(self) -> None:
        """Validate any tasks marked as completed."""
        for task_id, task in self.agent._active_tasks.items():
            if task.get("status") == "completed":
                await self._validate_task_completion(task_id, task, task.get("result", {}))

    async def _validate_task_completion(
        self, 
        task_id: str, 
        task: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """Validate a completed task against required criteria.
        
        Args:
            task_id: ID of the completed task
            task: Task data
            result: Task execution result
        """
        # Prepare validation data
        validation_data = {
            "tests": result.get("tests", []),
            "documentation": result.get("documentation", {}),
            "implementation": result.get("implementation", {}),
            "demonstration": result.get("demonstration", {})
        }

        # Validate the task
        validation_result = self.validator.validate_improvement(
            improvement_id=task_id,
            **validation_data
        )

        if validation_result.status != ValidationStatus.PASSED:
            # Log violation
            self.logger.warning(
                f"Task {task_id} marked complete without proper validation. "
                f"Status: {validation_result.status}, "
                f"Message: {validation_result.message}"
            )

            # Log to empathy system
            await self._log_validation_violation(task_id, validation_result)

            # Block further progress
            await self._block_task_progress(task_id, validation_result)

            # Escalate if needed
            if self._should_escalate(task_id):
                await self._escalate_to_thea(task_id, validation_result)

    async def _log_validation_violation(
        self, 
        task_id: str,
        validation_result: ValidationResult
    ) -> None:
        """Log validation violation to empathy system."""
        if self.agent_bus:
            await self.agent_bus.publish(
                "agent.validation.violation",
                {
                    "agent_id": self.agent.agent_id,
                    "task_id": task_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "validation_result": validation_result.details
                }
            )

    async def _block_task_progress(
        self,
        task_id: str,
        validation_result: ValidationResult
    ) -> None:
        """Block further progress on the task."""
        # Revert task status
        self.agent._active_tasks[task_id]["status"] = "validation_failed"
        
        # Update task with validation details
        self.agent._active_tasks[task_id]["validation"] = {
            "status": validation_result.status.value,
            "message": validation_result.message,
            "details": validation_result.details,
            "timestamp": validation_result.timestamp
        }

        # Notify task management system
        if self.pbm:
            await self.pbm.update_task_status(
                task_id=task_id,
                status="validation_failed",
                details=validation_result.details
            )

    def _should_escalate(self, task_id: str) -> bool:
        """Determine if validation failure should be escalated to THEA."""
        # Check if this is a repeated violation
        task = self.agent._active_tasks.get(task_id, {})
        validation_history = task.get("validation_history", [])
        
        # Escalate if more than 2 validation failures
        return len(validation_history) >= 2

    async def _escalate_to_thea(
        self,
        task_id: str,
        validation_result: ValidationResult
    ) -> None:
        """Escalate validation failure to THEA."""
        if self.agent_bus:
            await self.agent_bus.publish(
                "thea.validation.escalation",
                {
                    "agent_id": self.agent.agent_id,
                    "task_id": task_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "validation_result": validation_result.details,
                    "validation_history": self.agent._active_tasks[task_id].get("validation_history", [])
                }
            )

    async def _handle_cycle_error(self, error: Exception) -> None:
        """Handle errors in the agent loop cycle."""
        # Log error
        self.logger.error(f"Cycle error: {error}", exc_info=True)
        
        # Notify error monitoring system
        if self.agent_bus:
            await self.agent_bus.publish(
                "agent.error",
                {
                    "agent_id": self.agent.agent_id,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    async def _handle_task_error(self, task_id: str, error: Exception) -> None:
        """Handle errors in task processing."""
        # Log error
        self.logger.error(f"Task {task_id} error: {error}", exc_info=True)
        
        # Update task status
        self.agent._active_tasks[task_id]["status"] = "error"
        self.agent._active_tasks[task_id]["error"] = {
            "type": type(error).__name__,
            "message": str(error),
            "timestamp": datetime.utcnow().isoformat()
        }

        # Notify task management system
        if self.pbm:
            await self.pbm.update_task_status(
                task_id=task_id,
                status="error",
                details={"error": str(error)}
            )
        # Always publish agent.error event
        if self.agent_bus:
            await self.agent_bus.publish(
                "agent.error",
                {
                    "agent_id": self.agent.agent_id,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "timestamp": self.agent._active_tasks[task_id]["error"]["timestamp"]
                }
            )

    async def start(self) -> None:
        """Start the agent loop."""
        self._running = True
        self.logger.info(f"Starting agent loop for {self.agent.agent_id}")
        
        while self._running:
            await self.run_cycle()
            await asyncio.sleep(self.config.agent_loop_interval)

    async def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        self.logger.info(f"Stopping agent loop for {self.agent.agent_id}") 