"""
Resilient Checkpoint Demo

This module demonstrates the ResilientCheckpointManager in action, showing
how it can be used to create checkpoints, detect drift, and recover from errors.

Usage:
    python -m dreamos.core.run_resilient_checkpoint_demo
"""

import os
import json
import time
import logging
import random
from pathlib import Path

# Import the checkpoint manager
from dreamos.core.resilient_checkpoint_manager import ResilientCheckpointManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("checkpoint_demo")

def setup_environment(agent_id):
    """Set up the test environment."""
    # Ensure checkpoint directory exists
    checkpoint_dir = Path("runtime/agent_comms/checkpoints")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure agent data directory exists
    agent_data_dir = Path(f"runtime/agent_data/{agent_id}")
    agent_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample memory file if it doesn't exist
    memory_path = agent_data_dir / "memory.json"
    if not memory_path.exists():
        with open(memory_path, 'w') as f:
            json.dump({
                "short_term": ["Initial memory entry"],
                "session": ["Initial session entry"]
            }, f)
    
    # Create sample context file if it doesn't exist
    context_path = agent_data_dir / "context.json"
    if not context_path.exists():
        with open(context_path, 'w') as f:
            json.dump({
                "goals": ["Demonstrate checkpoint system"],
                "constraints": ["Must be resilient to errors"],
                "decisions": ["Initial decision"]
            }, f)
    
    # Ensure agent mailbox directories exist
    inbox_dir = Path(f"runtime/agent_comms/agent_mailboxes/{agent_id}/inbox")
    inbox_dir.mkdir(parents=True, exist_ok=True)
    
    processed_dir = inbox_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample working tasks file if it doesn't exist
    tasks_dir = Path("runtime")
    tasks_dir.mkdir(parents=True, exist_ok=True)
    
    tasks_path = tasks_dir / "working_tasks.json"
    if not tasks_path.exists():
        with open(tasks_path, 'w') as f:
            json.dump([
                {
                    "task_id": "DEMO-TASK-001",
                    "assigned_agent": agent_id,
                    "status": "in_progress",
                    "description": "Checkpoint system demo task"
                }
            ], f)
    
    logger.info(f"Environment set up for agent {agent_id}")
    
    return {
        "checkpoint_dir": checkpoint_dir,
        "agent_data_dir": agent_data_dir,
        "memory_path": memory_path,
        "context_path": context_path,
        "tasks_path": tasks_path
    }

def simulate_drift(memory_path):
    """Simulate agent drift by modifying memory."""
    try:
        # Read current memory
        with open(memory_path, 'r') as f:
            memory_data = json.load(f)
        
        # Add drift indicators
        memory_data["short_term"].extend([
            "DRIFT INDICATOR: Unexpected memory item",
            "DRIFT INDICATOR: Another unexpected item"
        ])
        memory_data["_corrupted_field"] = "This shouldn't be here"
        
        # Write back modified memory
        with open(memory_path, 'w') as f:
            json.dump(memory_data, f, indent=2)
        
        logger.info(f"Simulated drift in memory file: {memory_path}")
        
    except Exception as e:
        logger.error(f"Error simulating drift: {str(e)}")

def simulate_error():
    """Simulate a random error."""
    error_types = [
        "IOError: Failed to read file",
        "PermissionError: Access denied",
        "TimeoutError: Operation timed out",
        "ConnectionError: Failed to connect",
        "ValueError: Invalid data format"
    ]
    
    error = random.choice(error_types)
    logger.error(f"Simulated error: {error}")
    
    raise RuntimeError(f"Simulated error: {error}")

def run_demo():
    """Run the checkpoint demo."""
    logger.info("=== Starting Resilient Checkpoint Manager Demo ===")
    
    # Set up agent ID
    agent_id = "demo-agent"
    
    # Set up environment
    env = setup_environment(agent_id)
    memory_path = env["memory_path"]
    context_path = env["context_path"]
    
    # Initialize checkpoint manager
    checkpoint_manager = ResilientCheckpointManager(agent_id)
    
    # Demo Part 1: Basic Checkpoint Creation
    logger.info("\n=== Part 1: Basic Checkpoint Creation ===")
    
    # Create checkpoints of different types
    routine_checkpoint = checkpoint_manager.create_checkpoint("routine")
    logger.info(f"Created routine checkpoint: {routine_checkpoint}")
    
    pre_op_checkpoint = checkpoint_manager.create_checkpoint("pre_operation")
    logger.info(f"Created pre-operation checkpoint: {pre_op_checkpoint}")
    
    recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
    logger.info(f"Created recovery checkpoint: {recovery_checkpoint}")
    
    # Get latest checkpoints
    latest_routine = checkpoint_manager.get_latest_checkpoint("routine")
    logger.info(f"Latest routine checkpoint: {latest_routine}")
    
    # Demo Part 2: Drift Simulation and Recovery
    logger.info("\n=== Part 2: Drift Simulation and Recovery ===")
    
    # Create pre-drift state memory
    with open(memory_path, 'w') as f:
        json.dump({
            "short_term": ["Clean memory state"],
            "session": ["Clean session state"]
        }, f, indent=2)
    
    # Create checkpoint of clean state
    clean_checkpoint = checkpoint_manager.create_checkpoint("pre_drift")
    logger.info(f"Created clean state checkpoint: {clean_checkpoint}")
    
    # Simulate drift
    simulate_drift(memory_path)
    
    # Verify drift
    with open(memory_path, 'r') as f:
        memory_after_drift = json.load(f)
    logger.info(f"Memory after drift: {memory_after_drift}")
    
    # Detect drift (in a real scenario, we would use the detect_drift method)
    # For demo purposes, we'll assume drift was detected
    logger.warning("Drift detected - initiating recovery")
    
    # Restore from clean checkpoint
    success = checkpoint_manager.restore_checkpoint(clean_checkpoint)
    
    if success:
        logger.info("Successfully restored from clean checkpoint")
        
        # Verify restoration
        with open(memory_path, 'r') as f:
            restored_memory = json.load(f)
        logger.info(f"Memory after restoration: {restored_memory}")
    else:
        logger.error("Failed to restore from checkpoint")
    
    # Demo Part 3: Error Handling
    logger.info("\n=== Part 3: Error Handling ===")
    
    # Create pre-error state
    with open(context_path, 'w') as f:
        json.dump({
            "goals": ["Demonstrate checkpoint system"],
            "constraints": ["Must be resilient to errors"],
            "decisions": ["Pre-error decision"]
        }, f, indent=2)
    
    # Create pre-error checkpoint
    pre_error_checkpoint = checkpoint_manager.create_checkpoint("pre_operation")
    logger.info(f"Created pre-error checkpoint: {pre_error_checkpoint}")
    
    # Try to perform risky operation
    try:
        logger.info("Attempting risky operation...")
        
        # Simulate an error
        simulate_error()
        
        logger.info("Risky operation completed successfully (this shouldn't happen)")
        
    except Exception as e:
        logger.error(f"Error during operation: {str(e)}")
        
        # Create recovery checkpoint
        error_recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
        logger.info(f"Created error recovery checkpoint: {error_recovery_checkpoint}")
        
        # Restore from pre-error checkpoint
        logger.info(f"Restoring from pre-error checkpoint: {pre_error_checkpoint}")
        success = checkpoint_manager.restore_checkpoint(pre_error_checkpoint)
        
        if success:
            logger.info("Successfully restored from pre-error checkpoint")
            
            # Verify restoration
            with open(context_path, 'r') as f:
                restored_context = json.load(f)
            logger.info(f"Context after restoration: {restored_context}")
        else:
            logger.error("Failed to restore from pre-error checkpoint")
    
    # Demo Part 4: Checkpoint Retention Policy
    logger.info("\n=== Part 4: Checkpoint Retention Policy ===")
    
    # Count initial routine checkpoints
    routine_checkpoints_before = [f for f in os.listdir("runtime/agent_comms/checkpoints") 
                                if f.startswith(agent_id) and f.endswith("routine.checkpoint")]
    logger.info(f"Initial routine checkpoints count: {len(routine_checkpoints_before)}")
    
    # Create several more routine checkpoints
    logger.info("Creating 5 additional routine checkpoints...")
    for i in range(5):
        checkpoint_manager.create_checkpoint("routine")
        time.sleep(0.1)  # Ensure unique timestamps
    
    # Count routine checkpoints after
    routine_checkpoints_after = [f for f in os.listdir("runtime/agent_comms/checkpoints") 
                               if f.startswith(agent_id) and f.endswith("routine.checkpoint")]
    logger.info(f"Final routine checkpoints count: {len(routine_checkpoints_after)}")
    
    if len(routine_checkpoints_after) <= 3:
        logger.info("✅ Retention policy working correctly - keeping only the most recent checkpoints")
    else:
        logger.warning("❌ Retention policy not enforced as expected")
    
    logger.info("\n=== Resilient Checkpoint Manager Demo Complete ===")
    logger.info(f"Checkpoint directory: runtime/agent_comms/checkpoints")
    logger.info(f"Agent data directory: runtime/agent_data/{agent_id}")

if __name__ == "__main__":
    run_demo() 