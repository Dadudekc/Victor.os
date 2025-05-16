"""
Integration tests for JARVIS core architecture and interaction patterns.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from dreamos.automation.interaction import InteractionManager
from dreamos.automation.jarvis_core import JarvisCore


class TestJarvisIntegration(unittest.TestCase):
    """Integration tests for JARVIS system."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()

        # Create memory directory
        self.memory_dir = Path(self.test_dir) / "jarvis"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory_path = self.memory_dir / "memory.json"

        # Create test config
        self.config_path = Path(self.test_dir) / "test_config.json"
        with open(self.config_path, "w") as f:
            json.dump(
                {
                    "jarvis": {
                        "memory_path": str(self.memory_path),
                        "log_level": "DEBUG",
                    }
                },
                f,
            )

        # Create a direct config object for JarvisCore
        self.config = {"jarvis": {"memory_path": str(self.memory_path)}}

        # Initialize JARVIS core with direct config
        self.jarvis = JarvisCore()
        # Manually set the memory path
        self.jarvis.memory_path = self.memory_path

        # Initialize interaction manager
        self.interaction = InteractionManager(self.jarvis)

    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary directory
        shutil.rmtree(self.test_dir)

    def test_activation(self):
        """Test JARVIS activation and deactivation."""
        # Test activation
        result = self.jarvis.activate()
        self.assertTrue(result)
        self.assertTrue(self.jarvis.is_active)

        # Test deactivation
        result = self.jarvis.deactivate()
        self.assertTrue(result)
        self.assertFalse(self.jarvis.is_active)

    def test_basic_input_processing(self):
        """Test basic input processing."""
        # Activate JARVIS
        self.jarvis.activate()

        # Test basic input
        response = self.jarvis.process_input("Hello JARVIS")
        self.assertIsNotNone(response)
        self.assertIn("content", response)

        # Test with interaction manager
        response = self.interaction.process_input("What can you do?")
        self.assertIsNotNone(response)
        self.assertIn("content", response)

    def test_command_pattern(self):
        """Test command interaction pattern."""
        # Test system command
        response = self.interaction.process_input("JARVIS status")
        self.assertIsNotNone(response)
        self.assertEqual(response.get("type"), "system_response")

        # Activate JARVIS
        response = self.interaction.process_input("Activate JARVIS")
        self.assertTrue(response.get("success", False))

        # Check status again
        response = self.interaction.process_input("JARVIS status")
        self.assertEqual(response.get("system_state", {}).get("status"), "operational")

        # Deactivate JARVIS
        response = self.interaction.process_input("Deactivate JARVIS")
        self.assertTrue(response.get("success", False))

    def test_query_pattern(self):
        """Test query interaction pattern."""
        # Activate JARVIS
        self.jarvis.activate()

        # Test question
        response = self.interaction.process_input("What is your status?")
        self.assertIsNotNone(response)

        # Test with question mark
        response = self.interaction.process_input("Can you help me?")
        self.assertIsNotNone(response)

    def test_memory_persistence(self):
        """Test memory persistence."""
        # Activate JARVIS
        self.jarvis.activate()

        # Add some interactions
        self.jarvis.process_input("Hello")
        self.jarvis.process_input("How are you?")

        # Deactivate to save memory
        self.jarvis.deactivate()

        # Check if memory file was created
        self.assertTrue(
            self.memory_path.exists(), f"Memory file not found at {self.memory_path}"
        )

        # Create a new JARVIS instance
        new_jarvis = JarvisCore()
        new_jarvis.memory_path = self.memory_path
        new_jarvis.activate()

        # Check if memory was loaded
        self.assertGreater(new_jarvis.memory.size(), 0)

        # Clean up
        new_jarvis.deactivate()


if __name__ == "__main__":
    unittest.main()
