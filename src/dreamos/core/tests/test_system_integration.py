import unittest
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from ..agent_registry import AgentRegistry
from ..checkpoint_manager import CheckpointManager
from ..recovery_system import RecoverySystem
from ..agent_loop import AgentLoop

class TestSystemIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.workspace_root = "runtime/test_workspace"
        self.agent_id = "Agent-7"
        
        # Create test workspace
        os.makedirs(self.workspace_root, exist_ok=True)
        
        # Initialize components
        self.registry = AgentRegistry()
        self.checkpoint_manager = CheckpointManager(self.agent_id)
        self.recovery_system = RecoverySystem(self.agent_id, self.workspace_root)
        self.agent_loop = AgentLoop(self.agent_id, self.workspace_root)
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.workspace_root):
            import shutil
            shutil.rmtree(self.workspace_root)
            
    def test_component_registration(self):
        """Test that all components are properly registered"""
        # Register agent
        self.registry.register_agent(self.agent_id)
        
        # Verify registration
        agent_state = self.registry.get_agent_state(self.agent_id)
        self.assertIsNotNone(agent_state)
        self.assertEqual(agent_state["context"], None)
        
    def test_checkpoint_creation(self):
        """Test checkpoint creation and restoration"""
        # Create checkpoint
        checkpoint_path = self.checkpoint_manager.create_checkpoint("test")
        self.assertTrue(os.path.exists(checkpoint_path))
        
        # Verify checkpoint data
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)
            self.assertEqual(checkpoint_data["agent_id"], self.agent_id)
            self.assertEqual(checkpoint_data["checkpoint_type"], "test")
            
    def test_recovery_system(self):
        """Test recovery system functionality"""
        # Create test state
        test_state = {
            "cycle_count": 1,
            "last_action": "test_action",
            "next_action": None
        }
        
        # Save good state
        self.recovery_system.save_good_state(test_state)
        
        # Verify recovery
        recovered_state = self.recovery_system.load_last_good_state()
        self.assertEqual(recovered_state["cycle_count"], test_state["cycle_count"])
        
    def test_agent_loop_integration(self):
        """Test agent loop integration with other components"""
        # Register agent
        self.registry.register_agent(self.agent_id)
        
        # Create initial checkpoint
        self.checkpoint_manager.create_checkpoint("pre_operation")
        
        # Execute one cycle
        success = self.agent_loop.execute_cycle()
        self.assertTrue(success)
        
        # Verify state updates
        agent_state = self.registry.get_agent_state(self.agent_id)
        self.assertIsNotNone(agent_state)
        
    def test_full_system_flow(self):
        """Test complete system integration flow"""
        # 1. Register agent
        self.registry.register_agent(self.agent_id)
        
        # 2. Create initial checkpoint
        checkpoint_path = self.checkpoint_manager.create_checkpoint("pre_operation")
        
        # 3. Execute agent loop
        success = self.agent_loop.execute_cycle()
        self.assertTrue(success)
        
        # 4. Save recovery state
        current_state = self.agent_loop.state
        self.recovery_system.save_good_state(current_state)
        
        # 5. Verify all components are in sync
        agent_state = self.registry.get_agent_state(self.agent_id)
        self.assertIsNotNone(agent_state)
        
        latest_checkpoint = self.checkpoint_manager.get_latest_checkpoint("pre_operation")
        self.assertIsNotNone(latest_checkpoint)
        
        recovery_status = self.recovery_system.get_recovery_status()
        self.assertTrue(recovery_status["has_last_good_state"])

if __name__ == '__main__':
    unittest.main() 