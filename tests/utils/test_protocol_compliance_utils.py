import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure the src directory is in the Python path
# This assumes the tests are run from the project root
project_root = Path(__file__).resolve().parent.parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# We still need the original AGENT_MAILBOX_ROOT for constructing the expected path string
# Now we can import the module to test
# AGENT_MAILBOX_ROOT is evaluated at import time, so we need to import the function *after* patching
# Or, patch the constant within the function's scope. We'll use the latter.
from dreamos.utils.protocol_compliance_utils import (
    AGENT_MAILBOX_ROOT as ORIGINAL_AGENT_MAILBOX_ROOT,
)
from dreamos.utils.protocol_compliance_utils import check_mailbox_structure


class TestProtocolComplianceUtils(unittest.TestCase):

    # No longer patching Path at the class level, will patch AGENT_MAILBOX_ROOT inside each test
    def test_check_mailbox_structure_exists(self):
        """Test check_mailbox_structure when the directory exists."""
        agent_id = "test_agent_001"
        # Use the *original* constant to build the expected string path for assertion
        expected_path_str = str(ORIGINAL_AGENT_MAILBOX_ROOT / agent_id / "inbox")

        # 1. Create the final mock path object (agent_id/inbox)
        mock_final_path = MagicMock(spec=Path)
        mock_final_path.is_dir.return_value = True
        # Ensure the string representation matches the expected *real* path for assertion messages
        mock_final_path.__str__.return_value = expected_path_str

        # 2. Create the intermediate mock path object (agent_id)
        mock_intermediate_path = MagicMock(spec=Path)
        # When "/ inbox" is called on this, return the final mock
        mock_intermediate_path.__truediv__.return_value = mock_final_path

        # 3. Create the root mock path object (AGENT_MAILBOX_ROOT)
        mock_root_path = MagicMock(spec=Path)
        # When "/ agent_id" is called on this, return the intermediate mock
        mock_root_path.__truediv__.return_value = mock_intermediate_path

        # 4. Patch the AGENT_MAILBOX_ROOT constant *within the function's module*
        with patch(
            "dreamos.utils.protocol_compliance_utils.AGENT_MAILBOX_ROOT", mock_root_path
        ):
            is_compliant, details = check_mailbox_structure(agent_id)

            # Assertions
            self.assertTrue(is_compliant)
            self.assertIn("Mailbox inbox found", details)
            # Check the path string in the details message uses the mock's __str__
            self.assertIn(expected_path_str, details)

            # Check mocks were called as expected
            mock_root_path.__truediv__.assert_called_once_with(agent_id)
            mock_intermediate_path.__truediv__.assert_called_once_with("inbox")
            mock_final_path.is_dir.assert_called_once()

    def test_check_mailbox_structure_missing(self):
        """Test check_mailbox_structure when the directory is missing."""
        agent_id = "test_agent_002"
        expected_path_str = str(ORIGINAL_AGENT_MAILBOX_ROOT / agent_id / "inbox")

        # 1. Final mock path
        mock_final_path = MagicMock(spec=Path)
        mock_final_path.is_dir.return_value = False  # Directory does not exist
        mock_final_path.__str__.return_value = expected_path_str

        # 2. Intermediate mock path
        mock_intermediate_path = MagicMock(spec=Path)
        mock_intermediate_path.__truediv__.return_value = mock_final_path

        # 3. Root mock path
        mock_root_path = MagicMock(spec=Path)
        mock_root_path.__truediv__.return_value = mock_intermediate_path

        # 4. Patch AGENT_MAILBOX_ROOT
        with patch(
            "dreamos.utils.protocol_compliance_utils.AGENT_MAILBOX_ROOT", mock_root_path
        ):
            is_compliant, details = check_mailbox_structure(agent_id)

            # Assertions
            self.assertFalse(is_compliant)
            self.assertIn("Expected mailbox inbox not found", details)
            self.assertIn(expected_path_str, details)

            # Check mocks
            mock_root_path.__truediv__.assert_called_once_with(agent_id)
            mock_intermediate_path.__truediv__.assert_called_once_with("inbox")
            mock_final_path.is_dir.assert_called_once()


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
