import logging
import unittest
from unittest.mock import MagicMock, patch

from archive.trading_api_robinhood import CustomRobinhoodAPI  # Import the actual module


class TestCustomRobinhoodAPI(unittest.TestCase):

    def setUp(self):
        """
        Initialize the Robinhood API object with a mock logger.
        """
        self.logger = logging.getLogger("TestLogger")
        self.api = CustomRobinhoodAPI(logger=self.logger)

    @patch("requests.Session.post")
    def test_login_success(self, mock_post):
        """
        Test successful login response from Robinhood.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "mock_access_token"}
        mock_post.return_value = mock_response

        result = self.api.login()

        self.assertTrue(result)
        self.assertEqual(self.api.access_token, "mock_access_token")
        self.assertTrue(self.api.logged_in)

    @patch("requests.Session.post")
    def test_login_failure(self, mock_post):
        """
        Test login failure (incorrect credentials).
        """
        mock_response = MagicMock()
        mock_response.status_code = 400  # Simulating bad credentials
        mock_post.return_value = mock_response

        result = self.api.login()

        self.assertFalse(result)
        self.assertIsNone(self.api.access_token)
        self.assertFalse(self.api.logged_in)

    @patch("requests.Session.post")
    def test_mfa_verification_required(self, mock_post):
        """
        Test login requiring MFA verification.
        """
        mock_response = MagicMock()
        mock_response.status_code = 403  # Simulating MFA required
        mock_response.json.return_value = {"challenge": {"id": "mock_challenge_id"}}
        mock_post.return_value = mock_response

        result = self.api.login()

        self.assertFalse(
            result
        )  # Should wait for manual approval, so login fails initially

    @patch("requests.Session.post")
    def test_retry_login_after_verification(self, mock_post):
        """
        Test that login retries and succeeds after manual approval.
        """
        mock_failed_response = MagicMock()
        mock_failed_response.status_code = 403
        mock_failed_response.json.return_value = {
            "challenge": {"id": "mock_challenge_id"}
        }

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"access_token": "mock_access_token"}

        # First return a failed login (MFA required), then return a successful login
        mock_post.side_effect = [mock_failed_response, mock_success_response]

        self.api._wait_for_manual_approval({})

        self.assertTrue(self.api.logged_in)
        self.assertEqual(self.api.access_token, "mock_access_token")

    @patch("requests.Session.post")
    def test_logout_success(self, mock_post):
        """
        Test successful logout.
        """
        self.api.access_token = "mock_access_token"
        self.api.logged_in = True

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        self.api.logout()

        self.assertFalse(self.api.logged_in)

    @patch("requests.Session.post")
    def test_logout_failure(self, mock_post):
        """
        Test failed logout due to API error.
        """
        self.api.access_token = "mock_access_token"
        self.api.logged_in = True

        mock_response = MagicMock()
        mock_response.status_code = 500  # Internal server error
        mock_post.return_value = mock_response

        self.api.logout()

        self.assertTrue(self.api.logged_in)  # Logout should not have succeeded


if __name__ == "__main__":
    unittest.main()
