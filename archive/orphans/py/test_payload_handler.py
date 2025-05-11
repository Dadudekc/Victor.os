import glob
import json
import os
import sys
import time
import unittest

# Add the relay directory to the Python path to import the handler
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../relay")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../feedback"))
)

from payload_handler import process_gpt_command, validate_parameters
from status_pusher import FEEDBACK_DIR


class TestPayloadHandlerFeedbackIntegration(unittest.TestCase):
    def setUp(self):
        # Ensure feedback dir exists and is clean before each test
        os.makedirs(FEEDBACK_DIR, exist_ok=True)
        # Clean up any feedback files from previous runs
        # Be specific to avoid deleting unrelated files
        for f in glob.glob(os.path.join(FEEDBACK_DIR, "feedback_test-*.json")):
            try:
                os.remove(f)
            except OSError as e:
                print(f"Warning: Could not remove test file {f}: {e}")

    def tearDown(self):
        # Clean up after tests
        for f in glob.glob(os.path.join(FEEDBACK_DIR, "feedback_test-*.json")):
            try:
                os.remove(f)
            except OSError as e:
                print(f"Warning: Could not remove test file {f}: {e}")

    def find_feedback_file(self, request_id):
        """Helper to find the feedback file for a given request ID."""
        time.sleep(0.1)  # Give file system time to write
        matches = glob.glob(os.path.join(FEEDBACK_DIR, f"feedback_{request_id}_*.json"))
        if matches:
            return matches[0]  # Return the first match
        return None

    def read_feedback_file(self, file_path):
        """Helper to read and parse the JSON feedback file."""
        with open(file_path, "r") as f:
            return json.load(f)

    def test_validate_parameters_valid(self):
        self.assertTrue(
            validate_parameters("list_dir", {"relative_workspace_path": "."})
        )
        self.assertTrue(
            validate_parameters(
                "edit_file", {"target_file": "a", "code_edit": "b", "instructions": "c"}
            )
        )

    def test_validate_parameters_missing(self):
        self.assertFalse(validate_parameters("edit_file", {"target_file": "a"}))
        self.assertFalse(
            validate_parameters("run_terminal", {"command": "ls"})
        )  # Missing is_background

    def test_validate_parameters_unknown_command(self):
        self.assertFalse(validate_parameters("unknown_command", {"param": "value"}))

    def test_process_valid_command_generates_feedback(self):
        request_id = "test-valid-001"
        payload = {
            "request_id": request_id,
            "timestamp": "2023-01-01T00:00:00Z",
            "command_type": "list_dir",
            "parameters": {"relative_workspace_path": "test"},
        }
        process_gpt_command(payload)

        feedback_file = self.find_feedback_file(request_id)
        self.assertIsNotNone(
            feedback_file, f"Feedback file for {request_id} not found."
        )
        feedback_data = self.read_feedback_file(feedback_file)

        self.assertEqual(feedback_data["request_id"], request_id)
        # Check for simulated_success or success depending on simulation details
        self.assertIn(feedback_data["status"], ["success", "simulated_success"])
        self.assertIn(
            "files", feedback_data["result"]
        )  # Check specific result structure for list_dir

    def test_process_missing_params_generates_error_feedback(self):
        request_id = "test-missing-params-002"
        payload = {
            "request_id": request_id,
            "timestamp": "2023-01-01T00:01:00Z",
            "command_type": "edit_file",
            "parameters": {"target_file": "oops.py"},  # Missing code_edit, instructions
        }
        process_gpt_command(payload)

        feedback_file = self.find_feedback_file(request_id)
        self.assertIsNotNone(
            feedback_file, f"Error feedback file for {request_id} not found."
        )
        feedback_data = self.read_feedback_file(feedback_file)

        self.assertEqual(feedback_data["request_id"], request_id)
        self.assertEqual(feedback_data["status"], "error")
        self.assertIn(
            "Missing or invalid parameters", feedback_data["result"]["message"]
        )

    def test_process_invalid_structure_generates_error_feedback(self):
        request_id = "test-invalid-struct-003"
        payload = {
            "request_id": request_id,
            "timestamp": "2023-01-01T00:02:00Z",
            # Missing command_type
            "parameters": {},
        }
        process_gpt_command(payload)

        feedback_file = self.find_feedback_file(request_id)
        self.assertIsNotNone(
            feedback_file, f"Structure error feedback file for {request_id} not found."
        )
        feedback_data = self.read_feedback_file(feedback_file)

        self.assertEqual(feedback_data["request_id"], request_id)
        self.assertEqual(feedback_data["status"], "error")
        self.assertIn("Invalid payload structure", feedback_data["result"]["message"])

    def test_process_harmful_command_generates_error_feedback(self):
        request_id = "test-harmful-cmd-004"
        payload = {
            "request_id": request_id,
            "timestamp": "2023-01-01T00:03:00Z",
            "command_type": "run_terminal",
            "parameters": {"command": "rm -rf /", "is_background": False},
        }
        process_gpt_command(payload)

        feedback_file = self.find_feedback_file(request_id)
        self.assertIsNotNone(
            feedback_file, f"Harmful command feedback file for {request_id} not found."
        )
        feedback_data = self.read_feedback_file(feedback_file)

        self.assertEqual(feedback_data["request_id"], request_id)
        self.assertEqual(feedback_data["status"], "error")
        self.assertIn(
            "Rejected potentially harmful command", feedback_data["result"]["message"]
        )


if __name__ == "__main__":
    unittest.main()
