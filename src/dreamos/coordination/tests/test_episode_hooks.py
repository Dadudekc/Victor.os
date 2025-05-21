"""
Tests for episode hooks functionality.
"""

import os
import signal
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ..episode_hooks import (
    on_episode_start,
    on_episode_end,
    on_episode_error,
    register_agent,
    unregister_agent,
    record_failed_task,
    get_episode_status,
    RESILIENCE_CONFIG
)

class TestEpisodeHooks(unittest.TestCase):
    def setUp(self):
        self.episode_path = Path("test_episode.yaml")
        self.test_agent_id = "test_agent"
        self.test_task_id = "test_task"
        
        # Create a temporary episode file
        with open(self.episode_path, "w") as f:
            f.write("test episode content")
    
    def tearDown(self):
        # Clean up temporary episode file
        if self.episode_path.exists():
            os.remove(self.episode_path)
    
    @patch("dreamos.coordination.episode_hooks.resume_autonomy")
    @patch("dreamos.coordination.episode_hooks.TaskManager")
    @patch("dreamos.coordination.episode_hooks.AgentManager")
    def test_episode_start(self, mock_agent_manager, mock_task_manager, mock_resume_autonomy):
        """Test episode start functionality."""
        # Test successful start
        result = on_episode_start(self.episode_path)
        self.assertTrue(result)
        
        # Verify managers were initialized
        mock_task_manager.assert_called_once()
        mock_agent_manager.assert_called_once()
        mock_resume_autonomy.assert_called_once()
        
        # Verify episode state
        status = get_episode_status()
        self.assertEqual(status["status"], "running")
        self.assertIsNotNone(status["start_time"])
        self.assertIsNone(status["end_time"])
        self.assertEqual(status["error_count"], 0)
        self.assertEqual(status["recovery_attempts"], 0)
        self.assertEqual(len(status["active_agents"]), 0)
        self.assertEqual(len(status["failed_tasks"]), 0)
        self.assertEqual(len(status["recovered_tasks"]), 0)
    
    def test_episode_end(self):
        """Test episode end functionality."""
        # Start episode first
        on_episode_start(self.episode_path)
        
        # Test successful end
        result = on_episode_end(self.episode_path)
        self.assertTrue(result)
        
        # Verify episode state
        status = get_episode_status()
        self.assertEqual(status["status"], "completed")
        self.assertIsNotNone(status["end_time"])
    
    def test_episode_error_handling(self):
        """Test episode error handling."""
        # Start episode first
        on_episode_start(self.episode_path)
        
        # Test error handling
        test_error = Exception("Test error")
        result = on_episode_error(self.episode_path, test_error)
        self.assertTrue(result)
        
        # Verify error was recorded
        status = get_episode_status()
        self.assertEqual(status["error_count"], 1)
        self.assertEqual(status["recovery_attempts"], 1)
    
    def test_agent_registration(self):
        """Test agent registration and unregistration."""
        # Start episode first
        on_episode_start(self.episode_path)
        
        # Register agent
        register_agent(self.test_agent_id)
        status = get_episode_status()
        self.assertIn(self.test_agent_id, status["active_agents"])
        
        # Unregister agent
        unregister_agent(self.test_agent_id)
        status = get_episode_status()
        self.assertNotIn(self.test_agent_id, status["active_agents"])
    
    def test_failed_task_recording(self):
        """Test recording of failed tasks."""
        # Start episode first
        on_episode_start(self.episode_path)
        
        # Record failed task
        test_error = Exception("Task failed")
        record_failed_task(self.test_task_id, test_error)
        
        # Verify task was recorded
        status = get_episode_status()
        self.assertIn(self.test_task_id, status["failed_tasks"])
    
    def test_error_threshold(self):
        """Test error threshold handling."""
        # Start episode first
        on_episode_start(self.episode_path)
        
        # Exceed error threshold
        for _ in range(RESILIENCE_CONFIG["error_threshold"]):
            on_episode_error(self.episode_path, Exception("Test error"))
        
        # Verify episode was ended
        status = get_episode_status()
        self.assertEqual(status["status"], "completed")
    
    def test_recovery_attempts(self):
        """Test recovery attempts limit."""
        # Start episode first
        on_episode_start(self.episode_path)
        
        # Exceed recovery attempts
        for _ in range(RESILIENCE_CONFIG["max_recovery_attempts"]):
            on_episode_error(self.episode_path, Exception("Test error"))
        
        # Verify episode was ended
        status = get_episode_status()
        self.assertEqual(status["status"], "completed")
    
    def test_signal_handling(self):
        """Test signal handling for graceful shutdown."""
        # Start episode first
        on_episode_start(self.episode_path)
        
        # Simulate SIGTERM
        os.kill(os.getpid(), signal.SIGTERM)
        time.sleep(0.1)  # Allow time for signal handling
        
        # Verify episode was ended
        status = get_episode_status()
        self.assertEqual(status["status"], "completed")

if __name__ == "__main__":
    unittest.main() 