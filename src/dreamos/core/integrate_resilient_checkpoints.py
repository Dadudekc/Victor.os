"""
Resilient Checkpoint Integration

This module demonstrates how to integrate the ResilientCheckpointManager
into an agent's operational loop, with enhanced drift detection and
error recovery capabilities.

Usage:
    python -m dreamos.core.integrate_resilient_checkpoints <agent_id>
"""

import os
import sys
import time
import json
import random
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Import the resilient checkpoint manager
from dreamos.core.resilient_checkpoint_manager import ResilientCheckpointManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dreamos.core.integrate_resilient_checkpoints")

class AgentSimulator:
    """
    Simulates an agent's operational loop with resilient checkpoint integration.
    
    This demonstrates how the ResilientCheckpointManager should be integrated
    into the agent's operational loop for:
    1. Regular checkpoint creation
    2. Drift detection and recovery
    3. Error handling with recovery checkpoints
    """
    
    def __init__(self, agent_id: str):
        """
        Initialize the agent simulator.
        
        Args:
            agent_id: Identifier of the agent
        """
        self.agent_id = agent_id
        self.checkpoint_manager = ResilientCheckpointManager(agent_id)
        self.session_start_time = time.time()
        self.last_checkpoint_time = self.session_start_time
        
        # Ensure agent data directories exist
        self.agent_data_dir = Path(f"runtime/agent_data/{agent_id}")
        self.agent_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize memory file if it doesn't exist
        self.memory_path = self.agent_data_dir / "memory.json"
        if not self.memory_path.exists():
            self._initialize_memory()
        
        # Initialize context file if it doesn't exist
        self.context_path = self.agent_data_dir / "context.json"
        if not self.context_path.exists():
            self._initialize_context()
        
        logger.info(f"Initialized AgentSimulator for {agent_id}")
    
    def _initialize_memory(self):
        """Initialize the agent's memory file."""
        memory_data = {
            "short_term": [],
            "session": []
        }
        
        with open(self.memory_path, 'w') as f:
            json.dump(memory_data, f, indent=2)
        
        logger.info(f"Initialized memory file at {self.memory_path}")
    
    def _initialize_context(self):
        """Initialize the agent's context file."""
        context_data = {
            "goals": ["Demonstrate resilient checkpoint integration"],
            "constraints": ["Must handle errors gracefully"],
            "decisions": []
        }
        
        with open(self.context_path, 'w') as f:
            json.dump(context_data, f, indent=2)
        
        logger.info(f"Initialized context file at {self.context_path}")
    
    def _process_mailbox(self):
        """Simulate processing the agent's mailbox."""
        logger.info("Processing mailbox...")
        
        # Simulate finding a new message
        message_found = random.random() < 0.3  # 30% chance of finding a message
        
        if message_found:
            # Add to memory to simulate processing
            self._update_memory("Processed a new message")
    
    def _check_tasks(self):
        """Simulate checking for assigned tasks."""
        logger.info("Checking tasks...")
        
        # Simulate finding a new task
        task_updated = random.random() < 0.2  # 20% chance of task update
        
        if task_updated:
            # Add to memory to simulate task processing
            self._update_memory("Updated task status")
    
    def _execute_current_task(self):
        """Simulate executing the current task."""
        logger.info("Executing current task...")
        
        # Simulate making a decision
        decision_made = random.random() < 0.4  # 40% chance of making a decision
        
        if decision_made:
            # Update context to simulate decision making
            self._update_context(f"Made decision: Option {random.randint(1, 3)}")
    
    def _update_memory(self, entry: str):
        """
        Update the agent's memory.
        
        Args:
            entry: Memory entry to add
        """
        try:
            # Read current memory
            with open(self.memory_path, 'r') as f:
                memory_data = json.load(f)
            
            # Add entry to short-term memory
            memory_data["short_term"].append(entry)
            
            # Write updated memory
            with open(self.memory_path, 'w') as f:
                json.dump(memory_data, f, indent=2)
            
            logger.info(f"Added entry to memory: {entry}")
            
        except Exception as e:
            logger.error(f"Error updating memory: {str(e)}")
            
            # Create recovery checkpoint (defensive)
            recovery_checkpoint = self.checkpoint_manager.create_checkpoint("recovery")
            logger.info(f"Created recovery checkpoint due to memory error: {recovery_checkpoint}")
    
    def _update_context(self, decision: str):
        """
        Update the agent's operational context.
        
        Args:
            decision: Decision to add
        """
        try:
            # Read current context
            with open(self.context_path, 'r') as f:
                context_data = json.load(f)
            
            # Add decision
            context_data["decisions"].append(decision)
            
            # Write updated context
            with open(self.context_path, 'w') as f:
                json.dump(context_data, f, indent=2)
            
            logger.info(f"Added decision to context: {decision}")
            
        except Exception as e:
            logger.error(f"Error updating context: {str(e)}")
            
            # Create recovery checkpoint (defensive)
            recovery_checkpoint = self.checkpoint_manager.create_checkpoint("recovery")
            logger.info(f"Created recovery checkpoint due to context error: {recovery_checkpoint}")
    
    def _simulate_drift(self):
        """Simulate agent drift for demonstration purposes."""
        logger.info("⚠️ Simulating agent drift...")
        
        try:
            # Read current memory
            with open(self.memory_path, 'r') as f:
                memory_data = json.load(f)
            
            # Introduce "corrupted" data
            memory_data["short_term"].extend(["DRIFT INDICATOR", "Corrupted memory entry"])
            memory_data["_corrupted_field"] = "This shouldn't be here"
            
            # Write corrupted memory
            with open(self.memory_path, 'w') as f:
                json.dump(memory_data, f, indent=2)
            
            logger.info("Introduced simulated drift in memory")
            
        except Exception as e:
            logger.error(f"Error simulating drift: {str(e)}")
    
    def _simulate_error(self):
        """Simulate an error for demonstration purposes."""
        logger.info("⚠️ Simulating operational error...")
        
        # Create pre-error checkpoint
        pre_error_checkpoint = self.checkpoint_manager.create_checkpoint("pre_operation")
        logger.info(f"Created pre-operation checkpoint: {pre_error_checkpoint}")
        
        try:
            # Simulate an error during operation
            if random.random() < 0.7:  # 70% chance of error for demonstration
                raise RuntimeError("Simulated critical error during operation")
            
            logger.info("Operation completed without errors")
            
        except Exception as e:
            logger.error(f"Error during operation: {str(e)}")
            
            # Create recovery checkpoint
            recovery_checkpoint = self.checkpoint_manager.create_checkpoint("recovery")
            logger.info(f"Created recovery checkpoint: {recovery_checkpoint}")
            
            # Restore from pre-error checkpoint
            success = self.checkpoint_manager.restore_checkpoint(pre_error_checkpoint)
            if success:
                logger.info("Successfully restored from pre-error checkpoint")
            else:
                logger.error("Failed to restore from pre-error checkpoint")
    
    def run_loop(self, iterations: int = 10, simulate_drift_at: Optional[int] = None,
                simulate_error_at: Optional[int] = None):
        """
        Run the agent's operational loop.
        
        Args:
            iterations: Number of iterations to run
            simulate_drift_at: Iteration at which to simulate drift (None to disable)
            simulate_error_at: Iteration at which to simulate an error (None to disable)
        """
        logger.info(f"Starting agent loop for {self.agent_id} with {iterations} iterations")
        
        # Create initial checkpoint
        initial_checkpoint = self.checkpoint_manager.create_checkpoint("routine")
        logger.info(f"Created initial checkpoint: {initial_checkpoint}")
        
        for i in range(iterations):
            logger.info(f"\n--- Iteration {i+1}/{iterations} ---")
            
            try:
                # Simulate drift if specified
                if simulate_drift_at is not None and i + 1 == simulate_drift_at:
                    self._simulate_drift()
                
                # Simulate error if specified
                if simulate_error_at is not None and i + 1 == simulate_error_at:
                    self._simulate_error()
                    continue  # Skip rest of this iteration
                
                # Normal agent operations
                self._process_mailbox()
                self._check_tasks()
                self._execute_current_task()
                
                # Regular checkpoint creation (every 3 iterations)
                if (i + 1) % 3 == 0:
                    checkpoint = self.checkpoint_manager.create_checkpoint("routine")
                    logger.info(f"Created routine checkpoint: {checkpoint}")
                
                # Check for drift
                if self.checkpoint_manager.detect_drift():
                    logger.warning("Potential drift detected, creating recovery checkpoint")
                    recovery_checkpoint = self.checkpoint_manager.create_checkpoint("recovery")
                    logger.info(f"Created recovery checkpoint: {recovery_checkpoint}")
                    
                    # Get latest checkpoint prior to drift
                    latest = self.checkpoint_manager.get_latest_checkpoint("routine")
                    if latest:
                        logger.info(f"Restoring from latest routine checkpoint: {latest}")
                        self.checkpoint_manager.restore_checkpoint(latest)
                    
                # Simulate some time passing
                time.sleep(0.5)
                
            except Exception as e:
                # Create recovery checkpoint on unhandled error
                recovery_checkpoint = self.checkpoint_manager.create_checkpoint("recovery")
                logger.error(f"Unhandled error during operation: {str(e)}")
                logger.info(f"Recovery point created: {recovery_checkpoint}")
        
        logger.info("Agent loop completed")

def main():
    """Main entry point."""
    # Get agent ID from command line
    if len(sys.argv) > 1:
        agent_id = sys.argv[1]
    else:
        agent_id = "agent-3"  # Default to Agent-3
    
    # Create and run the agent simulator
    agent = AgentSimulator(agent_id)
    
    # Run the loop with simulated drift and error
    agent.run_loop(
        iterations=15,
        simulate_drift_at=5,   # Simulate drift at iteration 5
        simulate_error_at=10   # Simulate error at iteration 10
    )

if __name__ == "__main__":
    main() 