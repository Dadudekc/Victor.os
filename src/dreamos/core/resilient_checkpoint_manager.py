"""
Resilient Checkpoint Manager

This module enhances the CheckpointManager with resilient IO operations to prevent
checkpoint failures and data corruption. It wraps the standard CheckpointManager
with retry logic and fallback mechanisms from resilient_io.

This integration is critical for ensuring reliable agent state management.
"""

import os
import json
import logging
import time
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

# Import the resilient IO utilities
from dreamos.utils.resilient_io import (
    read_file, write_file, read_json, write_json, list_dir
)

# Import the checkpoint manager
from dreamos.core.checkpoint_manager import CheckpointManager

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dreamos.core.resilient_checkpoint_manager")

class ResilientCheckpointManager:
    """
    Enhanced CheckpointManager with resilient IO operations.
    
    This class wraps the standard CheckpointManager with retry logic and
    fallback mechanisms from resilient_io to ensure reliable checkpoint operations
    even in the face of transient file system errors.
    
    Usage:
        resilient_manager = ResilientCheckpointManager(agent_id)
        
        # Create a checkpoint
        checkpoint_path = resilient_manager.create_checkpoint("routine")
        
        # Restore from checkpoint
        resilient_manager.restore_checkpoint(checkpoint_path)
        
        # Get latest checkpoint
        latest = resilient_manager.get_latest_checkpoint("routine")
    """
    
    def __init__(self, agent_id: str):
        """
        Initialize the resilient checkpoint manager for a specific agent.
        
        Args:
            agent_id: Identifier of the agent
        """
        self.agent_id = agent_id
        self.checkpoint_dir = "runtime/agent_comms/checkpoints"
        self.manager = CheckpointManager(agent_id)
        logger.info(f"Initialized ResilientCheckpointManager for {agent_id}")
    
    def create_checkpoint(self, checkpoint_type: str = "routine") -> str:
        """
        Create a checkpoint of the agent's current state with resilient IO.
        
        Args:
            checkpoint_type: Type of checkpoint ("routine", "pre_operation", "recovery")
            
        Returns:
            Path to the created checkpoint file
        """
        timestamp = self._get_timestamp()
        filename = f"{self.agent_id}_{timestamp}_{checkpoint_type}.checkpoint"
        path = os.path.join(self.checkpoint_dir, filename)
        
        try:
            # Collect agent state using resilient IO operations
            state = {
                "current_task": self._get_current_task_state(),
                "mailbox": self._get_mailbox_state(),
                "operational_context": self._get_operational_context(),
                "memory": self._get_memory_state()
            }
            
            # Create checkpoint data
            checkpoint_data = {
                "agent_id": self.agent_id,
                "timestamp": self._get_timestamp_iso(),
                "checkpoint_type": checkpoint_type,
                "version": "1.0",
                "state": state
            }
            
            # Write checkpoint data using resilient IO
            write_json(path, checkpoint_data)
            
            logger.info(f"Created {checkpoint_type} checkpoint at {path}")
            
            # Apply retention policy
            self._apply_retention_policy(checkpoint_type)
            
            return path
            
        except Exception as e:
            logger.error(f"Failed to create checkpoint: {str(e)}")
            # Try to use the original checkpoint manager as a fallback
            return self.manager.create_checkpoint(checkpoint_type)
    
    def restore_checkpoint(self, checkpoint_path: str) -> bool:
        """
        Restore agent state from a checkpoint with resilient IO.
        
        Args:
            checkpoint_path: Path to the checkpoint file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read the checkpoint data using resilient IO
            checkpoint_data = read_json(checkpoint_path)
            
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
            logger.error(f"Failed to restore checkpoint with resilient IO: {str(e)}")
            # Try to use the original checkpoint manager as a fallback
            return self.manager.restore_checkpoint(checkpoint_path)
    
    def get_latest_checkpoint(self, checkpoint_type: str = "routine") -> Optional[str]:
        """
        Get the latest checkpoint of the specified type with resilient IO.
        
        Args:
            checkpoint_type: Type of checkpoint ("routine", "pre_operation", "recovery")
            
        Returns:
            Path to the latest checkpoint or None if not found
        """
        try:
            checkpoints = self._list_checkpoints(checkpoint_type)
            if not checkpoints:
                logger.warning(f"No {checkpoint_type} checkpoints found for {self.agent_id}")
                return None
            
            # Sort by timestamp (which is part of the filename)
            sorted_checkpoints = sorted(checkpoints)
            latest = sorted_checkpoints[-1]
            logger.info(f"Found latest {checkpoint_type} checkpoint: {latest}")
            return latest
            
        except Exception as e:
            logger.error(f"Failed to get latest checkpoint with resilient IO: {str(e)}")
            # Try to use the original checkpoint manager as a fallback
            return self.manager.get_latest_checkpoint(checkpoint_type)
    
    def detect_drift(self) -> bool:
        """
        Detect potential agent drift based on operational metrics.
        
        Returns:
            True if drift is detected, False otherwise
        """
        try:
            # Use the original manager's drift detection
            return self.manager.detect_drift()
        except Exception as e:
            logger.error(f"Error detecting drift: {str(e)}")
            return False
    
    def _get_current_task_state(self) -> Dict[str, Any]:
        """Collect current task state using resilient IO."""
        try:
            # Try to get current task from working_tasks.json
            tasks_path = "runtime/working_tasks.json"
            if os.path.exists(tasks_path):
                tasks = read_json(tasks_path)
                
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
        """Collect mailbox state using resilient IO."""
        try:
            # Check agent mailbox
            inbox_path = f"runtime/agent_comms/agent_mailboxes/{self.agent_id}/inbox"
            processed_path = f"runtime/agent_comms/agent_mailboxes/{self.agent_id}/inbox/processed"
            
            if not os.path.exists(inbox_path):
                return {"last_processed_id": "", "pending_count": 0}
            
            # Count pending messages (excluding .keep and processed directory)
            pending_messages = list_dir(inbox_path)
            pending_messages = [f for f in pending_messages 
                              if os.path.isfile(os.path.join(inbox_path, f)) 
                              and f != ".keep"]
            pending_count = len(pending_messages)
            
            # Get last processed message if any
            last_processed_id = ""
            if os.path.exists(processed_path):
                processed_files = list_dir(processed_path)
                processed_files = [f for f in processed_files 
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
        """Collect operational context using resilient IO."""
        context = {
            "goals": [],
            "constraints": [],
            "decisions": []
        }
        
        try:
            # Check if there's a context file for this agent
            context_path = f"runtime/agent_data/{self.agent_id}/context.json"
            if os.path.exists(context_path):
                agent_context = read_json(context_path)
                context.update(agent_context)
        except Exception as e:
            logger.error(f"Error getting operational context: {str(e)}")
            
        return context
    
    def _get_memory_state(self) -> Dict[str, Any]:
        """Collect memory state using resilient IO."""
        memory = {
            "short_term": [],
            "session": []
        }
        
        try:
            # Check if there's a memory file for this agent
            memory_path = f"runtime/agent_data/{self.agent_id}/memory.json"
            if os.path.exists(memory_path):
                agent_memory = read_json(memory_path)
                memory.update(agent_memory)
        except Exception as e:
            logger.error(f"Error getting memory state: {str(e)}")
            
        return memory
    
    def _restore_task_state(self, task_state: Dict[str, Any]) -> None:
        """Restore task state using resilient IO."""
        try:
            if not task_state.get("id"):
                logger.warning("No task to restore")
                return
            
            # Update working_tasks.json if task exists
            tasks_path = "runtime/working_tasks.json"
            if os.path.exists(tasks_path):
                tasks = read_json(tasks_path)
                
                task_id = task_state.get("id")
                context = task_state.get("context", {})
                
                # Update the task if it exists
                for i, task in enumerate(tasks):
                    if task.get("task_id") == task_id:
                        # Only update status if it comes from context
                        if "status" in context:
                            tasks[i]["status"] = context["status"]
                        logger.info(f"Restored task state for {task_id}")
                        
                        write_json(tasks_path, tasks)
                        return
                
                logger.warning(f"Task {task_id} not found in working tasks")
        except Exception as e:
            logger.error(f"Error restoring task state: {str(e)}")
    
    def _restore_mailbox_state(self, mailbox_state: Dict[str, Any]) -> None:
        """Restore mailbox state - primarily for tracking purposes."""
        # Mailbox state is primarily for tracking purposes, no restoration needed
        logger.info(f"Mailbox state restored: {mailbox_state.get('pending_count', 0)} pending messages")
    
    def _restore_operational_context(self, operational_context: Dict[str, Any]) -> None:
        """Restore operational context using resilient IO."""
        try:
            # Ensure agent data directory exists
            agent_data_dir = f"runtime/agent_data/{self.agent_id}"
            os.makedirs(agent_data_dir, exist_ok=True)
            
            # Write context to file
            context_path = f"{agent_data_dir}/context.json"
            write_json(context_path, operational_context)
            
            logger.info(f"Restored operational context to {context_path}")
        except Exception as e:
            logger.error(f"Error restoring operational context: {str(e)}")
    
    def _restore_memory_state(self, memory_state: Dict[str, Any]) -> None:
        """Restore memory state using resilient IO."""
        try:
            # Ensure agent data directory exists
            agent_data_dir = f"runtime/agent_data/{self.agent_id}"
            os.makedirs(agent_data_dir, exist_ok=True)
            
            # Write memory to file
            memory_path = f"{agent_data_dir}/memory.json"
            write_json(memory_path, memory_state)
            
            logger.info(f"Restored memory state to {memory_path}")
        except Exception as e:
            logger.error(f"Error restoring memory state: {str(e)}")
    
    def _list_checkpoints(self, checkpoint_type: Optional[str] = None) -> List[str]:
        """List available checkpoints using resilient IO."""
        checkpoints = []
        try:
            files = list_dir(self.checkpoint_dir)
            for filename in files:
                if filename.startswith(self.agent_id) and filename.endswith(".checkpoint"):
                    if checkpoint_type is None or f"_{checkpoint_type}." in filename:
                        checkpoints.append(os.path.join(self.checkpoint_dir, filename))
        except Exception as e:
            logger.error(f"Error listing checkpoints: {str(e)}")
            
        return checkpoints
    
    def _apply_retention_policy(self, checkpoint_type: str) -> None:
        """Apply retention policy for checkpoints."""
        try:
            # Retention policies based on checkpoint type
            if checkpoint_type == "routine":
                # Keep only the last 3 routine checkpoints
                routine_checkpoints = self._list_checkpoints("routine")
                if len(routine_checkpoints) > 3:
                    # Sort by creation time
                    sorted_checkpoints = sorted(routine_checkpoints)
                    # Remove oldest checkpoints
                    for checkpoint in sorted_checkpoints[:-3]:
                        if os.path.exists(checkpoint):
                            os.remove(checkpoint)
                            logger.info(f"Removed old routine checkpoint: {checkpoint}")
            
            # For recovery checkpoints, we keep them for 7 days
            # This would require a date-based cleanup which we'll implement in a future update
        except Exception as e:
            logger.error(f"Error applying retention policy: {str(e)}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in YYYYMMDDHHMMSS format."""
        return time.strftime("%Y%m%d%H%M%S", time.gmtime())
    
    def _get_timestamp_iso(self) -> str:
        """Get current timestamp in ISO format."""
        return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

def integrate_with_agent_loop():
    """
    Example code for integrating ResilientCheckpointManager with an agent's operational loop.
    """
    # Initialize checkpoint manager
    agent_id = "agent-3"  # Replace with actual agent ID
    checkpoint_manager = ResilientCheckpointManager(agent_id)
    
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
                
            # Check for drift
            if checkpoint_manager.detect_drift():
                logger.warning("Potential drift detected, creating recovery checkpoint")
                recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
                # Consider corrective action here
                
        except Exception as e:
            # Create recovery checkpoint on error
            recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
            logger.error(f"Error during operation: {str(e)}")
            logger.info(f"Recovery point created: {recovery_checkpoint}")
            # Continue loop or initiate recovery process

if __name__ == "__main__":
    # Example usage
    manager = ResilientCheckpointManager("test-agent")
    checkpoint = manager.create_checkpoint("routine")
    print(f"Created checkpoint: {checkpoint}")
    
    # Example integration
    # integrate_with_agent_loop() 