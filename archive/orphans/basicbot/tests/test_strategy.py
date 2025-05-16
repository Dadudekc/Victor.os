from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from basicbot.strategy import Strategy


# -----------------------------
# Sample Data for Testing
# -----------------------------
@pytest.fixture
def sample_data():
    """
    Creates a DataFrame with columns 'close', 'high', and 'low'.
    We'll use simple data so that we can compute indicators.
    """
    data = {
        "close": [100, 102, 104, 106, 108],
        "high": [101, 103, 105, 107, 109],
        "low": [99, 101, 103, 105, 107],
    }
    return pd.DataFrame(data)


# -----------------------------
# Strategy Instance Fixture
# -----------------------------
@pytest.fixture
def strategy_instance():
    # Use a simple configuration dictionary and a logger.
    import logging

    logger = logging.getLogger("TestStrategy")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler()
        logger.addHandler(handler)

    return Strategy(
        maShortLength=50,
        maLongLength=200,
        rsiLength=14,
        rsiOverbought=60,
        rsiOversold=40,
        atrLength=14,
        atrMultiplier=1.5,
        riskPercent=0.5,
        profitTarget=15,
        useTrailingStop=True,
    )


# -----------------------------
# Test calculate_indicators
# -----------------------------
def test_calculate_indicators(sample_data, strategy_instance):
    df_ind = strategy_instance.calculate_indicators(sample_data)
    for col in ["SMA_short", "SMA_long", "RSI", "ATR"]:
        assert col in df_ind.columns, f"Column {col} missing in indicators."
    for col in ["SMA_short", "RSI"]:
        assert not df_ind[col].isnull().all(), f"Column {col} is all NaN."


# -----------------------------
# Test evaluate signals (BUY, SELL, HOLD)
# -----------------------------
def test_evaluate_buy_signal(strategy_instance):
    data = {
        "close": [100, 105, 110],
        "SMA_short": [98, 99, 100],
        "SMA_long": [95, 90, 90],
        "RSI": [50, 40, 35],  # RSI < rsiOverbought
    }
    df = pd.DataFrame(data)
    signal_series = strategy_instance.generate_signals(df)
    assert (
        signal_series.iloc[-1] == "BUY"
    ), f"Expected BUY, got {signal_series.iloc[-1]}"


def test_evaluate_sell_signal(strategy_instance):
    data = {
        "close": [120, 115, 110],
        "SMA_short": [125, 123, 120],
        "SMA_long": [128, 125, 123],
        "RSI": [80, 75, 70],  # RSI > rsiOversold
    }
    df = pd.DataFrame(data)
    signal_series = strategy_instance.generate_signals(df)
    assert (
        signal_series.iloc[-1] == "SELL"
    ), f"Expected SELL, got {signal_series.iloc[-1]}"


def test_evaluate_hold_signal(strategy_instance):
    """
    Construct a DataFrame where the last row should trigger a HOLD signal.
    """
    data = {
        "close": [100, 102, 104],
        "SMA_short": [99, 100, 101],
        "SMA_long": [98, 99, 100],
        "RSI": [50, 55, 59],  # Between overbought and oversold
    }
    df = pd.DataFrame(data)
    signal_series = strategy_instance.generate_signals(df)
    assert (
        signal_series.iloc[-1] == "HOLD"
    ), f"Expected HOLD, got {signal_series.iloc[-1]}"


# -----------------------------
# Test compute_exit_levels
# -----------------------------
def test_compute_exit_levels(strategy_instance, sample_data):
    df_ind = strategy_instance.calculate_indicators(sample_data)
    df_exit = strategy_instance.compute_exit_levels(df_ind)
    for col in ["stopLong", "takeProfitLong", "stopShort", "takeProfitShort"]:
        assert col in df_exit.columns, f"Exit level column {col} is missing."

    row = df_exit.iloc[-1]
    expected_stop_long = row["close"] - (row["ATR"] * strategy_instance.atrMultiplier)
    expected_tp_long = row["close"] * (1 + strategy_instance.profitTarget / 100)

    np.testing.assert_almost_equal(row["stopLong"], expected_stop_long, decimal=5)
    np.testing.assert_almost_equal(row["takeProfitLong"], expected_tp_long, decimal=5)


# -----------------------------
# Test calculate_position_size
# -----------------------------
def test_calculate_position_size(strategy_instance):
    balance = 10000
    stop_loss_pct = 0.05  # 5%
    expected_size = (balance * (strategy_instance.riskPercent / 100)) / stop_loss_pct
    pos_size = strategy_instance.calculate_position_size(balance, stop_loss_pct)
    np.testing.assert_almost_equal(pos_size, expected_size, decimal=5)


# -----------------------------
# Test optimize_signals
# -----------------------------
def test_optimize_signals(strategy_instance, sample_data):
    dummy_predictions = pd.Series(
        ["OPTIMIZED"] * len(sample_data),
        index=sample_data.index,
        name="optimized_signal",
    )
    strategy_instance.model_manager = MagicMock()
    strategy_instance.model_manager.predict.return_value = dummy_predictions

    df_ind = strategy_instance.calculate_indicators(sample_data)
    df_ind["signal"] = "HOLD"
    df_opt = strategy_instance.optimize_signals(df_ind, model_name="randomforest")

    assert "optimized_signal" in df_opt.columns
    pd.testing.assert_series_equal(
        df_opt["optimized_signal"], dummy_predictions, check_dtype=False
    )
