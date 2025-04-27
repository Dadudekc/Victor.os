import unittest
import os
import sys
import json
from unittest.mock import patch, mock_open, MagicMock

# --- Add project root to sys.path ---
script_dir = os.path.dirname(__file__) # tools/
project_root = os.path.abspath(os.path.join(script_dir, '..\..\..')) # Adjust based on actual structure
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# Module to test
from agents.dreamforge.core.prompt_staging_service import write_to_cursor_input, read_from_cursor_output

# Assume ConfigManager and log_event are available/mockable
# from dreamos.config_manager import ConfigManager # Example
# from utils.event_logger import log_event # Example

# Mock config for testing - replace with actual config loading/mocking as needed
def mock_config_manager():
    mock_cfg = MagicMock()
    mock_cfg.get_value.side_effect = lambda key: {
        'CURSOR_INPUT_FILE': 'mock_cursor_input.txt',
        'CURSOR_OUTPUT_FILE': 'mock_cursor_output.json'
    }.get(key, None)
    return mock_cfg

@patch('agents.dreamforge.core.prompt_staging_service.log_event', MagicMock()) # Mock logging globally for tests
@patch('agents.dreamforge.core.prompt_staging_service.ConfigManager', mock_config_manager) # Mock config
class TestCursorBridgeFunctions(unittest.TestCase):

    def tearDown(self):
        """Clean up mock files created during tests."""
        if os.path.exists("mock_cursor_input.txt"): os.remove("mock_cursor_input.txt")
        if os.path.exists("mock_cursor_output.json"): os.remove("mock_cursor_output.json")

    # --- Tests for write_to_cursor_input ---
    @patch("builtins.open", new_callable=mock_open)
    def test_write_to_cursor_input_success(self, mock_file):
        """Test successful write to the input file."""
        test_text = "Test prompt content"
        # Call the function using the imported name
        success = write_to_cursor_input(test_text)

        self.assertTrue(success)
        # Verify file was opened in write mode with correct encoding
        mock_file.assert_called_once_with("mock_cursor_input.txt", 'w', encoding='utf-8')
        # Verify content was written
        mock_file().write.assert_called_once_with(test_text)

    @patch("builtins.open", side_effect=IOError("Disk full"))
    def test_write_to_cursor_input_failure(self, mock_open_fail):
        """Test write failure due to IO error."""
        test_text = "This won't be written"
        # Call the function using the imported name
        success = write_to_cursor_input(test_text)

        self.assertFalse(success)
        mock_open_fail.assert_called_once_with("mock_cursor_input.txt", 'w', encoding='utf-8')

    # --- Tests for read_from_cursor_output ---
    @patch("builtins.open", new_callable=mock_open, read_data='{"key": "value", "num": 123}')
    def test_read_from_cursor_output_success(self, mock_file):
        """Test successful read and JSON parse from the output file."""
        expected_data = {"key": "value", "num": 123}
        # Call the function using the imported name
        result = read_from_cursor_output()

        self.assertEqual(result, expected_data)
        mock_file.assert_called_once_with("mock_cursor_output.json", 'r', encoding='utf-8')

    @patch("os.path.exists", return_value=False)
    def test_read_from_cursor_output_file_not_found(self, mock_exists):
        """Test read failure when the output file does not exist."""
        # Call the function using the imported name
        result = read_from_cursor_output()

        self.assertIsNone(result)
        mock_exists.assert_called_once_with("mock_cursor_output.json")

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='')
    def test_read_from_cursor_output_empty_file(self, mock_file, mock_exists):
        """Test read failure when the output file is empty."""
        # Call the function using the imported name
        result = read_from_cursor_output()

        self.assertIsNone(result)
        mock_exists.assert_called_once_with("mock_cursor_output.json")
        mock_file.assert_called_once_with("mock_cursor_output.json", 'r', encoding='utf-8')

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='{"key": "value",') # Invalid JSON
    def test_read_from_cursor_output_invalid_json(self, mock_file, mock_exists):
        """Test read failure when the output file contains invalid JSON."""
        # Call the function using the imported name
        result = read_from_cursor_output()

        self.assertIsNone(result)
        mock_exists.assert_called_once_with("mock_cursor_output.json")
        mock_file.assert_called_once_with("mock_cursor_output.json", 'r', encoding='utf-8')

# Add more tests as needed

if __name__ == '__main__':
    unittest.main() 
