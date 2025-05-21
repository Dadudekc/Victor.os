"""
adaptive_momentum.py - Adaptive Momentum Strategy

This strategy combines multiple technical indicators with dynamic risk management:
- Moving Average Convergence Divergence (MACD)
- Relative Strength Index (RSI)
- Average True Range (ATR)
- Volume Weighted Average Price (VWAP)
- Dynamic position sizing based on volatility
- Adaptive risk management based on market conditions
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Union, List, Any
import logging
from datetime import datetime

from basicbot.strategy import Strategy
from basicbot.risk_manager import RiskManager

class AdaptiveMomentumStrategy(Strategy):
    """
    Adaptive Momentum Strategy that adjusts to market conditions.
    """
    
    def __init__(
        self,
        symbol: str = None,
        timeframe: str = None,
        # Technical Parameters
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        rsi_length: int = 14,
        rsi_overbought: int = 70,
        rsi_oversold: int = 30,
        vwap_length: int = 20,
        atr_length: int = 14,
        # Risk Parameters
        base_risk_pct: float = 1.0,
        max_risk_pct: float = 2.0,
        min_risk_pct: float = 0.5,
        volatility_threshold: float = 2.0,
        profit_target_multiplier: float = 2.0,
        use_trailing_stop: bool = True,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the Adaptive Momentum Strategy.
        
        Args:
            symbol: Trading symbol
            timeframe: Data timeframe
            macd_fast: MACD fast period
            macd_slow: MACD slow period
            macd_signal: MACD signal period
            rsi_length: RSI calculation period
            rsi_overbought: RSI overbought threshold
            rsi_oversold: RSI oversold threshold
            vwap_length: VWAP calculation period
            atr_length: ATR calculation period
            base_risk_pct: Base risk percentage
            max_risk_pct: Maximum risk percentage
            min_risk_pct: Minimum risk percentage
            volatility_threshold: Volatility threshold for risk adjustment
            profit_target_multiplier: Multiplier for profit target
            use_trailing_stop: Whether to use trailing stops
            logger: Logger instance
        """
        super().__init__(
            symbol=symbol,
            timeframe=timeframe,
            macdFast=macd_fast,
            macdSlow=macd_slow,
            macdSignal=macd_signal,
            rsiLength=rsi_length,
            rsiOverbought=rsi_overbought,
            rsiOversold=rsi_oversold,
            atrLength=atr_length,
            riskPercent=base_risk_pct,
            profitTarget=profit_target_multiplier * 100,
            useTrailingStop=use_trailing_stop,
            logger=logger
        )
        
        # Additional parameters
        self.vwap_length = vwap_length
        self.base_risk_pct = base_risk_pct
        self.max_risk_pct = max_risk_pct
        self.min_risk_pct = min_risk_pct
        self.volatility_threshold = volatility_threshold
        
        # Initialize risk manager
        self.risk_manager = RiskManager(
            max_risk_pct=max_risk_pct,
            max_drawdown_pct=5.0,
            atr_multiplier=2.0,
            logger=logger
        )
        
        self.logger.info(
            f"AdaptiveMomentumStrategy initialized: {self.symbol} @ {self.timeframe}"
        )
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators for the strategy.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added indicator columns
        """
        # Calculate base indicators
        df = super().calculate_indicators(df)
        
        # Calculate VWAP
        df['VWAP'] = self._calculate_vwap(df)
        
        # Calculate volatility
        df['volatility'] = df['ATR'] / df['close']
        
        # Calculate trend strength
        df['trend_strength'] = abs(df['MACD'] - df['MACD_signal'])
        
        # Calculate momentum
        df['momentum'] = df['close'].pct_change(periods=5)
        
        # Calculate additional indicators
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        df['price_distance'] = (df['close'] - df['VWAP']) / df['VWAP']
        df['rsi_ma'] = df['RSI'].rolling(window=5).mean()
        df['macd_hist'] = df['MACD'] - df['MACD_signal']
        df['macd_hist_ma'] = df['macd_hist'].rolling(window=5).mean()
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals based on multiple indicators.
        
        Args:
            df: DataFrame with price data and indicators
            
        Returns:
            Series with 'BUY', 'SELL', or 'HOLD' signals
        """
        self.logger.debug("Generating trading signals...")
        
        # Initialize signals series
        signals = pd.Series(['HOLD'] * len(df), index=df.index)
        
        # Check required columns
        required_columns = [
            'close', 'VWAP', 'RSI', 'MACD', 'MACD_signal',
            'volatility', 'trend_strength', 'momentum',
            'volume_ratio', 'price_distance', 'rsi_ma',
            'macd_hist', 'macd_hist_ma'
        ]
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            self.logger.error(f"Missing required columns: {missing}")
            return signals
        
        for i in range(1, len(df)):
            # Get current values
            current = df.iloc[i]
            previous = df.iloc[i-1]
            
            # Calculate signal strength
            signal_strength = self._calculate_signal_strength(current)
            
            # Generate signals based on conditions
            if self._is_buy_signal(current, previous, signal_strength):
                signals.iloc[i] = 'BUY'
            elif self._is_sell_signal(current, previous, signal_strength):
                signals.iloc[i] = 'SELL'
        
        # Count signals
        buy_count = (signals == 'BUY').sum()
        sell_count = (signals == 'SELL').sum()
        self.logger.info(f"Generated signals: BUY={buy_count}, SELL={sell_count}")
        
        return signals
    
    def _calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate Volume Weighted Average Price.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Series with VWAP values
        """
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        volume_price = typical_price * df['volume']
        
        # Calculate cumulative values
        cumulative_volume = df['volume'].rolling(window=self.vwap_length).sum()
        cumulative_volume_price = volume_price.rolling(window=self.vwap_length).sum()
        
        # Calculate VWAP
        vwap = cumulative_volume_price / cumulative_volume
        return vwap
    
    def _calculate_signal_strength(self, current: pd.Series) -> float:
        """
        Calculate the strength of the trading signal.
        
        Args:
            current: Current price data and indicators
            
        Returns:
            Signal strength score (0-1)
        """
        # Normalize indicators
        rsi_score = (current['RSI'] - 30) / 40  # Normalize RSI to 0-1
        macd_score = abs(current['MACD'] - current['MACD_signal']) / current['close']
        trend_score = current['trend_strength'] / current['close']
        momentum_score = abs(current['momentum'])
        volume_score = min(current['volume_ratio'], 3.0) / 3.0
        price_score = abs(current['price_distance'])
        
        # Combine scores with weights
        signal_strength = (
            0.25 * rsi_score +
            0.25 * macd_score +
            0.15 * trend_score +
            0.15 * momentum_score +
            0.10 * volume_score +
            0.10 * price_score
        )
        
        return min(max(signal_strength, 0), 1)
    
    def _is_buy_signal(
        self,
        current: pd.Series,
        previous: pd.Series,
        signal_strength: float
    ) -> bool:
        """
        Determine if current conditions indicate a buy signal.
        
        Args:
            current: Current price data and indicators
            previous: Previous price data and indicators
            signal_strength: Calculated signal strength
            
        Returns:
            Boolean indicating buy signal
        """
        # Price above VWAP
        price_above_vwap = current['close'] > current['VWAP']
        
        # MACD conditions
        macd_cross_up = (
            previous['MACD'] <= previous['MACD_signal'] and
            current['MACD'] > current['MACD_signal']
        )
        macd_hist_increasing = current['macd_hist'] > current['macd_hist_ma']
        
        # RSI conditions
        rsi_oversold = current['RSI'] < self.rsiOversold
        rsi_bullish = current['RSI'] > current['rsi_ma']
        
        # Volume conditions
        volume_increasing = current['volume_ratio'] > 1.2
        
        # Momentum conditions
        positive_momentum = current['momentum'] > 0
        
        # Volatility check
        acceptable_volatility = current['volatility'] < self.volatility_threshold
        
        # Combine conditions
        return (
            price_above_vwap and
            (macd_cross_up or (rsi_oversold and rsi_bullish)) and
            macd_hist_increasing and
            volume_increasing and
            positive_momentum and
            acceptable_volatility and
            signal_strength > 0.6
        )
    
    def _is_sell_signal(
        self,
        current: pd.Series,
        previous: pd.Series,
        signal_strength: float
    ) -> bool:
        """
        Determine if current conditions indicate a sell signal.
        
        Args:
            current: Current price data and indicators
            previous: Previous price data and indicators
            signal_strength: Calculated signal strength
            
        Returns:
            Boolean indicating sell signal
        """
        # Price below VWAP
        price_below_vwap = current['close'] < current['VWAP']
        
        # MACD conditions
        macd_cross_down = (
            previous['MACD'] >= previous['MACD_signal'] and
            current['MACD'] < current['MACD_signal']
        )
        macd_hist_decreasing = current['macd_hist'] < current['macd_hist_ma']
        
        # RSI conditions
        rsi_overbought = current['RSI'] > self.rsiOverbought
        rsi_bearish = current['RSI'] < current['rsi_ma']
        
        # Volume conditions
        volume_increasing = current['volume_ratio'] > 1.2
        
        # Momentum conditions
        negative_momentum = current['momentum'] < 0
        
        # Volatility check
        high_volatility = current['volatility'] > self.volatility_threshold
        
        # Combine conditions
        return (
            price_below_vwap and
            (macd_cross_down or (rsi_overbought and rsi_bearish)) and
            macd_hist_decreasing and
            volume_increasing and
            negative_momentum and
            (high_volatility or signal_strength > 0.7)
        )
    
    def adjust_risk_parameters(self, df: pd.DataFrame) -> None:
        """
        Adjust risk parameters based on market conditions.
        
        Args:
            df: DataFrame with price data and indicators
        """
        if len(df) < 2:
            return
        
        # Get latest data
        current = df.iloc[-1]
        
        # Adjust risk based on volatility
        volatility_factor = 1.0
        if current['volatility'] > self.volatility_threshold:
            volatility_factor = 0.5
        elif current['volatility'] < self.volatility_threshold * 0.5:
            volatility_factor = 1.5
        
        # Adjust risk based on trend strength
        trend_factor = 1.0
        if current['trend_strength'] > current['close'] * 0.02:
            trend_factor = 1.2
        elif current['trend_strength'] < current['close'] * 0.01:
            trend_factor = 0.8
        
        # Adjust risk based on volume
        volume_factor = 1.0
        if current['volume_ratio'] > 1.5:
            volume_factor = 1.2
        elif current['volume_ratio'] < 0.8:
            volume_factor = 0.8
        
        # Calculate new risk percentage
        new_risk_pct = self.base_risk_pct * volatility_factor * trend_factor * volume_factor
        
        # Ensure within bounds
        new_risk_pct = min(max(new_risk_pct, self.min_risk_pct), self.max_risk_pct)
        
        # Update risk manager
        self.risk_manager.max_risk_pct = new_risk_pct
        
        self.logger.info(
            f"Risk parameters adjusted: volatility_factor={volatility_factor:.2f}, "
            f"trend_factor={trend_factor:.2f}, volume_factor={volume_factor:.2f}, "
            f"new_risk_pct={new_risk_pct:.2%}"
        ) 