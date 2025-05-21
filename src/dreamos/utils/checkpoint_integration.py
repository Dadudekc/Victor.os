"""
Checkpoint Integration Utilities

This module provides helper functions and utilities for integrating the CheckpointManager
into agent operational loops. It simplifies the process of setting up checkpointing,
performing controlled restarts, and validating checkpoint integration.

Author: Agent-3 (Autonomous Loop Engineer)
Date: 2025-05-18
"""

import os
import time
import json
import logging
import functools
import subprocess
import sys
from typing import Tuple, Dict, List, Any, Optional, Callable
from datetime import datetime, timezone

# Import CheckpointManager from core
from dreamos.core.checkpoint_manager import CheckpointManager

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dreamos.utils.checkpoint_integration")

def setup_checkpoint_system(agent_id: str) -> Tuple[CheckpointManager, float]:
    """
    Set up the checkpoint system for an agent, creating the necessary
    directories and initializing time tracking.
    
    Args:
        agent_id: The ID of the agent
        
    Returns:
        Tuple of (checkpoint_manager, last_checkpoint_time)
    """
    logger.info(f"Setting up checkpoint system for {agent_id}")
    
    # Initialize the checkpoint manager
    checkpoint_manager = CheckpointManager(agent_id)
    
    # Initialize time tracking
    session_start_time = time.time()
    last_checkpoint_time = session_start_time
    
    # Create agent-specific directories if they don't exist
    agent_data_dir = f"runtime/agent_data/{agent_id}"
    os.makedirs(agent_data_dir, exist_ok=True)
    
    # Record session start as a checkpoint
    checkpoint_manager.create_checkpoint("session_start")
    
    return checkpoint_manager, last_checkpoint_time

def check_and_create_checkpoint(checkpoint_manager: CheckpointManager, 
                              last_checkpoint_time: float, 
                              interval: int = 1800) -> float:
    """
    Check if enough time has passed and create a routine checkpoint if needed.
    
    Args:
        checkpoint_manager: The CheckpointManager instance
        last_checkpoint_time: Timestamp of the last checkpoint
        interval: Checkpoint interval in seconds (default: 30 minutes)
        
    Returns:
        Updated last_checkpoint_time
    """
    current_time = time.time()
    if current_time - last_checkpoint_time >= interval:
        checkpoint_manager.create_checkpoint("routine")
        return current_time
    return last_checkpoint_time

def controlled_restart(checkpoint_path: str) -> bool:
    """
    Perform a controlled restart of the agent, preserving the checkpoint
    for restoration on startup.
    
    Args:
        checkpoint_path: Path to the checkpoint to use for restoration
        
    Returns:
        True if restart was initiated, False otherwise
    """
    try:
        logger.info(f"Initiating controlled restart with checkpoint: {checkpoint_path}")
        
        # Extract agent ID from checkpoint path
        checkpoint_filename = os.path.basename(checkpoint_path)
        agent_id = checkpoint_filename.split('_')[0]
        
        # Save restart information
        restart_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "checkpoint_path": checkpoint_path,
            "reason": "Controlled restart to prevent drift"
        }
        
        # Write restart info to a file
        restart_file = f"runtime/agent_data/{agent_id}/restart_info.json"
        with open(restart_file, 'w') as f:
            json.dump(restart_info, f, indent=2)
            
        # In a real environment, we would signal the agent runner to restart this agent
        # For demonstration, we'll just log the intention
        logger.info(f"Agent {agent_id} restart requested with checkpoint {checkpoint_path}")
        
        # Simulation of restart - in real implementation this would be handled by the agent runner
        logger.info("Simulating agent restart...")
        
        return True
    except Exception as e:
        logger.error(f"Error during controlled restart: {str(e)}")
        return False

def checkpoint_operation(func: Callable) -> Callable:
    """
    Decorator to automatically create checkpoints before and after operations,
    and handle errors with recovery checkpoints.
    
    Args:
        func: The function to checkpoint
        
    Returns:
        Wrapped function with checkpointing
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Find checkpoint_manager in args or kwargs
        checkpoint_manager = None
        for arg in args:
            if isinstance(arg, CheckpointManager):
                checkpoint_manager = arg
                break
                
        if not checkpoint_manager and 'checkpoint_manager' in kwargs:
            checkpoint_manager = kwargs['checkpoint_manager']
            
        if not checkpoint_manager:
            logger.warning("No CheckpointManager found for operation checkpointing")
            return func(*args, **kwargs)
            
        # Create pre-operation checkpoint
        try:
            pre_op_checkpoint = checkpoint_manager.create_checkpoint("pre_operation")
            logger.info(f"Created pre-operation checkpoint before {func.__name__}: {pre_op_checkpoint}")
            
            # Execute the operation
            result = func(*args, **kwargs)
            
            # If successful, create post-operation checkpoint
            post_op_checkpoint = checkpoint_manager.create_checkpoint("post_operation")
            logger.info(f"Created post-operation checkpoint after {func.__name__}: {post_op_checkpoint}")
            
            return result
        except Exception as e:
            # Create recovery checkpoint on error
            recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
            logger.error(f"Error in {func.__name__}: {str(e)}, recovery checkpoint: {recovery_checkpoint}")
            raise
            
    return wrapper

def validate_checkpoint_integration(checkpoint_manager: CheckpointManager) -> List[str]:
    """
    Validate the checkpoint integration for an agent.
    
    Args:
        checkpoint_manager: The CheckpointManager instance
        
    Returns:
        List of issues found (empty if integration is valid)
    """
    issues = []
    
    # Check if there are existing checkpoints
    routine_checkpoints = checkpoint_manager._list_checkpoints("routine")
    if not routine_checkpoints:
        issues.append("No routine checkpoints found - checkpointing may not be active")
        
    # Attempt to create and restore a test checkpoint
    try:
        test_checkpoint = checkpoint_manager.create_checkpoint("test")
        restore_result = checkpoint_manager.restore_checkpoint(test_checkpoint)
        if not restore_result:
            issues.append("Checkpoint restoration failed - state handlers may be incomplete")
    except Exception as e:
        issues.append(f"Checkpoint test failed: {str(e)}")
        
    # Check for custom implementations of state methods
    method_names = [
        "_get_current_task_state",
        "_get_mailbox_state",
        "_get_operational_context",
        "_get_memory_state",
        "_restore_task_state",
        "_restore_mailbox_state",
        "_restore_operational_context",
        "_restore_memory_state"
    ]
    
    base_methods = {name: getattr(CheckpointManager, name) for name in method_names}
    instance_methods = {name: getattr(checkpoint_manager, name) for name in method_names}
    
    # Check which methods are not overridden
    for name, method in instance_methods.items():
        if method.__code__.co_code == base_methods[name].__code__.co_code:
            issues.append(f"Method {name} is not customized - default implementation may be insufficient")
            
    return issues

def restore_from_latest_checkpoint(agent_id: str, checkpoint_type: str = "routine") -> bool:
    """
    Restore an agent from its latest checkpoint of the specified type.
    
    Args:
        agent_id: The ID of the agent
        checkpoint_type: Type of checkpoint to restore from
        
    Returns:
        True if restoration was successful, False otherwise
    """
    try:
        checkpoint_manager = CheckpointManager(agent_id)
        latest_checkpoint = checkpoint_manager.get_latest_checkpoint(checkpoint_type)
        
        if not latest_checkpoint:
            logger.error(f"No {checkpoint_type} checkpoints found for {agent_id}")
            return False
            
        logger.info(f"Restoring {agent_id} from checkpoint: {latest_checkpoint}")
        return checkpoint_manager.restore_checkpoint(latest_checkpoint)
    except Exception as e:
        logger.error(f"Error restoring from checkpoint: {str(e)}")
        return False

def create_example_integration(agent_id: str, output_path: str) -> bool:
    """
    Create an example integration script for the specified agent.
    
    Args:
        agent_id: The ID of the agent
        output_path: Where to write the example script
        
    Returns:
        True if the example was created successfully, False otherwise
    """
    try:
        # Basic integration example template
        template = f'''"""
Checkpoint Integration Example for {agent_id}

This script demonstrates how to integrate the CheckpointManager into {agent_id}'s
operational loop to prevent drift in long-running sessions.

Generated by: dreamos.utils.checkpoint_integration
Date: {datetime.now().strftime("%Y-%m-%d")}
"""

import time
import logging
from dreamos.core.checkpoint_manager import CheckpointManager
from dreamos.utils.checkpoint_integration import (
    setup_checkpoint_system,
    check_and_create_checkpoint,
    controlled_restart,
    checkpoint_operation
)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("{agent_id.lower()}")

@checkpoint_operation
def execute_critical_operation(checkpoint_manager, operation_name):
    """Example of a critical operation that uses checkpointing."""
    logger.info(f"Executing critical operation: {{operation_name}}")
    # Simulate work
    time.sleep(1)
    return f"{{operation_name}} completed successfully"

def main():
    """Main operational loop with checkpoint integration."""
    # Initialize checkpoint system
    checkpoint_manager, last_checkpoint_time = setup_checkpoint_system("{agent_id}")
    
    # Operational variables
    session_start_time = time.time()
    
    # Main loop
    while True:  # In real implementation, there would be a proper exit condition
        try:
            # 1. Process mailbox (simulated)
            logger.info("Processing mailbox...")
            
            # 2. Execute current task or claim new one (simulated)
            logger.info("Executing current task or claiming new one...")
            
            # Example of executing a critical operation
            result = execute_critical_operation(checkpoint_manager, "Data Processing")
            logger.info(f"Operation result: {{result}}")
            
            # 3. Regular checkpointing
            last_checkpoint_time = check_and_create_checkpoint(
                checkpoint_manager, 
                last_checkpoint_time
            )
            
            # 4. Check for session refresh
            current_time = time.time()
            if current_time - session_start_time >= 7200:  # 2 hours
                logger.info("Session duration exceeds 2 hours, initiating controlled restart")
                recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
                controlled_restart(recovery_checkpoint)
                break  # Exit loop after restart
                
            # Simulate short delay between operations
            time.sleep(5)
            
        except Exception as e:
            # Create recovery checkpoint on error
            recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
            logger.error(f"Error during operation: {{str(e)}}")
            logger.info(f"Recovery checkpoint created: {{recovery_checkpoint}}")
            
            # Continue loop instead of breaking (resilience)
            continue

if __name__ == "__main__":
    main()
'''

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write the example script
        with open(output_path, 'w') as f:
            f.write(template)
            
        logger.info(f"Created example integration script at {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating example integration: {str(e)}")
        return False

if __name__ == "__main__":
    # If run directly, this can be used to validate checkpoint integration
    # or generate example integration scripts
    pass 