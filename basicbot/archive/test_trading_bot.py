import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from trading_bot import get_historical_data, check_signals, TradingAPI

class TestTradingBot(unittest.TestCase):
    def setUp(self):
        """Set up some sample TSLA data for testing our strategy logic.
           No excuses—data must be bulletproof."""
        self.sample_data = pd.DataFrame({
            'close': [300, 302, 305, 307, 310],
            'sma_short': [299, 300, 301, 302, 303],
            'sma_long': [298, 299, 300, 301, 302],
            'rsi': [50, 55, 58, 59, 59]
        })

    def test_long_signal(self):
        """When conditions are perfect for a long trade, we should get 'long'."""
        signal = check_signals(self.sample_data)
        self.assertEqual(signal, "long", "Expected a long signal for bullish conditions.")

    def test_no_signal(self):
        """If conditions are off, we should get no signal at all."""
        # Alter the data so that RSI stays high and no valid short signal is triggered
        df = pd.DataFrame({
            'close': [290, 291, 292, 293, 294],
            'sma_short': [295, 295, 295, 295, 295],
            'sma_long': [300, 300, 300, 300, 300],
            'rsi': [70, 70, 70, 70, 70]  # Too high for a proper short signal under our rules
        })
        signal = check_signals(df)
        self.assertIsNone(signal, "No signal should be returned when conditions don't meet criteria.")

    @patch('trading_bot.api.get_position')
    def test_get_position_no_position(self, mock_get_position):
        """If there’s no TSLA position, we expect zeros—period."""
        mock_get_position.side_effect = Exception("No position")
        qty, cost = get_position()
        self.assertEqual(qty, 0, "Expected 0 quantity when no position exists.")
        self.assertEqual(cost, 0, "Expected 0 cost basis when no position exists.")

if __name__ == '__main__':
    unittest.main()
