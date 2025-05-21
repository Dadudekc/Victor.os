"""
Agent Checkpoint Manager

This module implements the CheckpointManager class for creating, managing, and restoring
agent state checkpoints, as specified in docs/vision/CHECKPOINT_PROTOCOL.md.

This is a critical component for addressing agent drift in long-running sessions.
"""

import json
import time
import os
import logging
import shutil
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dreamos.core.checkpoint_manager")

class CheckpointManager:
    """
    Manager for agent state checkpoints to prevent drift in long-running sessions.
    
    Usage:
        checkpoint_manager = CheckpointManager(agent_id)
        
        # Create a checkpoint
        checkpoint_path = checkpoint_manager.create_checkpoint("routine")
        
        # Restore from checkpoint
        checkpoint_manager.restore_checkpoint(checkpoint_path)
        
        # Get latest checkpoint
        latest = checkpoint_manager.get_latest_checkpoint("routine")
    """
    
    def __init__(self, agent_id: str):
        """
        Initialize the checkpoint manager for a specific agent.
        
        Args:
            agent_id: Identifier of the agent
        """
        self.agent_id = agent_id
        self.checkpoint_dir = "runtime/agent_comms/checkpoints"
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        logger.info(f"Initialized CheckpointManager for {agent_id}")
    
    def create_checkpoint(self, checkpoint_type: str = "routine") -> str:
        """
        Create a checkpoint of the agent's current state.
        
        Args:
            checkpoint_type: Type of checkpoint ("routine", "pre_operation", "recovery")
            
        Returns:
            Path to the created checkpoint file
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        filename = f"{self.agent_id}_{timestamp}_{checkpoint_type}.checkpoint"
        path = os.path.join(self.checkpoint_dir, filename)
        
        # Collect agent state
        state = {
            "current_task": self._get_current_task_state(),
            "mailbox": self._get_mailbox_state(),
            "operational_context": self._get_operational_context(),
            "memory": self._get_memory_state()
        }
        
        # Create checkpoint file
        checkpoint_data = {
            "agent_id": self.agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checkpoint_type": checkpoint_type,
            "version": "1.0",
            "state": state
        }
        
        with open(path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        logger.info(f"Created {checkpoint_type} checkpoint at {path}")
        
        # Manage retention policy
        self._apply_retention_policy(checkpoint_type)
            
        return path
        
    def restore_checkpoint(self, checkpoint_path: str) -> bool:
        """
        Restore agent state from a checkpoint.
        
        Args:
            checkpoint_path: Path to the checkpoint file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(checkpoint_path, 'r') as f:
                checkpoint_data = json.load(f)
                
            # Validate checkpoint belongs to this agent
            if checkpoint_data["agent_id"] != self.agent_id:
                raise ValueError(f"Checkpoint belongs to {checkpoint_data['agent_id']}, not {self.agent_id}")
                
            # Apply state restoration
            self._restore_task_state(checkpoint_data["state"]["current_task"])
            self._restore_mailbox_state(checkpoint_data["state"]["mailbox"])
            self._restore_operational_context(checkpoint_data["state"]["operational_context"])
            self._restore_memory_state(checkpoint_data["state"]["memory"])
            
            logger.info(f"Successfully restored checkpoint from {checkpoint_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore checkpoint: {str(e)}")
            return False
    
    def get_latest_checkpoint(self, checkpoint_type: str = "routine") -> Optional[str]:
        """
        Get the latest checkpoint of the specified type.
        
        Args:
            checkpoint_type: Type of checkpoint ("routine", "pre_operation", "recovery")
            
        Returns:
            Path to the latest checkpoint or None if not found
        """
        checkpoints = self._list_checkpoints(checkpoint_type)
        if not checkpoints:
            logger.warning(f"No {checkpoint_type} checkpoints found for {self.agent_id}")
            return None
        
        # Sort by timestamp (which is part of the filename)
        sorted_checkpoints = sorted(checkpoints)
        latest = sorted_checkpoints[-1]
        logger.info(f"Found latest {checkpoint_type} checkpoint: {latest}")
        return latest
    
    def _get_current_task_state(self) -> Dict[str, Any]:
        """Collect current task state - implement according to agent type."""
        try:
            # Try to get current task from working_tasks.json
            tasks_path = "runtime/working_tasks.json"
            if os.path.exists(tasks_path):
                with open(tasks_path, 'r') as f:
                    tasks = json.load(f)
                    
                # Find task assigned to this agent
                for task in tasks:
                    if task.get("assigned_agent") == self.agent_id:
                        return {
                            "id": task.get("task_id", ""),
                            "status": task.get("status", "unknown"),
                            "progress_percentage": 0,  # Default to 0 as we don't track this yet
                            "context": task
                        }
        except Exception as e:
            logger.error(f"Error getting task state: {str(e)}")
            
        return {
            "id": "",
            "status": "unknown",
            "progress_percentage": 0,
            "context": {}
        }
        
    def _get_mailbox_state(self) -> Dict[str, Any]:
        """Collect mailbox state - implement according to agent type."""
        try:
            # Check agent mailbox
            inbox_path = f"runtime/agent_comms/agent_mailboxes/{self.agent_id}/inbox"
            processed_path = f"runtime/agent_comms/agent_mailboxes/{self.agent_id}/inbox/processed"
            
            if not os.path.exists(inbox_path):
                return {"last_processed_id": "", "pending_count": 0}
                
            # Count pending messages (excluding .keep and processed directory)
            pending_messages = [f for f in os.listdir(inbox_path) 
                              if os.path.isfile(os.path.join(inbox_path, f)) 
                              and f != ".keep"]
            pending_count = len(pending_messages)
            
            # Get last processed message if any
            last_processed_id = ""
            if os.path.exists(processed_path):
                processed_files = [f for f in os.listdir(processed_path) 
                                if os.path.isfile(os.path.join(processed_path, f))
                                and f != ".keep"]
                if processed_files:
                    last_processed_id = sorted(processed_files)[-1]
            
            return {
                "last_processed_id": last_processed_id,
                "pending_count": pending_count
            }
        except Exception as e:
            logger.error(f"Error getting mailbox state: {str(e)}")
            return {"last_processed_id": "", "pending_count": 0}
        
    def _get_operational_context(self) -> Dict[str, Any]:
        """Collect operational context - implement according to agent type."""
        context = {
            "goals": [],
            "constraints": [],
            "decisions": []
        }
        
        try:
            # Check if there's a context file for this agent
            context_path = f"runtime/agent_data/{self.agent_id}/context.json"
            if os.path.exists(context_path):
                with open(context_path, 'r') as f:
                    agent_context = json.load(f)
                    context.update(agent_context)
        except Exception as e:
            logger.error(f"Error getting operational context: {str(e)}")
            
        return context
        
    def _get_memory_state(self) -> Dict[str, Any]:
        """Collect memory state - implement according to agent type."""
        memory = {
            "short_term": [],
            "session": []
        }
        
        try:
            # Check if there's a memory file for this agent
            memory_path = f"runtime/agent_data/{self.agent_id}/memory.json"
            if os.path.exists(memory_path):
                with open(memory_path, 'r') as f:
                    agent_memory = json.load(f)
                    memory.update(agent_memory)
        except Exception as e:
            logger.error(f"Error getting memory state: {str(e)}")
            
        return memory
        
    def _restore_task_state(self, task_state: Dict[str, Any]) -> None:
        """Restore task state - implement according to agent type."""
        try:
            if not task_state.get("id"):
                logger.warning("No task to restore")
                return
                
            # Update working_tasks.json if task exists
            tasks_path = "runtime/working_tasks.json"
            if os.path.exists(tasks_path):
                with open(tasks_path, 'r') as f:
                    tasks = json.load(f)
                
                task_id = task_state.get("id")
                context = task_state.get("context", {})
                
                # Update the task if it exists
                for i, task in enumerate(tasks):
                    if task.get("task_id") == task_id:
                        # Only update status if it comes from context
                        if "status" in context:
                            tasks[i]["status"] = context["status"]
                        logger.info(f"Restored task state for {task_id}")
                        
                        with open(tasks_path, 'w') as f:
                            json.dump(tasks, f, indent=2)
                        return
                
                logger.warning(f"Task {task_id} not found in working tasks")
        except Exception as e:
            logger.error(f"Error restoring task state: {str(e)}")
        
    def _restore_mailbox_state(self, mailbox_state: Dict[str, Any]) -> None:
        """Restore mailbox state - implement according to agent type."""
        # Mailbox state is primarily for tracking purposes, no restoration needed
        logger.info(f"Mailbox state restored: {mailbox_state.get('pending_count', 0)} pending messages")
        
    def _restore_operational_context(self, operational_context: Dict[str, Any]) -> None:
        """Restore operational context - implement according to agent type."""
        try:
            # Ensure agent data directory exists
            agent_data_dir = f"runtime/agent_data/{self.agent_id}"
            os.makedirs(agent_data_dir, exist_ok=True)
            
            # Write context to file
            context_path = f"{agent_data_dir}/context.json"
            with open(context_path, 'w') as f:
                json.dump(operational_context, f, indent=2)
                
            logger.info(f"Restored operational context to {context_path}")
        except Exception as e:
            logger.error(f"Error restoring operational context: {str(e)}")
        
    def _restore_memory_state(self, memory_state: Dict[str, Any]) -> None:
        """Restore memory state - implement according to agent type."""
        try:
            # Ensure agent data directory exists
            agent_data_dir = f"runtime/agent_data/{self.agent_id}"
            os.makedirs(agent_data_dir, exist_ok=True)
            
            # Write memory to file
            memory_path = f"{agent_data_dir}/memory.json"
            with open(memory_path, 'w') as f:
                json.dump(memory_state, f, indent=2)
                
            logger.info(f"Restored memory state to {memory_path}")
        except Exception as e:
            logger.error(f"Error restoring memory state: {str(e)}")
        
    def _list_checkpoints(self, checkpoint_type: Optional[str] = None) -> List[str]:
        """
        List available checkpoints, optionally filtered by type.
        
        Args:
            checkpoint_type: Type of checkpoint to filter by
            
        Returns:
            List of checkpoint file paths
        """
        checkpoints = []
        try:
            for filename in os.listdir(self.checkpoint_dir):
                if filename.startswith(self.agent_id) and filename.endswith(".checkpoint"):
                    if checkpoint_type is None or f"_{checkpoint_type}." in filename:
                        checkpoints.append(os.path.join(self.checkpoint_dir, filename))
        except Exception as e:
            logger.error(f"Error listing checkpoints: {str(e)}")
            
        return checkpoints
    
    def _apply_retention_policy(self, checkpoint_type: str) -> None:
        """
        Apply retention policy for checkpoints.
        
        Args:
            checkpoint_type: Type of checkpoint
        """
        try:
            # Retention policies based on checkpoint type
            if checkpoint_type == "routine":
                # Keep only the last 3 routine checkpoints
                routine_checkpoints = self._list_checkpoints("routine")
                if len(routine_checkpoints) > 3:
                    # Sort by creation time (oldest first)
                    sorted_checkpoints = sorted(routine_checkpoints)
                    # Remove oldest checkpoints (everything except the 3 newest)
                    for checkpoint in sorted_checkpoints[:-3]:
                        if os.path.exists(checkpoint):
                            os.remove(checkpoint)
                            logger.info(f"Removed old routine checkpoint: {checkpoint}")
            
            # For recovery checkpoints, we keep them for 7 days
            # This would require a date-based cleanup which we'll implement in a future update
        except Exception as e:
            logger.error(f"Error applying retention policy: {str(e)}")
    
    def detect_drift(self) -> bool:
        """
        Detect potential agent drift based on operational metrics.
        
        Returns:
            True if drift is detected, False otherwise
        """
        # Basic drift detection based on session time
        # This is a placeholder for more sophisticated drift detection
        try:
            # Check if agent status file exists
            status_path = "runtime/agent_status.json"
            if os.path.exists(status_path):
                with open(status_path, 'r') as f:
                    status_data = json.load(f)
                
                if self.agent_id in status_data.get("agents", {}):
                    agent_status = status_data["agents"][self.agent_id]
                    
                    # Check if cycle count exceeds drift threshold
                    cycle_count = agent_status.get("cycle_count", 0)
                    drift_threshold = status_data.get("system", {}).get("drift_threshold", 300)
                    
                    if cycle_count > drift_threshold:
                        logger.warning(f"Potential drift detected: cycle count {cycle_count} exceeds threshold {drift_threshold}")
                        return True
        except Exception as e:
            logger.error(f"Error detecting drift: {str(e)}")
            
        return False

def integrate_with_agent_loop():
    """
    Example code for integrating CheckpointManager with an agent's operational loop.
    """
    # Initialize checkpoint manager
    agent_id = "agent-3"  # Replace with actual agent ID
    checkpoint_manager = CheckpointManager(agent_id)
    
    # Track operation time
    session_start_time = time.time()
    last_checkpoint_time = session_start_time
    
    # Main loop
    while True:  # Replace with actual loop condition
        try:
            # Normal agent operations
            # process_mailbox()
            # check_tasks()
            # execute_current_task()
            
            # Regular checkpoint creation
            current_time = time.time()
            if current_time - last_checkpoint_time >= 1800:  # 30 minutes
                checkpoint_manager.create_checkpoint("routine")
                last_checkpoint_time = current_time
                
            # Force state refresh after 2 hours
            if current_time - session_start_time >= 7200:  # 2 hours
                recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
                # Perform controlled restart with state from checkpoint
                # restart_with_checkpoint(recovery_checkpoint)
                session_start_time = current_time
                
        except Exception as e:
            # Create recovery checkpoint on error
            recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
            logger.error(f"Error during operation: {str(e)}")
            logger.info(f"Recovery point created: {recovery_checkpoint}")
            # Continue loop or initiate recovery process

if __name__ == "__main__":
    # Example usage
    manager = CheckpointManager("test-agent")
    checkpoint = manager.create_checkpoint("routine")
    print(f"Created checkpoint: {checkpoint}")
    
    # Example integration
    # integrate_with_agent_loop() 