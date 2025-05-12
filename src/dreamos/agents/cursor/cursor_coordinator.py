"""Coordinator for managing cursor agent states and response routing."""

import asyncio
import json
import logging
import re
import pyperclip
import pyautogui
from pathlib import Path
from typing import Dict, Optional, Set

from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.core.coordination.message_patterns import TaskMessage
from ..utils.cursor_monitor_utils import CursorStateMonitor
from ...utils.common_utils import get_utc_iso_timestamp

logger = logging.getLogger(__name__)

class CursorCoordinator:
    """Coordinates cursor agent states and manages response routing."""
    
    def __init__(
        self,
        bus: AgentBus,
        gui_images_dir: Path,
        coords_file: Path,
        thea_mailbox_dir: Path,
        check_interval: float = 1.0,
        hash_threshold: int = 5,
        response_timeout: float = 30.0,
        image_size: tuple = (50, 50)
    ):
        """Initialize the cursor coordinator.
        
        Args:
            bus: AgentBus instance for communication
            gui_images_dir: Directory containing cursor GUI images
            coords_file: Path to JSON file containing agent coordinates
            thea_mailbox_dir: Directory for THEA's mailbox
            check_interval: How often to check image states (seconds)
            hash_threshold: Threshold for image similarity comparison
            response_timeout: Timeout for waiting for responses (seconds)
            image_size: Size of the region to capture for state detection
        """
        self.bus = bus
        self.thea_mailbox_dir = thea_mailbox_dir
        self.monitor = CursorStateMonitor(
            bus=bus,
            gui_images_dir=gui_images_dir,
            coords_file=coords_file,
            check_interval=check_interval,
            hash_threshold=hash_threshold,
            image_size=image_size
        )
        self.response_timeout = response_timeout
        
        # Track agent tasks and responses
        self.agent_tasks: Dict[str, TaskMessage] = {}
        self.agent_responses: Dict[str, str] = {}
        self.response_futures: Dict[str, asyncio.Future] = {}
        
        # Subscribe to state changes and stuck alerts
        self.bus.subscribe("system.cursor.*.state", self._handle_state_change)
        self.bus.subscribe("system.cursor.*.stuck", self._handle_stuck_alert)
        
        # Ensure THEA's mailbox exists
        self.thea_mailbox_dir.mkdir(parents=True, exist_ok=True)
        self.thea_inbox = self.thea_mailbox_dir / "inbox.json"
        if not self.thea_inbox.exists():
            self.thea_inbox.write_text("[]")
            
    async def start(self) -> None:
        """Start the coordinator."""
        logger.info("Starting cursor coordinator")
        
    async def stop(self) -> None:
        """Stop the coordinator."""
        logger.info("Stopping cursor coordinator")
        # Stop monitoring all agents
        for agent_id in list(self.monitor.monitoring_tasks.keys()):
            await self.monitor.stop_monitoring(agent_id)
            
    async def register_agent(
        self,
        agent_id: str,
        coords: Dict[str, Dict[str, int]],
        task: TaskMessage
    ) -> None:
        """Register a cursor agent for monitoring.
        
        Args:
            agent_id: ID of the agent to register
            coords: Dictionary containing input_box and copy_button coordinates
            task: The task being performed by the agent
        """
        self.agent_tasks[agent_id] = task
        self.response_futures[agent_id] = asyncio.Future()
        await self.monitor.start_monitoring(agent_id, coords)
        logger.info(f"Registered cursor agent {agent_id} for task {task.task_id}")
        
    async def wait_for_response(self, agent_id: str) -> Optional[str]:
        """Wait for a response from a cursor agent.
        
        Args:
            agent_id: ID of the agent to wait for
            
        Returns:
            Optional[str]: The agent's response if received within timeout
        """
        if agent_id not in self.response_futures:
            logger.warning(f"No response future for agent {agent_id}")
            return None
            
        try:
            response = await asyncio.wait_for(
                self.response_futures[agent_id],
                timeout=self.response_timeout
            )
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for response from agent {agent_id}")
            return None
        finally:
            # Clean up
            if agent_id in self.response_futures:
                del self.response_futures[agent_id]
            if agent_id in self.agent_tasks:
                del self.agent_tasks[agent_id]
            if agent_id in self.agent_responses:
                del self.agent_responses[agent_id]
                
    async def _handle_state_change(self, message: Dict) -> None:
        """Handle cursor state change messages.
        
        Args:
            message: The state change message
        """
        try:
            data = message.get("data", {})
            agent_id = data.get("agent_id")
            is_complete = data.get("is_complete", False)
            
            if not agent_id or agent_id not in self.agent_tasks:
                return
                
            if is_complete:
                # Agent is complete, copy response
                await self._copy_agent_response(agent_id)
                
                # Check if we have a response
                if agent_id in self.agent_responses:
                    response = self.agent_responses[agent_id]
                    if agent_id in self.response_futures:
                        self.response_futures[agent_id].set_result(response)
                        
                # Determine if we should send to ChatGPT
                task = self.agent_tasks.get(agent_id)
                if task and self._should_send_to_chatgpt(task):
                    await self._send_to_chatgpt(agent_id, task)
                    
        except Exception as e:
            logger.error(f"Error handling state change: {e}", exc_info=True)
            
    async def _copy_agent_response(self, agent_id: str) -> None:
        """Copy response from an agent's input box.
        
        Args:
            agent_id: ID of the agent to copy from
        """
        try:
            coords = self.monitor.agent_coords.get(agent_id)
            if not coords:
                logger.warning(f"No coordinates found for agent {agent_id}")
                return
                
            # Click copy button
            copy_btn = coords.get("copy_button", {})
            if copy_btn:
                # Store initial clipboard state
                initial_clipboard = pyperclip.paste()
                
                # Click copy button
                pyautogui.click(copy_btn["x"], copy_btn["y"])
                await asyncio.sleep(0.1)  # Wait for copy to complete
                
                # Get new clipboard content
                new_clipboard = pyperclip.paste()
                
                # Verify if something was actually copied
                if new_clipboard and new_clipboard != initial_clipboard:
                    self.agent_responses[agent_id] = new_clipboard
                    logger.debug(f"Copied response from agent {agent_id}")
                    
                    # If clipboard is empty or unchanged, agent might not be done
                    if not new_clipboard:
                        logger.warning(
                            f"Empty clipboard after copy for agent {agent_id} - "
                            "agent may not be complete"
                        )
                        # Reset agent state to generating
                        if agent_id in self.monitor.agent_states:
                            self.monitor.agent_states[agent_id] = False
                            await self.monitor._publish_state_change(agent_id, False)
                else:
                    logger.warning(
                        f"No response copied from agent {agent_id} - "
                        "clipboard unchanged"
                    )
                    # Reset agent state to generating
                    if agent_id in self.monitor.agent_states:
                        self.monitor.agent_states[agent_id] = False
                        await self.monitor._publish_state_change(agent_id, False)
                    
        except Exception as e:
            logger.error(f"Failed to copy response from agent {agent_id}: {e}", exc_info=True)
            # Reset agent state to generating on error
            if agent_id in self.monitor.agent_states:
                self.monitor.agent_states[agent_id] = False
                await self.monitor._publish_state_change(agent_id, False)
            
    async def _handle_stuck_alert(self, message: Dict) -> None:
        """Handle stuck agent alerts.
        
        Args:
            message: The stuck alert message
        """
        try:
            data = message.get("data", {})
            agent_id = data.get("agent_id")
            stuck_message = data.get("message")
            
            if not agent_id or agent_id not in self.agent_tasks:
                return
                
            # Send stuck alert to THEA
            await self._send_to_chatgpt(
                agent_id,
                self.agent_tasks[agent_id],
                is_stuck=True,
                stuck_message=stuck_message
            )
            
        except Exception as e:
            logger.error(f"Error handling stuck alert: {e}", exc_info=True)
            
    def _should_send_to_chatgpt(self, task: TaskMessage) -> bool:
        """Determine if a task's response should be sent to ChatGPT.
        
        Args:
            task: The task to check
            
        Returns:
            bool: True if response should be sent to ChatGPT
        """
        # Check task metadata
        if task.metadata.get("requires_thea", False):
            return True
            
        # Check response content
        response = self.agent_responses.get(task.task_id)
        if response:
            # Look for THEA escalation patterns
            thea_patterns = [
                r"THEA:",
                r"escalate to THEA",
                r"need THEA's help",
                r"requires THEA",
                r"THEA assistance"
            ]
            return any(re.search(pattern, response, re.IGNORECASE) for pattern in thea_patterns)
            
        return False
        
    async def _send_to_chatgpt(
        self,
        agent_id: str,
        task: TaskMessage,
        is_stuck: bool = False,
        stuck_message: Optional[str] = None
    ) -> None:
        """Send a response to ChatGPT.
        
        Args:
            agent_id: ID of the agent that generated the response
            task: The task that was performed
            is_stuck: Whether this is a stuck agent alert
            stuck_message: Message about why the agent is stuck
        """
        response = self.agent_responses.get(agent_id)
        if not response and not is_stuck:
            logger.warning(f"No response to send to ChatGPT for agent {agent_id}")
            return
            
        try:
            # Load existing messages
            messages = []
            if self.thea_inbox.exists():
                messages = json.loads(self.thea_inbox.read_text())
                
            # Create new message
            message = {
                "from": agent_id,
                "task_id": task.task_id,
                "timestamp": get_utc_iso_timestamp(),
                "type": "stuck_alert" if is_stuck else "escalation",
                "content": {
                    "task": task.model_dump(),
                    "response": response if not is_stuck else None,
                    "stuck_message": stuck_message if is_stuck else None
                }
            }
            
            # Add to messages and save
            messages.append(message)
            self.thea_inbox.write_text(json.dumps(messages, indent=2))
            
            logger.info(
                f"Sent {'stuck alert' if is_stuck else 'response'} to THEA "
                f"from agent {agent_id}"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to send {'stuck alert' if is_stuck else 'response'} "
                f"to THEA for agent {agent_id}: {e}",
                exc_info=True
            ) 