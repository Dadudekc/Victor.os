"""
DreamOS Agent Loop Implementation
Provides the core loop functionality for all agents with validation enforcement.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union
import time

from dreamos.automation.validation_utils import (
    ImprovementValidator,
    ValidationResult,
    ValidationStatus,
)
from dreamos.core.config import AppConfig
from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.agents.base_agent import BaseAgent
from dreamos.core.project_board import ProjectBoardManager
from dreamos.automation.cursor_injector import CursorInjector
from dreamos.automation.response_retriever import ResponseRetriever
from dreamos.core.metrics.metrics_logger import MetricsLogger
from dreamos.core.alerting.alert_manager import AlertManager

logger = logging.getLogger(__name__)


class AgentLoop:
    """Core loop implementation for DreamOS agents with validation enforcement."""

    def __init__(
        self,
        agent: BaseAgent,
        config: AppConfig,
        pbm: ProjectBoardManager,
        agent_bus: Optional[AgentBus] = None,
        validation_state_dir: str = "runtime/state",
        workspace_root: Path = Path("."),
    ):
        """Initialize the agent loop.

        Args:
            agent: The agent instance to run the loop for
            config: Application configuration
            pbm: Project Board Manager instance
            agent_bus: Optional AgentBus instance for communication
            validation_state_dir: Directory for validation state storage
            workspace_root: Workspace root directory
        """
        self.agent = agent
        self.config = config
        self.pbm = pbm
        self.agent_bus = agent_bus
        self.validator = ImprovementValidator(state_dir=validation_state_dir)
        self.cycle_count = 0
        self._running = False
        self.logger = logging.getLogger(f"{agent.agent_id}.loop")
        
        # Initialize GUI automation components
        self.cursor_injector = CursorInjector(
            agent_id=agent.agent_id,
            target_window_title=config.gui_automation.cursor_window_title,
            coordinates_file=config.gui_automation.input_coords_file_path
        )
        self.response_retriever = ResponseRetriever(
            agent_id=agent.agent_id
        )
        
        # Setup mailbox path
        self.mailbox_path = Path(f"runtime/agent_mailboxes/{agent.agent_id}/inbox.json")
        self.mailbox_path.parent.mkdir(parents=True, exist_ok=True)

        self.workspace_root = workspace_root
        self.metrics = MetricsLogger(workspace_root)
        
        # Initialize alert manager
        self.alert_manager = AlertManager(
            config=config.alerting.model_dump(),
            workspace_root=workspace_root
        )

    async def run(self) -> None:
        """Start the main agent loop and run indefinitely."""
        self._running = True
        self.logger.info(f"Agent loop starting for {self.agent.agent_id}")

        # EDIT: Start background tasks for AlertManager's digest
        if self.alert_manager and hasattr(self.alert_manager, 'digest') and hasattr(self.alert_manager.digest, 'maybe_start_digest_task'):
            await self.alert_manager.digest.maybe_start_digest_task()
        
        # EDIT: Start cleanup task for AlertManager
        if self.alert_manager and hasattr(self.alert_manager, 'maybe_start_cleanup_task'):
            await self.alert_manager.maybe_start_cleanup_task()

        try:
            while self._running:
                await self.run_cycle()
        except Exception as e:
            self.logger.error(f"Error in agent loop: {e}", exc_info=True)

    async def run_cycle(self) -> None:
        """Execute a single cycle of the agent loop with validation enforcement."""
        cycle_start = time.time()
        errors_this_cycle = 0
        
        try:
            self.cycle_count += 1
            self.logger.debug(f"Starting cycle {self.cycle_count}")

            # Check for drift
            if self._check_for_drift():
                drift_start = time.time()
                self.logger.warning(f"Agent {self.agent.agent_id} detected in drift state")
                
                # Log drift event
                self.metrics.log_drift_event(
                    agent_id=self.agent.agent_id,
                    drift_start_time=drift_start
                )
                
                # Send drift alert
                await self.alert_manager.send_alert(
                    alert_type="DRIFT",
                    message=f"Agent {self.agent.agent_id} detected in drift state",
                    severity="warning",
                    details={
                        "agent_id": self.agent.agent_id,
                        "drift_start": datetime.fromtimestamp(drift_start).isoformat(),
                        "cycle_count": self.cycle_count
                    }
                )
                
                # Attempt recovery
                recovery_success = await self._attempt_recovery()
                
                # Log recovery attempt
                self.metrics.log_drift_event(
                    agent_id=self.agent.agent_id,
                    drift_start_time=drift_start,
                    drift_end_time=time.time(),
                    recovery_attempted=True,
                    recovery_successful=recovery_success
                )
                
                # Send recovery alert
                await self.alert_manager.send_alert(
                    alert_type="RECOVERY",
                    message=f"Agent {self.agent.agent_id} recovery {'successful' if recovery_success else 'failed'}",
                    severity="info" if recovery_success else "error",
                    details={
                        "agent_id": self.agent.agent_id,
                        "recovery_success": recovery_success,
                        "drift_duration_sec": time.time() - drift_start
                    }
                )
                
                if not recovery_success:
                    self.logger.error(f"Recovery failed for agent {self.agent.agent_id}")
                    return

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
            errors_this_cycle += 1
            self.logger.error(f"Error in agent loop cycle: {e}", exc_info=True)
            
            # Send error alert
            await self.alert_manager.send_alert(
                alert_type="ERROR",
                message=f"Agent {self.agent.agent_id} cycle error",
                severity="error",
                details={
                    "agent_id": self.agent.agent_id,
                    "error": str(e),
                    "cycle_count": self.cycle_count
                }
            )
            
            # Log error metrics
            self.metrics.log_task_execution_metrics(
                agent_id=self.agent.agent_id,
                task_id="cycle_error",
                start_time=cycle_start,
                end_time=time.time(),
                success=False,
                error=str(e)
            )
        
        # Log cycle completion metrics
        self.metrics.log_agent_cycle_update(
            agent_id=self.agent.agent_id,
            errors_this_cycle=errors_this_cycle
        )

    async def _check_mailbox(self) -> None:
        """Check agent's mailbox for new messages and route them appropriately."""
        if not self.mailbox_path.exists():
            return

        try:
            with open(self.mailbox_path, 'r') as f:
                messages = json.load(f)

            for message in messages:
                message_type = message.get('type')
                
                if message_type == 'inter_agent':
                    # Handle inter-agent communication
                    await self._handle_inter_agent_message(message)
                elif message_type == 'prompt':
                    # Forward to CursorInjector for LLM I/O
                    await self._handle_prompt_message(message)
                else:
                    self.logger.warning(f"Unknown message type: {message_type}")

            # Clear processed messages
            with open(self.mailbox_path, 'w') as f:
                json.dump([], f)

        except Exception as e:
            self.logger.error(f"Error processing mailbox: {e}", exc_info=True)
            # Log error metrics
            self.metrics.log_task_execution_metrics(
                agent_id=self.agent.agent_id,
                task_id="mailbox_error",
                start_time=time.time(),
                end_time=time.time(),
                success=False,
                error=str(e)
            )

    async def _handle_inter_agent_message(self, message: Dict[str, Any]) -> None:
        """Handle inter-agent communication messages."""
        subtype = message.get('subtype')
        start_time = time.time()
        
        try:
            # Log the message
            self.logger.info(f"Processing inter-agent message: {message}")
            
            # Update metrics
            await self._log_message_metrics('inter_agent', message)
            
            # Process based on message subtype
            if subtype == 'task_handoff':
                await self._handle_task_handoff(message)
            elif subtype == 'status_update':
                await self._handle_status_update(message)
            elif subtype == 'help_request':
                await self._handle_help_request(message)
            else:
                self.logger.warning(f"Unknown inter-agent message subtype: {subtype}")

            # Log successful message handling
            self.metrics.log_task_execution_metrics(
                agent_id=self.agent.agent_id,
                task_id=f"inter_agent_{subtype}",
                start_time=start_time,
                end_time=time.time(),
                success=True
            )

        except Exception as e:
            self.logger.error(f"Error handling inter-agent message: {e}", exc_info=True)
            # Log error metrics
            self.metrics.log_task_execution_metrics(
                agent_id=self.agent.agent_id,
                task_id=f"inter_agent_{subtype}_error",
                start_time=start_time,
                end_time=time.time(),
                success=False,
                error=str(e)
            )

    async def _handle_prompt_message(self, message: Dict[str, Any]) -> None:
        """Handle messages that require LLM interaction via Cursor."""
        start_time = time.time()
        
        try:
            # Log the message
            self.logger.info(f"Processing prompt message: {message}")
            
            # Update metrics
            await self._log_message_metrics('prompt', message)
            
            # Inject prompt into Cursor
            success = self.cursor_injector.inject_prompt(
                prompt_text=message['content'],
                response_format=message.get('response_format', 'text')
            )
            
            if success:
                # Retrieve response
                response = await self.response_retriever.get_response()
                
                # Log successful prompt handling
                self.metrics.log_task_execution_metrics(
                    agent_id=self.agent.agent_id,
                    task_id="prompt_response",
                    start_time=start_time,
                    end_time=time.time(),
                    success=True,
                    response_size=len(response) if response else 0
                )
            else:
                # Log failed prompt injection
                self.metrics.log_task_execution_metrics(
                    agent_id=self.agent.agent_id,
                    task_id="prompt_injection_failed",
                    start_time=start_time,
                    end_time=time.time(),
                    success=False,
                    error="Failed to inject prompt"
                )
            
            # Log response
            await self._log_response(response, message)
            
            # Handle response based on message subtype
            subtype = message.get('subtype')
            if subtype == 'task_execution':
                await self._handle_task_execution_response(response, message)
            elif subtype == 'help_response':
                await self._handle_help_response(response, message)
            else:
                self.logger.warning(f"Unknown prompt message subtype: {subtype}")

        except Exception as e:
            self.logger.error(f"Error handling prompt message: {e}", exc_info=True)
            # Log error metrics
            self.metrics.log_task_execution_metrics(
                agent_id=self.agent.agent_id,
                task_id="prompt_error",
                start_time=start_time,
                end_time=time.time(),
                success=False,
                error=str(e)
            )

    async def _handle_task_handoff(self, message: Dict[str, Any]) -> None:
        """Handle task handoff messages between agents.
        
        Args:
            message: Task handoff message containing:
                - task_id: ID of the task being handed off
                - priority: Task priority
                - context: Task context and requirements
                - from_agent: ID of the agent handing off the task
        """
        try:
            task_id = message.get('task_id')
            if not task_id:
                raise ValueError("Task handoff message missing task_id")

            # Log handoff attempt
            self.logger.info(f"Processing task handoff for task {task_id} from {message.get('from')}")
            
            # Check if we can accept the task
            if len(self.agent._active_tasks) >= self.config.swarm.max_concurrent_tasks:
                # Requeue the task
                await self._requeue_task(message)
                return

            # Update task status in project board
            if self.pbm:
                await self.pbm.update_task_status(
                    task_id=task_id,
                    status="claimed",
                    claimed_by=self.agent.agent_id,
                    details={
                        "handoff_from": message.get('from'),
                        "handoff_timestamp": datetime.utcnow().isoformat(),
                        "priority": message.get('priority', 'normal')
                    }
                )

            # Add to active tasks
            self.agent._active_tasks[task_id] = {
                "status": "claimed",
                "priority": message.get('priority', 'normal'),
                "context": message.get('context', {}),
                "handoff_from": message.get('from'),
                "handoff_timestamp": datetime.utcnow().isoformat()
            }

            # Log to devlog
            await self._log_to_devlog(
                f"Task {task_id} handed off from {message.get('from')}",
                {
                    "task_id": task_id,
                    "from_agent": message.get('from'),
                    "priority": message.get('priority'),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            # Update episode metrics
            if hasattr(self.agent, 'episode_metrics'):
                self.agent.episode_metrics['task_handoffs'].append({
                    "task_id": task_id,
                    "from_agent": message.get('from'),
                    "timestamp": datetime.utcnow().isoformat()
                })

            # Notify THEA if configured
            if self.agent_bus:
                await self.agent_bus.publish(
                    "thea.task.handoff",
                    {
                        "task_id": task_id,
                        "from_agent": message.get('from'),
                        "to_agent": self.agent.agent_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

        except Exception as e:
            self.logger.error(f"Error handling task handoff: {e}", exc_info=True)
            # Attempt to notify sender of failure
            await self._notify_handoff_failure(message, str(e))

    async def _handle_status_update(self, message: Dict[str, Any]) -> None:
        """Handle status update messages from other agents.
        
        Args:
            message: Status update message containing:
                - agent_id: ID of the agent sending the update
                - status: New status
                - details: Additional status details
        """
        try:
            agent_id = message.get('agent_id')
            status = message.get('status')
            if not agent_id or not status:
                raise ValueError("Status update message missing required fields")

            # Log status update
            self.logger.info(f"Processing status update from {agent_id}: {status}")
            
            # Update agent status in shared state
            status_path = Path(f"runtime/agent_status/{agent_id}.json")
            status_path.parent.mkdir(parents=True, exist_ok=True)
            
            status_data = {
                "agent_id": agent_id,
                "status": status,
                "details": message.get('details', {}),
                "last_update": datetime.utcnow().isoformat()
            }
            
            with open(status_path, 'w') as f:
                json.dump(status_data, f, indent=2)

            # Log to devlog
            await self._log_to_devlog(
                f"Status update from {agent_id}: {status}",
                status_data
            )

            # Update episode metrics
            if hasattr(self.agent, 'episode_metrics'):
                self.agent.episode_metrics['status_updates'].append(status_data)

            # Notify THEA if configured
            if self.agent_bus:
                await self.agent_bus.publish(
                    "thea.agent.status",
                    status_data
                )

        except Exception as e:
            self.logger.error(f"Error handling status update: {e}", exc_info=True)

    async def _handle_help_request(self, message: Dict[str, Any]) -> None:
        """Handle help request messages from other agents.
        
        Args:
            message: Help request message containing:
                - from_agent: ID of the agent requesting help
                - context: Help request context
                - urgency: Urgency level of the request
        """
        try:
            from_agent = message.get('from')
            context = message.get('context')
            if not from_agent or not context:
                raise ValueError("Help request message missing required fields")

            # Log help request
            self.logger.info(f"Processing help request from {from_agent}")
            
            # Check if we can help
            if not self._can_provide_help(context):
                await self._decline_help_request(message)
                return

            # Create help response message
            help_response = {
                "type": "inter_agent",
                "subtype": "help_response",
                "from": self.agent.agent_id,
                "to": from_agent,
                "context": context,
                "can_help": True,
                "availability": self._get_help_availability(),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Send response to requesting agent's mailbox
            response_path = Path(f"runtime/agent_mailboxes/{from_agent}/inbox.json")
            response_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing messages
            existing_messages = []
            if response_path.exists():
                with open(response_path, 'r') as f:
                    existing_messages = json.load(f)
            
            # Add our response
            existing_messages.append(help_response)
            
            # Write back
            with open(response_path, 'w') as f:
                json.dump(existing_messages, f, indent=2)

            # Log to devlog
            await self._log_to_devlog(
                f"Help response sent to {from_agent}",
                help_response
            )

            # Update episode metrics
            if hasattr(self.agent, 'episode_metrics'):
                self.agent.episode_metrics['help_responses'].append(help_response)

            # Notify THEA if configured
            if self.agent_bus:
                await self.agent_bus.publish(
                    "thea.agent.help",
                    {
                        "requesting_agent": from_agent,
                        "responding_agent": self.agent.agent_id,
                        "context": context,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

        except Exception as e:
            self.logger.error(f"Error handling help request: {e}", exc_info=True)
            # Attempt to notify requester of failure
            await self._notify_help_request_failure(message, str(e))

    async def _handle_task_execution_response(self, response: Any, message: Dict[str, Any]) -> None:
        """Handle LLM response for task execution.
        
        Args:
            response: LLM response from Cursor
            message: Original prompt message
        """
        try:
            task_id = message.get('task_id')
            if not task_id:
                raise ValueError("Task execution response missing task_id")

            # Log response
            self.logger.info(f"Processing task execution response for task {task_id}")
            
            # Update task status
            if task_id in self.agent._active_tasks:
                self.agent._active_tasks[task_id].update({
                    "status": "completed",
                    "result": response,
                    "completion_timestamp": datetime.utcnow().isoformat()
                })

                # Update project board
                if self.pbm:
                    await self.pbm.update_task_status(
                        task_id=task_id,
                        status="completed",
                        details={
                            "result": response,
                            "completion_timestamp": datetime.utcnow().isoformat()
                        }
                    )

            # Log to devlog
            await self._log_to_devlog(
                f"Task {task_id} execution completed",
                {
                    "task_id": task_id,
                    "result": response,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            # Update episode metrics
            if hasattr(self.agent, 'episode_metrics'):
                self.agent.episode_metrics['task_completions'].append({
                    "task_id": task_id,
                    "timestamp": datetime.utcnow().isoformat()
                })

            # Notify THEA if configured
            if self.agent_bus:
                await self.agent_bus.publish(
                    "thea.task.completion",
                    {
                        "task_id": task_id,
                        "agent_id": self.agent.agent_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

        except Exception as e:
            self.logger.error(f"Error handling task execution response: {e}", exc_info=True)

    async def _handle_help_response(self, response: Any, message: Dict[str, Any]) -> None:
        """Handle LLM response for help request.
        
        Args:
            response: LLM response from Cursor
            message: Original prompt message
        """
        try:
            from_agent = message.get('from')
            if not from_agent:
                raise ValueError("Help response missing from_agent")

            # Log response
            self.logger.info(f"Processing help response for {from_agent}")
            
            # Create help response message
            help_response = {
                "type": "inter_agent",
                "subtype": "help_response",
                "from": self.agent.agent_id,
                "to": from_agent,
                "content": response,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Send to requesting agent's mailbox
            response_path = Path(f"runtime/agent_mailboxes/{from_agent}/inbox.json")
            response_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing messages
            existing_messages = []
            if response_path.exists():
                with open(response_path, 'r') as f:
                    existing_messages = json.load(f)
            
            # Add our response
            existing_messages.append(help_response)
            
            # Write back
            with open(response_path, 'w') as f:
                json.dump(existing_messages, f, indent=2)

            # Log to devlog
            await self._log_to_devlog(
                f"Help response sent to {from_agent}",
                help_response
            )

            # Update episode metrics
            if hasattr(self.agent, 'episode_metrics'):
                self.agent.episode_metrics['help_responses'].append(help_response)

            # Notify THEA if configured
            if self.agent_bus:
                await self.agent_bus.publish(
                    "thea.agent.help.response",
                    {
                        "from_agent": self.agent.agent_id,
                        "to_agent": from_agent,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

        except Exception as e:
            self.logger.error(f"Error handling help response: {e}", exc_info=True)

    async def _log_to_devlog(self, message: str, data: Dict[str, Any]) -> None:
        """Log message and data to devlog.
        
        Args:
            message: Log message
            data: Additional data to log
        """
        try:
            devlog_path = Path(f"runtime/devlog/agents/{self.agent.agent_id}/devlog.md")
            devlog_path.parent.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.utcnow().isoformat()
            log_entry = f"\n## {timestamp}\n\n{message}\n\n```json\n{json.dumps(data, indent=2)}\n```\n"
            
            with open(devlog_path, 'a') as f:
                f.write(log_entry)
                
        except Exception as e:
            self.logger.error(f"Error writing to devlog: {e}", exc_info=True)

    def _can_provide_help(self, context: Dict[str, Any]) -> bool:
        """Check if agent can provide help for given context.
        
        Args:
            context: Help request context
            
        Returns:
            bool: True if agent can help
        """
        # Implement help capability check based on agent's expertise
        return True  # Placeholder

    def _get_help_availability(self) -> Dict[str, Any]:
        """Get agent's current help availability.
        
        Returns:
            Dict containing availability information
        """
        return {
            "available": len(self.agent._active_tasks) < self.config.swarm.max_concurrent_tasks,
            "active_tasks": len(self.agent._active_tasks),
            "max_tasks": self.config.swarm.max_concurrent_tasks
        }

    async def _requeue_task(self, message: Dict[str, Any]) -> None:
        """Requeue a task that couldn't be accepted.
        
        Args:
            message: Original task handoff message
        """
        try:
            if self.pbm:
                await self.pbm.update_task_status(
                    task_id=message['task_id'],
                    status="pending",
                    details={
                        "requeue_reason": "agent_at_capacity",
                        "requeue_timestamp": datetime.utcnow().isoformat()
                    }
                )
                
            # Log requeue
            self.logger.info(f"Requeued task {message['task_id']} - agent at capacity")
            
        except Exception as e:
            self.logger.error(f"Error requeueing task: {e}", exc_info=True)

    async def _notify_handoff_failure(self, message: Dict[str, Any], error: str) -> None:
        """Notify agent of task handoff failure.
        
        Args:
            message: Original task handoff message
            error: Error message
        """
        try:
            from_agent = message.get('from')
            if not from_agent:
                return
                
            failure_notice = {
                "type": "inter_agent",
                "subtype": "handoff_failure",
                "from": self.agent.agent_id,
                "to": from_agent,
                "task_id": message.get('task_id'),
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to original agent's mailbox
            response_path = Path(f"runtime/agent_mailboxes/{from_agent}/inbox.json")
            response_path.parent.mkdir(parents=True, exist_ok=True)
            
            existing_messages = []
            if response_path.exists():
                with open(response_path, 'r') as f:
                    existing_messages = json.load(f)
            
            existing_messages.append(failure_notice)
            
            with open(response_path, 'w') as f:
                json.dump(existing_messages, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error notifying handoff failure: {e}", exc_info=True)

    async def _notify_help_request_failure(self, message: Dict[str, Any], error: str) -> None:
        """Notify agent of help request failure.
        
        Args:
            message: Original help request message
            error: Error message
        """
        try:
            from_agent = message.get('from')
            if not from_agent:
                return
                
            failure_notice = {
                "type": "inter_agent",
                "subtype": "help_request_failure",
                "from": self.agent.agent_id,
                "to": from_agent,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to original agent's mailbox
            response_path = Path(f"runtime/agent_mailboxes/{from_agent}/inbox.json")
            response_path.parent.mkdir(parents=True, exist_ok=True)
            
            existing_messages = []
            if response_path.exists():
                with open(response_path, 'r') as f:
                    existing_messages = json.load(f)
            
            existing_messages.append(failure_notice)
            
            with open(response_path, 'w') as f:
                json.dump(existing_messages, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error notifying help request failure: {e}", exc_info=True)

    async def _decline_help_request(self, message: Dict[str, Any]) -> None:
        """Decline a help request.
        
        Args:
            message: Original help request message
        """
        try:
            from_agent = message.get('from')
            if not from_agent:
                return
                
            decline_notice = {
                "type": "inter_agent",
                "subtype": "help_declined",
                "from": self.agent.agent_id,
                "to": from_agent,
                "reason": "cannot_provide_help",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to original agent's mailbox
            response_path = Path(f"runtime/agent_mailboxes/{from_agent}/inbox.json")
            response_path.parent.mkdir(parents=True, exist_ok=True)
            
            existing_messages = []
            if response_path.exists():
                with open(response_path, 'r') as f:
                    existing_messages = json.load(f)
            
            existing_messages.append(decline_notice)
            
            with open(response_path, 'w') as f:
                json.dump(existing_messages, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error declining help request: {e}", exc_info=True)

    async def _log_message_metrics(self, message_type: str, message: Dict[str, Any]) -> None:
        """Log message metrics for monitoring."""
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'agent_id': self.agent.agent_id,
            'message_type': message_type,
            'message_subtype': message.get('subtype'),
            'from_agent': message.get('from'),
            'to_agent': message.get('to'),
        }
        
        # Log to devlog
        self.logger.debug(f"Message metrics: {metrics}")
        
        # Update episode metrics if available
        if hasattr(self.agent, 'episode_metrics'):
            self.agent.episode_metrics['message_metrics'].append(metrics)

    async def _log_response(self, response: Any, original_message: Dict[str, Any]) -> None:
        """Log LLM response for monitoring."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'agent_id': self.agent.agent_id,
            'message_id': original_message.get('message_id'),
            'response_type': original_message.get('expected_response_type'),
            'response': response,
        }
        
        # Log to devlog
        self.logger.debug(f"LLM response: {log_entry}")
        
        # Update episode metrics if available
        if hasattr(self.agent, 'episode_metrics'):
            self.agent.episode_metrics['llm_responses'].append(log_entry)

    def _check_for_drift(self) -> bool:
        """Check if agent has drifted from expected state.
        
        Returns:
            bool: True if agent is in drift state
        """
        try:
            # Read agent status
            status = self.metrics._read_status()
            if self.agent.agent_id not in status["agents"]:
                return True
            
            agent_status = status["agents"][self.agent.agent_id]
            last_active = datetime.fromisoformat(agent_status["last_active"])
            now = datetime.utcnow()
            
            # Check if agent has exceeded drift threshold
            drift_threshold = status["system"]["drift_threshold"]
            time_since_active = (now - last_active).total_seconds()
            
            return time_since_active > drift_threshold
            
        except Exception as e:
            self.logger.error(f"Error checking for drift: {e}")
            return True
    
    async def _attempt_recovery(self) -> bool:
        """Attempt to recover agent from drift state.
        
        Returns:
            bool: True if recovery was successful
        """
        try:
            # 1. Clear any stale state
            self.agent._active_tasks.clear()
            
            # 2. Reset agent status
            status = self.metrics._read_status()
            if self.agent.agent_id in status["agents"]:
                agent_status = status["agents"][self.agent.agent_id]
                agent_status.update({
                    "status": "active",
                    "last_active": datetime.utcnow().isoformat(),
                    "current_task": None
                })
                self.metrics._write_status(status)
            
            # 3. Reinitialize agent components
            if self.agent_bus:
                await self.agent_bus.reconnect()
            
            # 4. Verify recovery
            return self._verify_recovery()
            
        except Exception as e:
            self.logger.error(f"Error during recovery: {e}")
            return False
    
    def _verify_recovery(self) -> bool:
        """Verify that agent has recovered successfully.
        
        Returns:
            bool: True if agent is in healthy state
        """
        try:
            # Check agent status
            status = self.metrics._read_status()
            if self.agent.agent_id not in status["agents"]:
                return False
            
            agent_status = status["agents"][self.agent.agent_id]
            if agent_status["status"] != "active":
                return False
            
            # Check agent components
            if self.agent_bus and not self.agent_bus.is_connected():
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error verifying recovery: {e}")
            return False

    async def _check_new_tasks(self) -> None:
        """Check for new tasks from the Project Board Manager."""
        self.logger.debug("Checking for new tasks.")
        try:
            # Placeholder: Actual logic to fetch and assign tasks will be more complex
            # This might involve querying pbm for tasks assigned to this agent_id
            # and then adding them to self.agent._active_tasks or a similar queue.
            # For now, we'll just log that we're checking.
            if self.pbm:
                # Example: new_tasks = await self.pbm.get_new_tasks_for_agent(self.agent.agent_id)
                # for task in new_tasks:
                #     self.agent.assign_task(task) # Assuming agent has an assign_task method
                pass # Replace with actual task fetching logic
            self.logger.debug("Finished checking for new tasks.")
        except Exception as e:
            self.logger.error(f"Error checking for new tasks: {e}", exc_info=True)
            # Optionally, send an alert or log detailed metrics

    async def _process_active_tasks(self) -> None:
        """Process any active tasks assigned to the agent."""
        self.logger.debug("Processing active tasks.")
        # Placeholder: Logic to iterate through self.agent._active_tasks
        # and execute them. This will likely involve calling methods on self.agent
        # or dispatching to other components.
        active_task_ids = list(self.agent._active_tasks.keys()) # Get a copy of keys
        for task_id in active_task_ids:
            task = self.agent._active_tasks.get(task_id)
            if task:
                try:
                    self.logger.info(f"Starting processing for task: {task_id}")
                    # Simulate task processing by agent
                    # result = await self.agent.process_task(task) 
                    # For now, just log and remove
                    await asyncio.sleep(0.1) # Simulate work
                    self.logger.info(f"Completed processing for task: {task_id}")
                    # Remove task from active list or mark as completed
                    # del self.agent._active_tasks[task_id] 
                except Exception as e:
                    self.logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
        self.logger.debug("Finished processing active tasks.")

    async def _validate_completed_tasks(self) -> None:
        """Validate any tasks that have been completed by the agent."""
        self.logger.debug("Validating completed tasks.")
        # Placeholder: Logic to check for tasks marked as completed
        # and run validation checks on them using self.validator.
        # For now, we'll just log that we're checking.
        # completed_tasks = self.pbm.get_completed_tasks_for_agent(self.agent.agent_id)
        # for task in completed_tasks:
        #     validation_result = self.validator.validate(task_output, task_criteria)
        #     if validation_result.status == ValidationStatus.SUCCESS:
        #         self.pbm.mark_task_validated(task.id)
        #     else:
        #         self.pbm.mark_task_validation_failed(task.id, validation_result.feedback)
        self.logger.debug("Finished validating completed tasks.")

    # ... rest of the existing methods ... 