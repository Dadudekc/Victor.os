"""
Unit Tests for the THEA-Cursor Bridge Pipeline (thea_to_cursor_agent.py)

Uses mocking to simulate dependencies like GUI interactions, Scraper, and Cursor injection.
"""

import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch  # Added ANY

# Adjust path to import the agent script and its dependencies
project_root = Path(__file__).resolve().parents[1]
scripts_dir = project_root / "scripts"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(scripts_dir))

# Import the script to be tested
import thea_to_cursor_agent

# Import necessary components for mocking/config
from src.dreamos.core.config import AppConfig

# --- Test Constants ---
TEST_PROMPT_GUI = "Test prompt extracted via GUI"
TEST_PROMPT_SCRAPER = "Test prompt extracted via Scraper"
KNOWN_UUID = uuid.uuid4()  # Use a fixed UUID for predictable logging check


# --- Helper Function to Create Dummy Config ---
def create_dummy_config() -> AppConfig:
    # Create a basic AppConfig structure sufficient for the agent's needs
    # This avoids needing a full config file for tests
    # Using MagicMock to simulate nested structure easily
    config = MagicMock(spec=AppConfig)
    config.paths = MagicMock()
    config.paths.gui_snippets = project_root / "assets" / "gui_snippets"  # Example path
    # Add other necessary mock attributes if the agent uses them directly
    return config


# --- Test Class ---
class TestTheaBridgePipeline(unittest.TestCase):
    def setUp(self):
        """Set up for each test."""
        # Reset any global state in the agent module if necessary
        thea_to_cursor_agent.last_processed_reply_hash = None
        # Make sure log files don't interfere (or use temp files)
        # For simplicity, we mock log writing
        self.dummy_config = create_dummy_config()

    # --- Mocks Used Across Tests ---
    @patch("scripts.thea_to_cursor_agent.inject_prompt_into_cursor")
    @patch("scripts.thea_to_cursor_agent.log_extraction")
    @patch("scripts.thea_to_cursor_agent.copy_thea_reply")
    @patch("scripts.thea_to_cursor_agent.ChatGPTScraper")  # Mock the whole class
    @patch("scripts.thea_to_cursor_agent.load_bridge_mode")
    @patch("uuid.uuid4")  # Mock UUID generation
    @patch("time.sleep")  # Avoid actual sleeping
    def run_agent_cycle(
        self,
        mock_sleep,
        mock_uuid,
        mock_load_mode,
        mock_scraper_cls,
        mock_copy_reply,
        mock_log_extract,
        mock_inject_cursor,
        mode="gui",
        gui_return=TEST_PROMPT_GUI,
        scraper_return=TEST_PROMPT_SCRAPER,
    ):
        """Helper to run one cycle of the agent's main loop with specified mocks."""
        mock_load_mode.return_value = mode
        mock_copy_reply.return_value = gui_return
        mock_uuid.return_value = KNOWN_UUID

        # Configure scraper mock instance
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.extract_latest_reply.return_value = scraper_return
        mock_scraper_cls.return_value = mock_scraper_instance  # Mock constructor return

        # --- Simulate one loop iteration ---
        # We need to break the infinite loop for testing
        # Option 1: Patch time.sleep to raise an exception after first call
        # Option 2: Modify main_loop slightly or run its contents directly
        # Let's try patching sleep to raise after first call

        # Use a side effect to allow one sleep then break
        break_exception = StopIteration("Breaking loop for test")
        mock_sleep.side_effect = [
            None,
            break_exception,
        ]  # Allow first sleep, then raise

        try:
            # Call the main loop (it will break after one cycle due to mock_sleep)
            thea_to_cursor_agent.main_loop(self.dummy_config)
        except StopIteration as e:
            if str(e) != "Breaking loop for test":
                raise  # Re-raise unexpected StopIteration

        # Return mocks for assertion
        return (
            mock_inject_cursor,
            mock_log_extract,
            mock_copy_reply,
            mock_scraper_instance,
        )

    # --- Test Cases per Mode ---

    def test_gui_mode_cycle(self):
        """Test a single cycle in GUI mode."""
        mock_inject, mock_log, mock_gui, mock_scraper_inst = self.run_agent_cycle(
            mode="gui"
        )

        mock_gui.assert_called_once_with(config=self.dummy_config)
        mock_scraper_inst.extract_latest_reply.assert_not_called()
        mock_log.assert_called_once_with(
            method="gui", text=TEST_PROMPT_GUI, extraction_uuid=KNOWN_UUID
        )
        mock_inject.assert_called_once_with(
            prompt=TEST_PROMPT_GUI, config=self.dummy_config
        )
        self.assertNotEqual(
            thea_to_cursor_agent.last_processed_reply_hash, None
        )  # State updated

    def test_gui_mode_no_new_reply(self):
        """Test GUI mode when copy_thea_reply returns None."""
        mock_inject, mock_log, mock_gui, _ = self.run_agent_cycle(
            mode="gui", gui_return=None
        )

        mock_gui.assert_called_once_with(config=self.dummy_config)
        mock_log.assert_not_called()
        mock_inject.assert_not_called()
        self.assertEqual(thea_to_cursor_agent.last_processed_reply_hash, None)

    def test_scraper_mode_cycle(self):
        """Test a single cycle in Scraper mode."""
        mock_inject, mock_log, mock_gui, mock_scraper_inst = self.run_agent_cycle(
            mode="scraper"
        )

        mock_gui.assert_not_called()
        mock_scraper_inst.extract_latest_reply.assert_called_once()
        mock_log.assert_called_once_with(
            method="scraper", text=TEST_PROMPT_SCRAPER, extraction_uuid=KNOWN_UUID
        )
        mock_inject.assert_called_once_with(
            prompt=TEST_PROMPT_SCRAPER, config=self.dummy_config
        )
        self.assertNotEqual(thea_to_cursor_agent.last_processed_reply_hash, None)

    def test_scraper_mode_no_new_reply(self):
        """Test Scraper mode when extract_latest_reply returns None."""
        mock_inject, mock_log, mock_gui, mock_scraper_inst = self.run_agent_cycle(
            mode="scraper", scraper_return=None
        )

        mock_gui.assert_not_called()
        mock_scraper_inst.extract_latest_reply.assert_called_once()
        mock_log.assert_not_called()
        mock_inject.assert_not_called()
        self.assertEqual(thea_to_cursor_agent.last_processed_reply_hash, None)

    def test_hybrid_mode_scraper_first(self):
        """Test Hybrid mode where Scraper succeeds first."""
        mock_inject, mock_log, mock_gui, mock_scraper_inst = self.run_agent_cycle(
            mode="hybrid"
        )

        mock_scraper_inst.extract_latest_reply.assert_called_once()
        mock_gui.assert_not_called()  # GUI should not be called if scraper worked
        mock_log.assert_called_once_with(
            method="scraper", text=TEST_PROMPT_SCRAPER, extraction_uuid=KNOWN_UUID
        )
        mock_inject.assert_called_once_with(
            prompt=TEST_PROMPT_SCRAPER, config=self.dummy_config
        )
        self.assertNotEqual(thea_to_cursor_agent.last_processed_reply_hash, None)

    def test_hybrid_mode_gui_fallback(self):
        """Test Hybrid mode where Scraper fails, GUI succeeds."""
        mock_inject, mock_log, mock_gui, mock_scraper_inst = self.run_agent_cycle(
            mode="hybrid", scraper_return=None
        )

        mock_scraper_inst.extract_latest_reply.assert_called_once()
        mock_gui.assert_called_once_with(
            config=self.dummy_config
        )  # GUI called as fallback
        mock_log.assert_called_once_with(
            method="gui", text=TEST_PROMPT_GUI, extraction_uuid=KNOWN_UUID
        )
        mock_inject.assert_called_once_with(
            prompt=TEST_PROMPT_GUI, config=self.dummy_config
        )
        self.assertNotEqual(thea_to_cursor_agent.last_processed_reply_hash, None)

    def test_hybrid_mode_both_fail(self):
        """Test Hybrid mode where both Scraper and GUI fail."""
        mock_inject, mock_log, mock_gui, mock_scraper_inst = self.run_agent_cycle(
            mode="hybrid", scraper_return=None, gui_return=None
        )

        mock_scraper_inst.extract_latest_reply.assert_called_once()
        mock_gui.assert_called_once_with(config=self.dummy_config)
        mock_log.assert_not_called()
        mock_inject.assert_not_called()
        self.assertEqual(thea_to_cursor_agent.last_processed_reply_hash, None)

    def test_duplicate_suppression(self):
        """Test that the same reply hash is not processed twice."""
        # Run first cycle
        mock_inject, mock_log, _, _ = self.run_agent_cycle(
            mode="gui", gui_return="First reply"
        )
        mock_log.assert_called_once()
        mock_inject.assert_called_once()
        first_hash = thea_to_cursor_agent.last_processed_reply_hash
        self.assertIsNotNone(first_hash)

        # Reset mocks for second run
        mock_log.reset_mock()
        mock_inject.reset_mock()

        # Run second cycle with the same reply
        # Need to re-patch sleep to allow another cycle break
        with patch("time.sleep", side_effect=[None, StopIteration("Break 2")]):
            try:
                thea_to_cursor_agent.main_loop(self.dummy_config)
            except StopIteration as e:
                if str(e) != "Break 2":
                    raise

        mock_log.assert_not_called()  # Should not log again
        mock_inject.assert_not_called()  # Should not inject again
        self.assertEqual(
            thea_to_cursor_agent.last_processed_reply_hash, first_hash
        )  # Hash unchanged


if __name__ == "__main__":
    unittest.main()
