"""
Test script for the CheckpointManager implementation.

This script tests the basic functionality of the CheckpointManager class.
"""

import os
import json
import shutil
import unittest
from pathlib import Path
from datetime import datetime, timezone
import time

# Import the module to test
from dreamos.core.checkpoint_manager import CheckpointManager

class TestCheckpointManager(unittest.TestCase):
    """Test cases for CheckpointManager."""
    
    def setUp(self):
        """Set up the test environment."""
        self.agent_id = "test-agent"
        self.checkpoint_dir = "runtime/agent_comms/checkpoints"
        self.agent_data_dir = f"runtime/agent_data/{self.agent_id}"
        
        # Ensure the checkpoint directory exists
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        
        # Create a test agent data directory
        os.makedirs(self.agent_data_dir, exist_ok=True)
        
        # Create a test manager
        self.manager = CheckpointManager(self.agent_id)
        
        # Clean up any existing test checkpoints
        self._clean_test_checkpoints()
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove test checkpoints
        self._clean_test_checkpoints()
    
    def _clean_test_checkpoints(self):
        """Remove any test checkpoints."""
        for file in os.listdir(self.checkpoint_dir):
            if file.startswith(self.agent_id) and file.endswith(".checkpoint"):
                os.remove(os.path.join(self.checkpoint_dir, file))
    
    def test_create_checkpoint(self):
        """Test creating a checkpoint."""
        # Create a checkpoint
        checkpoint_path = self.manager.create_checkpoint("routine")
        
        # Verify the checkpoint was created
        self.assertTrue(os.path.exists(checkpoint_path))
        
        # Verify the checkpoint is valid JSON
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)
        
        # Verify essential fields
        self.assertEqual(checkpoint_data["agent_id"], self.agent_id)
        self.assertEqual(checkpoint_data["checkpoint_type"], "routine")
        self.assertTrue("timestamp" in checkpoint_data)
        self.assertTrue("state" in checkpoint_data)
    
    def test_get_latest_checkpoint(self):
        """Test getting the latest checkpoint."""
        # Create multiple checkpoints
        checkpoint1 = self.manager.create_checkpoint("routine")
        checkpoint2 = self.manager.create_checkpoint("routine")
        
        # Get the latest checkpoint
        latest = self.manager.get_latest_checkpoint("routine")
        
        # Verify it's the second one (latest)
        self.assertEqual(latest, checkpoint2)
    
    def test_retention_policy(self):
        """Test the retention policy for routine checkpoints."""
        # Create 5 checkpoints with distinct timestamps to ensure they can be differentiated
        all_checkpoints = []
        for i in range(5):
            # Use a unique timestamp by adding a suffix
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + f"_{i}"
            filename = f"{self.agent_id}_{timestamp}_routine.checkpoint"
            path = os.path.join(self.checkpoint_dir, filename)
            
            # Create a simple checkpoint file directly (bypassing retention policy)
            checkpoint_data = {
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checkpoint_type": "routine",
                "version": "1.0",
                "state": {}
            }
            
            with open(path, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
                
            all_checkpoints.append(path)
            
            # Small delay to ensure files have different timestamps
            time.sleep(0.1)
        
        # Now apply the retention policy manually
        self.manager._apply_retention_policy("routine")
        
        # Verify the 3 most recent checkpoints are kept
        remaining = self.manager._list_checkpoints("routine")
        
        # We should have exactly 3 checkpoints left
        self.assertEqual(len(remaining), 3, "Retention policy should keep exactly 3 checkpoints")
        
        # The oldest 2 should be gone
        for checkpoint in all_checkpoints[:2]:
            self.assertFalse(os.path.exists(checkpoint), 
                          f"Older checkpoint {checkpoint} should be deleted")
        
        # The newest 3 should remain
        for checkpoint in all_checkpoints[2:]:
            self.assertTrue(os.path.exists(checkpoint), 
                         f"Recent checkpoint {checkpoint} should be kept")
    
    def test_restore_checkpoint(self):
        """Test restoring from a checkpoint."""
        # Create a test task
        task_dir = os.path.dirname("runtime/working_tasks.json")
        os.makedirs(task_dir, exist_ok=True)
        
        test_task = [
            {
                "task_id": "TEST-TASK-001",
                "description": "Test task",
                "assigned_agent": self.agent_id,
                "status": "assigned"
            }
        ]
        
        with open("runtime/working_tasks.json", 'w') as f:
            json.dump(test_task, f)
        
        # Create a checkpoint
        checkpoint_path = self.manager.create_checkpoint("routine")
        
        # Modify the task status
        test_task[0]["status"] = "in_progress"
        with open("runtime/working_tasks.json", 'w') as f:
            json.dump(test_task, f)
        
        # Restore the checkpoint
        self.manager.restore_checkpoint(checkpoint_path)
        
        # Verify the task was restored to its original state
        with open("runtime/working_tasks.json", 'r') as f:
            restored_task = json.load(f)
        
        self.assertEqual(restored_task[0]["status"], "assigned")
    
    def test_checkpoint_types(self):
        """Test different checkpoint types."""
        # Create checkpoints of different types
        routine = self.manager.create_checkpoint("routine")
        pre_op = self.manager.create_checkpoint("pre_operation")
        recovery = self.manager.create_checkpoint("recovery")
        
        # Verify they exist
        self.assertTrue(os.path.exists(routine))
        self.assertTrue(os.path.exists(pre_op))
        self.assertTrue(os.path.exists(recovery))
        
        # Verify we can retrieve them by type
        self.assertEqual(self.manager.get_latest_checkpoint("routine"), routine)
        self.assertEqual(self.manager.get_latest_checkpoint("pre_operation"), pre_op)
        self.assertEqual(self.manager.get_latest_checkpoint("recovery"), recovery)
    
    def test_operational_context_restoration(self):
        """Test restoring operational context."""
        # Create a test context
        test_context = {
            "goals": ["Test goal 1", "Test goal 2"],
            "constraints": ["Test constraint"],
            "decisions": ["Test decision"]
        }
        
        # Create context file
        with open(f"{self.agent_data_dir}/context.json", 'w') as f:
            json.dump(test_context, f)
        
        # Create a checkpoint
        checkpoint_path = self.manager.create_checkpoint("routine")
        
        # Modify the context
        test_context["goals"] = ["New goal"]
        with open(f"{self.agent_data_dir}/context.json", 'w') as f:
            json.dump(test_context, f)
        
        # Restore the checkpoint
        self.manager.restore_checkpoint(checkpoint_path)
        
        # Verify the context was restored
        with open(f"{self.agent_data_dir}/context.json", 'r') as f:
            restored_context = json.load(f)
        
        self.assertEqual(restored_context["goals"], ["Test goal 1", "Test goal 2"])

if __name__ == "__main__":
    unittest.main() 