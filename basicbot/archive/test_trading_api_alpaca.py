import logging
import os
import unittest
from unittest.mock import MagicMock, patch

from trading_api_alpaca import TradingAPI


class TestTradingAPI(unittest.TestCase):
    """
    Unit tests for the TradingAPI class integrated with Alpaca.
    """

    def setUp(self):
        self.logger = logging.getLogger("TradingAPI_Test")
        # Set dummy Alpaca API credentials
        os.environ["ALPACA_API_KEY"] = "dummy_key"
        os.environ["ALPACA_SECRET_KEY"] = "dummy_secret"
        os.environ["ALPACA_BASE_URL"] = "https://paper-api.alpaca.markets"

    def tearDown(self):
        # Clean up environment variables
        for var in ["ALPACA_API_KEY", "ALPACA_SECRET_KEY", "ALPACA_BASE_URL"]:
            if var in os.environ:
                del os.environ[var]

    @patch("trading_api_alpaca.tradeapi.REST")
    def test_login_success(self, mock_rest):
        """
        Test that initializing TradingAPI sets logged_in to True
        and that the Alpaca client is constructed with the correct credentials.
        """
        instance = mock_rest.return_value
        # Simulate a valid get_account response (if needed later)
        instance.get_account.return_value = MagicMock(
            buying_power="1000.00", equity="5000.00"
        )
        api = TradingAPI(logger=self.logger)
        self.assertTrue(api.logged_in)
        mock_rest.assert_called_once_with(
            "dummy_key",
            "dummy_secret",
            "https://paper-api.alpaca.markets",
            api_version="v2",
        )

    def test_login_failure_missing_credentials(self):
        """
        Test that initializing TradingAPI fails when API credentials are missing.
        """
        del os.environ["ALPACA_API_KEY"]
        del os.environ["ALPACA_SECRET_KEY"]
        with self.assertRaises(ValueError):
            TradingAPI(logger=self.logger)

    @patch("trading_api_alpaca.tradeapi.REST")
    def test_place_buy_order(self, mock_rest):
        """
        Test placing a buy order via Alpaca.
        """
        instance = mock_rest.return_value
        fake_order = MagicMock(id="order123", status="submitted")
        instance.submit_order.return_value = fake_order
        api = TradingAPI(logger=self.logger)
        response = api.place_order(symbol="AAPL", qty=1, side="buy")
        self.assertEqual(response["id"], "order123")
        instance.submit_order.assert_called_once_with(
            symbol="AAPL", qty=1, side="buy", type="market", time_in_force="gtc"
        )

    @patch("trading_api_alpaca.tradeapi.REST")
    def test_place_sell_order(self, mock_rest):
        """
        Test placing a sell order via Alpaca.
        """
        instance = mock_rest.return_value
        fake_order = MagicMock(id="order456", status="submitted")
        instance.submit_order.return_value = fake_order
        api = TradingAPI(logger=self.logger)
        response = api.place_order(symbol="AAPL", qty=1, side="sell")
        self.assertEqual(response["id"], "order456")
        instance.submit_order.assert_called_once_with(
            symbol="AAPL", qty=1, side="sell", type="market", time_in_force="gtc"
        )

    @patch("trading_api_alpaca.tradeapi.REST")
    def test_get_account(self, mock_rest):
        """
        Test retrieving account details from Alpaca.
        """
        instance = mock_rest.return_value
        fake_account = MagicMock(buying_power="1000.00", equity="5000.00")
        instance.get_account.return_value = fake_account
        api = TradingAPI(logger=self.logger)
        account_details = api.get_account()
        self.assertEqual(account_details["buying_power"], "1000.00")
        instance.get_account.assert_called_once()

    @patch("trading_api_alpaca.tradeapi.REST")
    def test_logout(self, mock_rest):
        """
        Test the logout process.
        """
        api = TradingAPI(logger=self.logger)
        api.logout()
        self.assertFalse(api.logged_in)


if __name__ == "__main__":
    unittest.main()
