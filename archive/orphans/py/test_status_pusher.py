import json
import os
import sys
import unittest
from datetime import datetime

# Add the feedback directory to the Python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../feedback"))
)

from status_pusher import FEEDBACK_DIR, format_feedback, push_feedback


class TestStatusPusher(unittest.TestCase):
    def setUp(self):
        # Ensure feedback dir exists for tests
        os.makedirs(FEEDBACK_DIR, exist_ok=True)
        # Clean up any leftover files from previous runs
        for f in os.listdir(FEEDBACK_DIR):
            if f.startswith("feedback_test-") and f.endswith(".json"):
                os.remove(os.path.join(FEEDBACK_DIR, f))

    def test_format_feedback_structure(self):
        request_id = "test-format-001"
        command_type = "test_command"
        status = "success"
        result = {"data": "test data"}

        payload = format_feedback(request_id, command_type, status, result)

        self.assertEqual(payload["request_id"], request_id)
        self.assertEqual(payload["command_type"], command_type)
        self.assertEqual(payload["status"], status)
        self.assertEqual(payload["result"], result)
        self.assertIn("timestamp", payload)
        # Check if timestamp is recent (within a few seconds)
        ts = datetime.fromisoformat(payload["timestamp"])
        self.assertTrue((datetime.now(ts.tzinfo) - ts).total_seconds() < 5)

    def test_push_feedback_creates_file(self):
        request_id = "test-push-001"
        payload = format_feedback(
            request_id, "push_test", "simulated_success", {"ok": True}
        )

        success = push_feedback(payload)
        self.assertTrue(success)

        # Find the created file (name includes timestamp)
        found_file = None
        for f in os.listdir(FEEDBACK_DIR):
            if f.startswith(f"feedback_{request_id}") and f.endswith(".json"):
                found_file = os.path.join(FEEDBACK_DIR, f)
                break

        self.assertIsNotNone(found_file, "Feedback file was not created")

        # Verify file content
        with open(found_file, "r") as f_read:
            read_payload = json.load(f_read)
        self.assertEqual(read_payload["request_id"], request_id)
        self.assertEqual(read_payload["result"], {"ok": True})

        # Clean up the created file
        os.remove(found_file)

    def test_push_feedback_handles_complex_result(self):
        request_id = "test-push-complex-002"
        complex_result = {
            "message": "Processed items",
            "items": [1, "string", {"nested": True}],
            "count": 3,
        }
        payload = format_feedback(request_id, "complex_test", "success", complex_result)

        success = push_feedback(payload)
        self.assertTrue(success)

        found_file = None
        for f in os.listdir(FEEDBACK_DIR):
            if f.startswith(f"feedback_{request_id}") and f.endswith(".json"):
                found_file = os.path.join(FEEDBACK_DIR, f)
                break

        self.assertIsNotNone(found_file, "Feedback file for complex result not created")

        with open(found_file, "r") as f_read:
            read_payload = json.load(f_read)
        self.assertEqual(read_payload["result"], complex_result)

        os.remove(found_file)


if __name__ == "__main__":
    unittest.main()
