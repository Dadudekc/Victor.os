"""
DreamOS Agent Loop Implementation
Provides the core loop functionality for all agents with validation enforcement.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
import time

from dreamos.automation.validation_utils import (
    ImprovementValidator,
    ValidationResult,
    ValidationStatus,
)
from dreamos.core.config import AppConfig
from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.core.coordination.base_agent import BaseAgent
from dreamos.core.project_board import ProjectBoardManager
from dreamos.automation.cursor_injector import CursorInjector
from dreamos.automation.response_retriever import ResponseRetriever
from dreamos.core.metrics.metrics_logger import MetricsLogger
from dreamos.core.alerting.alert_manager import AlertManager
from dreamos.coordination.messaging import Message, MessageHandler, MessagePriority, MessageMode
from dreamos.coordination.agent_coordinates import AgentRegistry, AgentCoordinates

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
        
        # Initialize messaging system
        self.coordination_path = workspace_root / "src/dreamos/coordination"
        self.registry = AgentRegistry(self.coordination_path)
        self.message_handler = MessageHandler(self.coordination_path)
        
        # Register agent if not already registered
        if not self.registry.get_agent(agent.agent_id):
            self.registry.register_agent(
                agent_id=agent.agent_id,
                name=agent.__class__.__name__,
                coordinates=AgentCoordinates(x=0, y=0, z=0)
            )
        
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

            # Process incoming messages
            await self._process_messages()

            # Check directive compliance
            await self._check_directive_compliance()

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

    async def _process_messages(self) -> None:
        """Process incoming messages using the new messaging system."""
        try:
            # Get all unread messages
            messages = self.message_handler.get_messages(self.agent.agent_id)
            unread_count = len(messages)
            
            if unread_count > 0:
                self.logger.info(f"Processing {unread_count} unread messages")
                
                for message in messages:
                    # Process message based on priority
                    if message.priority >= MessagePriority.HIGH:
                        await self._handle_priority_message(message)
                    else:
                        await self._handle_normal_message(message)
                    
                    # Mark message as read after processing
                    self.message_handler.mark_read(self.agent.agent_id, message.id)
                    
            else:
                self.logger.debug("No new messages to process")
                
        except Exception as e:
            self.logger.error(f"Error processing messages: {e}", exc_info=True)

    async def _handle_priority_message(self, message: Message) -> None:
        """Handle high priority messages."""
        try:
            # Extract task information if present
            if "task:" in message.content.lower():
                task_info = self._parse_task_message(message.content)
                if task_info:
                    await self._queue_task(task_info)
            
            # Handle other priority messages
            self.logger.info(f"Processing priority message from {message.from_agent}: {message.content}")
            
            # Notify agent bus if configured
            if self.agent_bus:
                await self.agent_bus.publish(
                    "agent.priority_message",
                    {
                        "from_agent": message.from_agent,
                        "content": message.content,
                        "timestamp": message.timestamp.isoformat()
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Error handling priority message: {e}", exc_info=True)

    async def _handle_normal_message(self, message: Message) -> None:
        """Handle normal priority messages."""
        try:
            self.logger.info(f"Processing message from {message.from_agent}: {message.content}")
            
            # Update agent status if needed
            if "status:" in message.content.lower():
                await self._handle_status_update({
                    "agent_id": message.from_agent,
                    "status": message.content.split("status:")[1].strip(),
                    "details": message.metadata
                })
                
        except Exception as e:
            self.logger.error(f"Error handling normal message: {e}", exc_info=True)

    def _parse_task_message(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse task information from message content."""
        try:
            # Example task format:
            # task: INTEGRATE-MESSAGING-TO-AGENT-LOOP-001
            # objective: |
            #   Replace legacy inbox polling with messaging.py integration
            # actions:
            #   - Refactor agent_loop.py
            #   - Log unread message count
            # status: 🟡 pending approval
            
            lines = content.split("\n")
            task_info = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith("task:"):
                    task_info["id"] = line.split("task:")[1].strip()
                elif line.startswith("objective:"):
                    task_info["objective"] = line.split("objective:")[1].strip()
                elif line.startswith("actions:"):
                    task_info["actions"] = []
                elif line.startswith("- ") and "actions" in task_info:
                    task_info["actions"].append(line[2:].strip())
                elif line.startswith("status:"):
                    task_info["status"] = line.split("status:")[1].strip()
            
            return task_info if task_info.get("id") else None
            
        except Exception as e:
            self.logger.error(f"Error parsing task message: {e}")
            return None

    async def _queue_task(self, task_info: Dict[str, Any]) -> None:
        """Queue a task for processing."""
        try:
            if self.pbm:
                await self.pbm.create_task(
                    task_id=task_info["id"],
                    objective=task_info["objective"],
                    actions=task_info.get("actions", []),
                    status=task_info.get("status", "pending"),
                    assigned_agent=self.agent.agent_id
                )
                self.logger.info(f"Queued task {task_info['id']} for processing")
            else:
                self.logger.warning("Project Board Manager not configured, cannot queue task")
                
        except Exception as e:
            self.logger.error(f"Error queueing task: {e}", exc_info=True)

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
            
            # Parse performance metrics if present
            performance_metrics = {}
            if "performance" in message.get('details', {}):
                perf_details = message['details']['performance']
                performance_metrics = {
                    "tool_phases": perf_details.get('tool_phases', {}),
                    "cache_stats": perf_details.get('cache_stats', {}),
                    "bottlenecks": perf_details.get('bottlenecks', []),
                    "execution_times": perf_details.get('execution_times', {})
                }
                
                # Log performance metrics
                self.logger.info(f"Performance metrics from {agent_id}: {performance_metrics}")
                
                # Update metrics logger
                self.metrics.log_performance_metrics(
                    agent_id=agent_id,
                    metrics=performance_metrics
                )
            
            # Update agent status in shared state
            status_path = Path(f"runtime/agent_status/{agent_id}.json")
            status_path.parent.mkdir(parents=True, exist_ok=True)
            
            status_data = {
                "agent_id": agent_id,
                "status": status,
                "details": message.get('details', {}),
                "performance_metrics": performance_metrics,
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

    async def _handle_captain_directive(self, message: Message) -> None:
        """Handle captain directives with strict compliance enforcement.
        
        Args:
            message: Captain directive message
        """
        try:
            # Log directive receipt
            self.logger.warning(f"Received captain directive: {message.content}")
            
            # Extract required actions
            actions = message.metadata.get('required_actions', [])
            deadline = message.metadata.get('deadline')
            
            # Create compliance plan
            compliance_plan = {
                "directive_id": message.id,
                "received_at": datetime.utcnow().isoformat(),
                "deadline": deadline,
                "actions": actions,
                "status": "in_progress",
                "completion_percentage": 0
            }
            
            # Store compliance plan
            compliance_path = Path(f"runtime/compliance/{self.agent.agent_id}/{message.id}.json")
            compliance_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(compliance_path, 'w') as f:
                json.dump(compliance_plan, f, indent=2)
            
            # Send acknowledgment
            if self.agent_bus:
                await self.agent_bus.publish(
                    "thea.captain.directive.ack",
                    {
                        "agent_id": self.agent.agent_id,
                        "directive_id": message.id,
                        "acknowledged_at": datetime.utcnow().isoformat(),
                        "compliance_plan": compliance_plan
                    }
                )
            
            # Log to devlog
            await self._log_to_devlog(
                f"Received captain directive {message.id}",
                compliance_plan
            )
            
            # Update episode metrics
            if hasattr(self.agent, 'episode_metrics'):
                self.agent.episode_metrics['captain_directives'].append({
                    "directive_id": message.id,
                    "received_at": datetime.utcnow().isoformat(),
                    "actions": actions,
                    "deadline": deadline
                })
            
            # Send alert
            await self.alert_manager.send_alert(
                alert_type="CAPTAIN_DIRECTIVE",
                message=f"Received captain directive: {message.content}",
                severity="warning",
                details=compliance_plan
            )
            
        except Exception as e:
            self.logger.error(f"Error handling captain directive: {e}", exc_info=True)
            # Send failure alert
            await self.alert_manager.send_alert(
                alert_type="CAPTAIN_DIRECTIVE_ERROR",
                message=f"Failed to process captain directive: {str(e)}",
                severity="error",
                details={
                    "directive_id": message.id,
                    "error": str(e)
                }
            )

    async def _check_directive_compliance(self) -> None:
        """Check compliance status of all active captain directives."""
        try:
            compliance_dir = Path(f"runtime/compliance/{self.agent.agent_id}")
            if not compliance_dir.exists():
                return
                
            for directive_file in compliance_dir.glob("*.json"):
                with open(directive_file) as f:
                    compliance_plan = json.load(f)
                    
                # Skip completed directives
                if compliance_plan["status"] == "completed":
                    continue
                    
                # Check deadline
                deadline = datetime.fromisoformat(compliance_plan["deadline"]) if compliance_plan.get("deadline") else None
                deadline_met = True if not deadline else datetime.utcnow() <= deadline
                
                # Check action completion
                actions_status = {}
                for action in compliance_plan["actions"]:
                    # Check if action is marked complete in agent's state
                    action_key = f"action_{action.lower().replace(' ', '_')}"
                    actions_status[action] = self.agent._active_tasks.get(action_key, {}).get("completed", False)
                
                # Calculate completion percentage
                total_actions = len(actions_status)
                completed_actions = sum(1 for status in actions_status.values() if status)
                completion_percentage = (completed_actions / total_actions * 100) if total_actions > 0 else 0
                
                # Update compliance plan
                compliance_plan.update({
                    "last_check": datetime.utcnow().isoformat(),
                    "actions_status": actions_status,
                    "completion_percentage": completion_percentage,
                    "deadline_met": deadline_met
                })
                
                # Check for non-compliance
                if not deadline_met or completion_percentage < 100:
                    await self._handle_non_compliance(compliance_plan)
                else:
                    # Mark as completed
                    compliance_plan["status"] = "completed"
                    compliance_plan["completed_at"] = datetime.utcnow().isoformat()
                    
                    # Send completion report
                    completion_report = Message.create_compliance_report(
                        from_agent=self.agent.agent_id,
                        to_agent="Agent-7",  # Captain
                        directive_id=compliance_plan["directive_id"],
                        actions_status=actions_status,
                        completion_percentage=completion_percentage,
                        deadline_met=deadline_met,
                        notes="Directive completed successfully"
                    )
                    self.message_handler.send_message(completion_report)
                
                # Save updated compliance plan
                with open(directive_file, 'w') as f:
                    json.dump(compliance_plan, f, indent=2)
                    
        except Exception as e:
            self.logger.error(f"Error checking directive compliance: {e}", exc_info=True)

    async def _handle_non_compliance(self, compliance_plan: Dict[str, Any]) -> None:
        """Handle non-compliance with a captain directive.
        
        Args:
            compliance_plan: Current compliance plan
        """
        try:
            # Create escalation notice
            pending_actions = [
                action for action, status in compliance_plan["actions_status"].items()
                if not status
            ]
            
            # Get backup agent
            backup_agent = self._get_backup_agent()
            
            # Check if this is a second failure (backup agent already failed)
            is_second_failure = compliance_plan.get("backup_agent_failed", False)
            
            if is_second_failure:
                # Escalate to THEA
                await self._escalate_to_thea(compliance_plan, pending_actions)
            else:
                # Try backup agent first
                if backup_agent:
                    # Update compliance plan with backup info
                    compliance_plan.update({
                        "backup_agent": backup_agent,
                        "backup_assigned_at": datetime.utcnow().isoformat()
                    })
                    
                    # Create handoff message
                    handoff = Message.create_captain_directive(
                        from_agent=self.agent.agent_id,
                        to_agent=backup_agent,
                        directive=f"BACKUP ASSIGNMENT - Directive {compliance_plan['directive_id']}",
                        urgency="HIGH",
                        required_actions=pending_actions,
                        deadline=compliance_plan.get("deadline")
                    )
                    
                    # Send handoff
                    self.message_handler.send_message(handoff)
                    
                    # Log handoff
                    await self._log_to_devlog(
                        f"Handed off directive {compliance_plan['directive_id']} to backup agent {backup_agent}",
                        {
                            "compliance_plan": compliance_plan,
                            "handoff": handoff.to_dict()
                        }
                    )
                else:
                    # No backup available, escalate to THEA
                    await self._escalate_to_thea(compliance_plan, pending_actions)
            
            # Create escalation notice
            escalation = Message.create_escalation_notice(
                from_agent=self.agent.agent_id,
                to_agent="Agent-7",  # Captain
                directive_id=compliance_plan["directive_id"],
                reason="Deadline exceeded or incomplete actions",
                actions_pending=pending_actions,
                backup_agent=backup_agent
            )
            
            # Send escalation
            self.message_handler.send_message(escalation)
            
            # Log escalation
            await self._log_to_devlog(
                f"Escalated directive {compliance_plan['directive_id']}",
                {
                    "compliance_plan": compliance_plan,
                    "escalation": escalation.to_dict()
                }
            )
            
            # Send alert
            await self.alert_manager.send_alert(
                alert_type="DIRECTIVE_NON_COMPLIANCE",
                message=f"Agent {self.agent.agent_id} failed to comply with directive {compliance_plan['directive_id']}",
                severity="error",
                details={
                    "compliance_plan": compliance_plan,
                    "pending_actions": pending_actions,
                    "backup_agent": backup_agent,
                    "is_second_failure": is_second_failure
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error handling non-compliance: {e}", exc_info=True)

    async def _escalate_to_thea(self, compliance_plan: Dict[str, Any], pending_actions: List[str]) -> None:
        """Escalate directive to THEA for swarm-wide recovery.
        
        Args:
            compliance_plan: Current compliance plan
            pending_actions: List of pending actions
        """
        try:
            # Create THEA escalation message
            thea_escalation = {
                "type": "thea_escalation",
                "directive_id": compliance_plan["directive_id"],
                "original_agent": self.agent.agent_id,
                "backup_agent": compliance_plan.get("backup_agent"),
                "pending_actions": pending_actions,
                "compliance_plan": compliance_plan,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to THEA via agent bus
            if self.agent_bus:
                await self.agent_bus.publish(
                    "thea.directive.escalation",
                    thea_escalation
                )
            
            # Log THEA escalation
            await self._log_to_devlog(
                f"Escalated directive {compliance_plan['directive_id']} to THEA",
                thea_escalation
            )
            
            # Send alert
            await self.alert_manager.send_alert(
                alert_type="THEA_ESCALATION",
                message=f"Directive {compliance_plan['directive_id']} escalated to THEA",
                severity="critical",
                details=thea_escalation
            )
            
            # Update compliance plan
            compliance_plan.update({
                "thea_escalated": True,
                "thea_escalation_time": datetime.utcnow().isoformat(),
                "status": "thea_handling"
            })
            
            # Save updated compliance plan
            compliance_path = Path(f"runtime/compliance/{self.agent.agent_id}/{compliance_plan['directive_id']}.json")
            with open(compliance_path, 'w') as f:
                json.dump(compliance_plan, f, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error escalating to THEA: {e}", exc_info=True)

    async def _handle_thea_recovery(self, recovery_plan: Dict[str, Any]) -> None:
        """Handle recovery plan from THEA.
        
        Args:
            recovery_plan: THEA's recovery plan
        """
        try:
            directive_id = recovery_plan["directive_id"]
            compliance_path = Path(f"runtime/compliance/{self.agent.agent_id}/{directive_id}.json")
            
            if not compliance_path.exists():
                self.logger.error(f"No compliance plan found for directive {directive_id}")
                return
            
            # Read current compliance plan
            with open(compliance_path) as f:
                compliance_plan = json.load(f)
            
            # Create recovery snapshot before starting
            await self._create_recovery_snapshot(compliance_plan)
            
            # Update with THEA's recovery plan
            compliance_plan.update({
                "thea_recovery": recovery_plan,
                "recovery_started_at": datetime.utcnow().isoformat(),
                "status": "recovering",
                "recovery_metrics": {
                    "start_time": datetime.utcnow().isoformat(),
                    "actions_completed": 0,
                    "total_actions": len(recovery_plan.get("recovery_actions", [])),
                    "task_preservation_rate": 0.0,
                    "recovery_success": False
                }
            })
            
            # Execute recovery actions
            for action in recovery_plan.get("recovery_actions", []):
                try:
                    action_start = time.time()
                    
                    # Execute recovery action
                    await self._execute_recovery_action(action)
                    
                    # Calculate action metrics
                    action_duration = time.time() - action_start
                    
                    # Update compliance plan
                    compliance_plan["recovery_progress"].append({
                        "action": action,
                        "status": "completed",
                        "completed_at": datetime.utcnow().isoformat(),
                        "duration_seconds": action_duration
                    })
                    
                    # Update metrics
                    compliance_plan["recovery_metrics"]["actions_completed"] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error executing recovery action: {e}")
                    compliance_plan["recovery_progress"].append({
                        "action": action,
                        "status": "failed",
                        "error": str(e),
                        "failed_at": datetime.utcnow().isoformat()
                    })
                    
                    # Attempt rollback on failure
                    await self._rollback_recovery(compliance_plan)
                    return
            
            # Calculate final metrics
            end_time = datetime.utcnow()
            start_time = datetime.fromisoformat(compliance_plan["recovery_metrics"]["start_time"])
            total_duration = (end_time - start_time).total_seconds()
            
            # Calculate task preservation rate
            original_tasks = len(compliance_plan.get("original_state", {}).get("active_tasks", []))
            current_tasks = len(self.agent._active_tasks)
            task_preservation = (current_tasks / original_tasks * 100) if original_tasks > 0 else 100
            
            # Update final metrics
            compliance_plan["recovery_metrics"].update({
                "end_time": end_time.isoformat(),
                "total_duration_seconds": total_duration,
                "task_preservation_rate": task_preservation,
                "recovery_success": True
            })
            
            # Save updated compliance plan
            with open(compliance_path, 'w') as f:
                json.dump(compliance_plan, f, indent=2)
            
            # Log recovery progress
            await self._log_to_devlog(
                f"Executed THEA recovery plan for directive {directive_id}",
                compliance_plan
            )
            
            # Call agent's recovery hook
            if hasattr(self.agent, 'on_recovery'):
                try:
                    await self.agent.on_recovery(compliance_plan)
                except Exception as e:
                    self.logger.error(f"Error in agent recovery hook: {e}")
            
            # Start recovery monitoring
            asyncio.create_task(self._monitor_recovery_success(compliance_plan))
            
        except Exception as e:
            self.logger.error(f"Error handling THEA recovery: {e}", exc_info=True)
            # Attempt rollback on critical failure
            await self._rollback_recovery(compliance_plan)

    async def _create_recovery_snapshot(self, compliance_plan: Dict[str, Any]) -> None:
        """Create a snapshot of current state for potential rollback.
        
        Args:
            compliance_plan: Current compliance plan
        """
        try:
            snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                "agent_state": {
                    "active_tasks": self.agent._active_tasks.copy(),
                    "status": self.agent.status if hasattr(self.agent, 'status') else None,
                    "metrics": self.agent.episode_metrics.copy() if hasattr(self.agent, 'episode_metrics') else {}
                },
                "compliance_state": compliance_plan.copy()
            }
            
            # Store snapshot
            snapshot_path = Path(f"runtime/recovery_snapshots/{self.agent.agent_id}/{compliance_plan['directive_id']}.json")
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(snapshot_path, 'w') as f:
                json.dump(snapshot, f, indent=2)
                
            # Update compliance plan
            compliance_plan["original_state"] = snapshot["agent_state"]
            
        except Exception as e:
            self.logger.error(f"Error creating recovery snapshot: {e}", exc_info=True)

    async def _rollback_recovery(self, compliance_plan: Dict[str, Any]) -> None:
        """Rollback to last known good state.
        
        Args:
            compliance_plan: Current compliance plan
        """
        try:
            snapshot_path = Path(f"runtime/recovery_snapshots/{self.agent.agent_id}/{compliance_plan['directive_id']}.json")
            
            if not snapshot_path.exists():
                self.logger.error("No recovery snapshot found for rollback")
                return
                
            # Read snapshot
            with open(snapshot_path) as f:
                snapshot = json.load(f)
            
            # Restore agent state
            self.agent._active_tasks = snapshot["agent_state"]["active_tasks"]
            if hasattr(self.agent, 'status'):
                self.agent.status = snapshot["agent_state"]["status"]
            if hasattr(self.agent, 'episode_metrics'):
                self.agent.episode_metrics = snapshot["agent_state"]["metrics"]
            
            # Update compliance plan
            compliance_plan.update({
                "status": "rolled_back",
                "rollback_time": datetime.utcnow().isoformat(),
                "rollback_reason": "Recovery failure",
                "original_state": snapshot["agent_state"]
            })
            
            # Save updated compliance plan
            compliance_path = Path(f"runtime/compliance/{self.agent.agent_id}/{compliance_plan['directive_id']}.json")
            with open(compliance_path, 'w') as f:
                json.dump(compliance_plan, f, indent=2)
            
            # Log rollback
            await self._log_to_devlog(
                f"Rolled back recovery for directive {compliance_plan['directive_id']}",
                compliance_plan
            )
            
            # Send rollback alert
            await self.alert_manager.send_alert(
                alert_type="RECOVERY_ROLLBACK",
                message=f"Recovery rolled back for directive {compliance_plan['directive_id']}",
                severity="warning",
                details=compliance_plan
            )
            
        except Exception as e:
            self.logger.error(f"Error during recovery rollback: {e}", exc_info=True)

    async def _monitor_recovery_success(self, compliance_plan: Dict[str, Any]) -> None:
        """Monitor agent success for 3 cycles after recovery.
        
        Args:
            compliance_plan: Current compliance plan
        """
        try:
            cycles_to_monitor = 3
            cycle_results = []
            
            for cycle in range(cycles_to_monitor):
                # Wait for next cycle
                await asyncio.sleep(self.config.agent.cycle_interval)
                
                # Check agent status
                status = self.metrics._read_status()
                agent_status = status["agents"].get(self.agent.agent_id, {})
                
                cycle_result = {
                    "cycle": cycle + 1,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": agent_status.get("status"),
                    "active_tasks": len(self.agent._active_tasks),
                    "errors": agent_status.get("errors_this_cycle", 0)
                }
                
                cycle_results.append(cycle_result)
            
            # Update compliance plan with monitoring results
            compliance_plan["recovery_metrics"]["post_recovery_monitoring"] = cycle_results
            
            # Calculate success rate
            successful_cycles = sum(1 for r in cycle_results if r["errors"] == 0)
            success_rate = (successful_cycles / cycles_to_monitor) * 100
            
            compliance_plan["recovery_metrics"]["post_recovery_success_rate"] = success_rate
            
            # Save updated compliance plan
            compliance_path = Path(f"runtime/compliance/{self.agent.agent_id}/{compliance_plan['directive_id']}.json")
            with open(compliance_path, 'w') as f:
                json.dump(compliance_plan, f, indent=2)
            
            # Log monitoring results
            await self._log_to_devlog(
                f"Recovery monitoring completed for directive {compliance_plan['directive_id']}",
                {
                    "compliance_plan": compliance_plan,
                    "monitoring_results": cycle_results,
                    "success_rate": success_rate
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error monitoring recovery success: {e}", exc_info=True)

    async def _execute_recovery_action(self, action: Dict[str, Any]) -> None:
        """Execute a recovery action from THEA.
        
        Args:
            action: Recovery action to execute
        """
        try:
            action_type = action.get("type")
            
            if action_type == "reset_agent":
                # Reset agent state
                self.agent._active_tasks.clear()
                await self._attempt_recovery()
                
            elif action_type == "redelegate":
                # Redelegate tasks to new agent
                new_agent = action.get("new_agent")
                if new_agent:
                    # Create redelegation message
                    redelegation = Message.create_captain_directive(
                        from_agent=self.agent.agent_id,
                        to_agent=new_agent,
                        directive=f"REDELEGATION - Directive {action['directive_id']}",
                        urgency="HIGH",
                        required_actions=action.get("actions", []),
                        deadline=action.get("deadline")
                    )
                    self.message_handler.send_message(redelegation)
                    
            elif action_type == "swarm_reset":
                # Trigger swarm-wide reset
                if self.agent_bus:
                    await self.agent_bus.publish(
                        "thea.swarm.reset",
                        {
                            "triggered_by": self.agent.agent_id,
                            "reason": action.get("reason", "THEA recovery"),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
            
        except Exception as e:
            self.logger.error(f"Error executing recovery action: {e}", exc_info=True)
            raise

    def _get_backup_agent(self) -> Optional[str]:
        """Get a backup agent for task reassignment.
        
        Returns:
            Optional[str]: ID of backup agent, or None if none available
        """
        try:
            # Read agent status to find available agents
            status_path = Path("runtime/agent_status")
            if not status_path.exists():
                return None
                
            available_agents = []
            for agent_file in status_path.glob("*.json"):
                with open(agent_file) as f:
                    agent_status = json.load(f)
                    if agent_status["status"] == "active":
                        available_agents.append(agent_status["agent_id"])
            
            # Remove current agent from available list
            if self.agent.agent_id in available_agents:
                available_agents.remove(self.agent.agent_id)
                
            # Return first available agent, or None
            return available_agents[0] if available_agents else None
            
        except Exception as e:
            self.logger.error(f"Error getting backup agent: {e}")
            return None

    # ... rest of the existing methods ... 