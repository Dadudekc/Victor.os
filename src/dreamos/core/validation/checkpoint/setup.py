#!/usr/bin/env python3
"""
Dream.OS Checkpoint Verification Setup Script

This script helps set up the checkpoint verification environment by creating
necessary directories and generating demo checkpoint files for validation.
"""

import os
import json
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

# Constants
CHECKPOINT_DIR = "runtime/agent_comms/checkpoints"


def create_demo_checkpoint(
    agent_id: str,
    checkpoint_type: str,
    timestamp_offset: int = 0,
    checkpoint_dir: Optional[str] = None
) -> str:
    """
    Create a demo checkpoint file for testing.
    
    Args:
        agent_id: The ID of the agent
        checkpoint_type: The type of checkpoint (routine, pre-operation, recovery)
        timestamp_offset: Minutes to offset the timestamp by (for creating interval tests)
        checkpoint_dir: Optional custom checkpoint directory
        
    Returns:
        str: Path to the created checkpoint file
    """
    # Ensure checkpoint directory exists
    checkpoint_dir = checkpoint_dir or CHECKPOINT_DIR
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    # Create timestamp
    timestamp = datetime.now(timezone.utc) - timedelta(minutes=timestamp_offset)
    timestamp_str = timestamp.strftime("%Y%m%d%H%M%S")
    
    # Create checkpoint filename
    filename = f"{agent_id}_{timestamp_str}_{checkpoint_type}.checkpoint"
    file_path = os.path.join(checkpoint_dir, filename)
    
    # Create checkpoint data with all required fields
    checkpoint_data = {
        "agent_id": agent_id,
        "timestamp": timestamp.isoformat(),
        "checkpoint_type": checkpoint_type,
        "version": "1.0",
        "state": {
            "current_task": {
                "task_id": "DEMO-TASK-001",
                "status": "in_progress",
                "progress": 65,
                "details": "Demo task for checkpoint testing"
            },
            "mailbox": {
                "last_processed_id": "MSG-456",
                "pending_count": 2,
                "last_check": timestamp.isoformat()
            },
            "operational_context": {
                "goals": ["Demonstrate checkpoint functionality"],
                "constraints": ["Compliance with protocol"],
                "current_focus": "Checkpoint creation"
            },
            "memory": {
                "short_term": ["Created checkpoint file"],
                "session": ["Initialized agent", "Started task", "Created checkpoint"],
                "last_event_time": timestamp.isoformat()
            }
        }
    }
    
    # Write checkpoint file
    with open(file_path, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)
    
    print(f"Created demo checkpoint: {file_path}")
    return file_path


def create_demo_agent_checkpoints(
    agent_id: str,
    checkpoint_dir: Optional[str] = None,
    count: int = 3,
    interval_minutes: int = 30
) -> List[str]:
    """
    Create a set of demo checkpoint files for an agent with proper intervals.
    
    Args:
        agent_id: The ID of the agent
        checkpoint_dir: Optional custom checkpoint directory
        count: Number of checkpoint files to create
        interval_minutes: Interval between checkpoints in minutes
        
    Returns:
        List[str]: Paths to created checkpoint files
    """
    checkpoint_files = []
    
    # Create routine checkpoints with proper intervals
    for i in range(count):
        offset = i * interval_minutes
        file_path = create_demo_checkpoint(
            agent_id, 
            "routine", 
            timestamp_offset=offset,
            checkpoint_dir=checkpoint_dir
        )
        checkpoint_files.append(file_path)
    
    # Create one pre-operation checkpoint
    pre_op_file = create_demo_checkpoint(
        agent_id, 
        "pre-operation",
        timestamp_offset=5,
        checkpoint_dir=checkpoint_dir
    )
    checkpoint_files.append(pre_op_file)
    
    # Create one recovery checkpoint
    recovery_file = create_demo_checkpoint(
        agent_id, 
        "recovery",
        timestamp_offset=10,
        checkpoint_dir=checkpoint_dir
    )
    checkpoint_files.append(recovery_file)
    
    return checkpoint_files


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Dream.OS Checkpoint Verification Setup")
    parser.add_argument("--checkpoint-dir", type=str, help="Custom checkpoint directory path")
    parser.add_argument("--demo-agent-id", type=str, default="demo-agent", help="ID for the demo agent")
    parser.add_argument("--count", type=int, default=3, help="Number of routine checkpoints to create")
    parser.add_argument("--interval", type=int, default=30, help="Interval between checkpoints in minutes")
    
    return parser.parse_args()


def main():
    """Main entry point for the setup script."""
    args = parse_args()
    
    print(f"Setting up checkpoint verification environment...")
    
    # Create demo checkpoints
    create_demo_agent_checkpoints(
        args.demo_agent_id,
        checkpoint_dir=args.checkpoint_dir,
        count=args.count,
        interval_minutes=args.interval
    )
    
    print(f"\nSetup complete. Demo checkpoints created for {args.demo_agent_id}.")
    print(f"You can now run the verification tool to validate the demo checkpoints.")


if __name__ == "__main__":
    main() 