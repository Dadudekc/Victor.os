import pytest
import pandas as pd
from unittest.mock import MagicMock
from basicbot.backtester import Backtester

@pytest.fixture
def mock_strategy():
    """Mock trading strategy with simple indicator calculation and evaluation."""
    strategy = MagicMock()
    # For indicator calculation, add a simple SMA column.
    strategy.calculate_indicators.side_effect = lambda df: df.assign(sma=df['close'].rolling(3).mean())
    # For signal evaluation, return BUY if close is above the SMA mean, otherwise SELL.
    strategy.generate_signals.side_effect = lambda df: df['close'].apply(
        lambda x: 'BUY' if x > df['sma'].mean() else 'SELL'
    )
    return strategy

@pytest.fixture
def mock_logger():
    """Mock logger to prevent real logging."""
    from logging import getLogger
    return getLogger("TestLogger")

@pytest.fixture
def mock_api():
    """Mock API for potential data fetching (not used in this version)."""
    return MagicMock()

@pytest.fixture
def sample_data():
    """Create sample historical price data."""
    return pd.DataFrame({
        'timestamp': pd.date_range(start="2024-01-01", periods=10, freq="D"),
        'close': [100, 102, 104, 98, 97, 105, 110, 115, 120, 125]
    })

def test_backtester_initialization(mock_strategy, mock_logger, mock_api):
    """Test that the Backtester initializes correctly with required parameters."""
    backtester = Backtester(strategy=mock_strategy, logger=mock_logger, api=mock_api, symbol="TSLA", timeframe="5Min", limit=100)
    assert backtester.strategy == mock_strategy
    assert backtester.logger == mock_logger
    assert backtester.api == mock_api
    assert backtester.symbol == "TSLA"
    assert backtester.timeframe == "5Min"
    assert backtester.limit == 100

def test_run_backtest_valid_data(mock_strategy, mock_logger, sample_data):
    """Test running backtest with valid data."""
    backtester = Backtester(strategy=mock_strategy, logger=mock_logger)
    result_df = backtester.run_backtest(sample_data)
    # Validate expected columns
    for col in ['signal', 'position', 'returns', 'strategy_returns', 'cumulative_returns']:
        assert col in result_df.columns
    # Validate that at least some signals are generated
    assert not result_df['signal'].isnull().all()
    assert not result_df['position'].isnull().all()

def test_run_backtest_missing_close_column(mock_strategy, mock_logger):
    """Test that running backtest on a DataFrame missing 'close' column raises an error."""
    backtester = Backtester(strategy=mock_strategy, logger=mock_logger)
    invalid_df = pd.DataFrame({'open': [100, 102, 104]})
    with pytest.raises(ValueError, match="Data must contain a 'close' column for backtesting."):
        backtester.run_backtest(invalid_df)

def test_calculate_indicators(mock_strategy, mock_logger, sample_data):
    """Test indicator calculation with mock strategy."""
    backtester = Backtester(strategy=mock_strategy, logger=mock_logger)
    result_df = backtester._calculate_indicators(sample_data)
    # Ensure an indicator was added (from our mock strategy, column 'sma' should be added).
    assert 'sma' in result_df.columns
    # First two values may be NaN due to SMA(3)
    assert result_df['sma'].isnull().sum() == 2

def test_generate_signals(mock_strategy, mock_logger, sample_data):
    """Test signal generation logic."""
    backtester = Backtester(strategy=mock_strategy, logger=mock_logger)
    df_with_indicators = backtester._calculate_indicators(sample_data)
    result_df = backtester._generate_signals(df_with_indicators)
    # Ensure signals are assigned
    assert 'signal' in result_df.columns
    # Our mock evaluate returns either 'BUY' or 'SELL'
    assert result_df['signal'].isin(['BUY', 'SELL']).all()
    assert 'position' in result_df.columns
    assert result_df['position'].isin([1, -1]).all()

def test_calculate_returns(mock_strategy, mock_logger, sample_data):
    """Test performance metrics calculation."""
    backtester = Backtester(strategy=mock_strategy, logger=mock_logger)
    df_with_signals = backtester._calculate_indicators(sample_data)
    df_with_signals = backtester._generate_signals(df_with_signals)
    result_df = backtester._calculate_returns(df_with_signals)
    for col in ['returns', 'strategy_returns', 'cumulative_returns']:
        assert col in result_df.columns
    # First return should be NaN
    assert pd.isna(result_df.loc[0, 'returns'])
    # Check cumulative returns are computed (last value should be > 0)
    assert result_df['cumulative_returns'].iloc[-1] > 0
