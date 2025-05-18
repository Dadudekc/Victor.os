"""
risk_manager.py - Trading Risk Management System

This module provides risk management functions for the BasicBot trading system:
- Position sizing based on account balance and risk percentage
- Maximum position limits
- Drawdown protection
- Trade validation

Usage:
    from basicbot.risk_manager import RiskManager
    risk = RiskManager(max_risk_pct=1.0, max_position_size=5000)
    position_size = risk.calculate_position_size(symbol, price, stop_loss)
"""

import logging
from typing import Dict, Optional, Tuple, Any, Union
import datetime

# Handle both package and standalone imports
try:
    from basicbot.config import config
    from basicbot.logger import setup_logging
except ImportError:
    from config import config
    from logger import setup_logging


class RiskManager:
    """
    Risk management system for controlling trade size and exposure.
    """
    
    def __init__(
        self,
        max_risk_pct: float = 1.0,
        max_position_size: float = None,
        max_positions: int = None,
        max_daily_trades: int = 5,
        max_drawdown_pct: float = 5.0,
        atr_multiplier: float = 2.0,
        logger: logging.Logger = None
    ):
        """
        Initialize the risk manager with risk parameters.
        
        Args:
            max_risk_pct: Maximum percentage of account to risk per trade (0-100)
            max_position_size: Maximum position size in dollars
            max_positions: Maximum number of open positions allowed
            max_daily_trades: Maximum number of trades per day
            max_drawdown_pct: Maximum drawdown percentage allowed before halting trading
            atr_multiplier: ATR multiplier for stop loss calculation
            logger: Logger instance (will create one if not provided)
        """
        self.logger = logger or setup_logging("risk_manager")
        
        # Convert percentages to decimals
        self.max_risk_pct = max_risk_pct / 100.0 if max_risk_pct > 1.0 else max_risk_pct
        self.max_drawdown_pct = max_drawdown_pct / 100.0 if max_drawdown_pct > 1.0 else max_drawdown_pct
        
        # Other risk parameters
        self.max_position_size = max_position_size
        self.max_positions = max_positions or config.get_env("MAX_POSITIONS", 5, int)
        self.max_daily_trades = max_daily_trades
        self.atr_multiplier = atr_multiplier
        
        # Tracking variables
        self.daily_trades = 0
        self.last_trade_date = None
        self.initial_equity = None
        self.max_equity = None
        
        # Initialize risk state
        self._reset_daily_tracking()
        
        self.logger.info(
            f"Risk Manager initialized: max_risk={max_risk_pct}%, "
            f"max_drawdown={max_drawdown_pct}%, max_daily_trades={max_daily_trades}"
        )
    
    def _reset_daily_tracking(self):
        """
        Reset daily trading metrics.
        Called at the start of each trading day.
        """
        today = datetime.date.today()
        
        # If this is a new trading day, reset counters
        if self.last_trade_date != today:
            self.daily_trades = 0
            self.last_trade_date = today
            self.logger.info(f"Daily trade tracking reset for {today}")
    
    def update_account_metrics(self, equity: float, buying_power: float) -> None:
        """
        Update account metrics for risk calculations.
        
        Args:
            equity: Current account equity
            buying_power: Current buying power
        """
        # Initialize max equity on first update
        if self.initial_equity is None:
            self.initial_equity = equity
            self.max_equity = equity
        
        # Update max equity if current equity is higher
        if equity > self.max_equity:
            self.max_equity = equity
        
        # Check for drawdown
        self._check_drawdown(equity)
    
    def _check_drawdown(self, equity: float) -> bool:
        """
        Check if current drawdown exceeds maximum allowed.
        
        Args:
            equity: Current account equity
            
        Returns:
            Boolean indicating if trading should be halted due to drawdown
        """
        if self.max_equity is None or self.max_equity == 0:
            return False
        
        # Calculate current drawdown as percentage
        drawdown = (self.max_equity - equity) / self.max_equity
        
        # Log warning if drawdown exceeds threshold
        if drawdown >= self.max_drawdown_pct:
            self.logger.warning(
                f"Maximum drawdown exceeded: {drawdown:.2%} vs threshold {self.max_drawdown_pct:.2%}. "
                f"Trading should be halted."
            )
            return True
        
        return False
    
    def can_place_trade(self, account_balance: float, current_positions: int) -> Tuple[bool, str]:
        """
        Determine if a new trade can be placed based on risk rules.
        
        Args:
            account_balance: Current account balance
            current_positions: Number of currently open positions
            
        Returns:
            Tuple of (can_trade, reason)
        """
        self._reset_daily_tracking()
        
        # Check if max positions reached
        if self.max_positions is not None and current_positions >= self.max_positions:
            return False, f"Maximum positions ({self.max_positions}) reached"
        
        # Check if max daily trades reached
        if self.daily_trades >= self.max_daily_trades:
            return False, f"Maximum daily trades ({self.max_daily_trades}) reached"
        
        # Check for drawdown if we have equity data
        if self.max_equity is not None:
            drawdown = (self.max_equity - account_balance) / self.max_equity
            if drawdown >= self.max_drawdown_pct:
                return False, f"Maximum drawdown ({self.max_drawdown_pct:.2%}) exceeded: {drawdown:.2%}"
        
        return True, "Trade allowed"
    
    def calculate_position_size(
        self, 
        account_balance: float, 
        price: float, 
        stop_loss: Optional[float] = None,
        atr: Optional[float] = None
    ) -> Tuple[float, int]:
        """
        Calculate position size based on risk parameters.
        
        Args:
            account_balance: Current account balance
            price: Current price of the asset
            stop_loss: Stop loss price (if None, will use ATR if provided)
            atr: Asset's Average True Range (for stop loss calculation)
            
        Returns:
            Tuple of (position_size_dollars, position_size_shares)
        """
        # Ensure we have valid inputs
        if price <= 0:
            self.logger.error(f"Invalid price: {price}")
            return 0, 0
        
        # Calculate stop loss if not provided
        if stop_loss is None and atr is not None:
            stop_loss = price - (atr * self.atr_multiplier)
        
        # Calculate risk amount
        risk_amount = account_balance * self.max_risk_pct
        
        # Calculate position size based on stop loss
        if stop_loss is not None and stop_loss > 0 and stop_loss < price:
            # Risk per share
            risk_per_share = price - stop_loss
            
            # Shares to buy based on risk
            if risk_per_share > 0:
                shares = risk_amount / risk_per_share
            else:
                shares = 0
                self.logger.warning(f"Invalid risk per share: {risk_per_share}. Using zero shares.")
        else:
            # No stop loss provided, use fixed percentage of account
            position_dollars = account_balance * self.max_risk_pct
            shares = position_dollars / price
        
        # Calculate position size in dollars
        position_dollars = shares * price
        
        # Apply maximum position size constraint
        if self.max_position_size is not None and position_dollars > self.max_position_size:
            position_dollars = self.max_position_size
            shares = position_dollars / price
        
        # Round shares to whole number (or to appropriate precision for crypto)
        shares = int(shares)
        position_dollars = shares * price
        
        self.logger.info(
            f"Position size: ${position_dollars:.2f} ({shares} shares) "
            f"based on account balance ${account_balance:.2f} and max risk {self.max_risk_pct:.2%}"
        )
        
        return position_dollars, shares
    
    def record_trade(self) -> None:
        """
        Record that a trade was placed.
        Updates daily trade counter.
        """
        self._reset_daily_tracking()
        self.daily_trades += 1
        self.logger.info(f"Trade recorded. Daily trade count: {self.daily_trades}/{self.max_daily_trades}")
    
    def validate_trade(
        self, symbol: str, side: str, quantity: int, price: float
    ) -> Tuple[bool, str]:
        """
        Validate a trade before execution.
        
        Args:
            symbol: Trading symbol
            side: Trade side ('buy' or 'sell')
            quantity: Number of shares/contracts
            price: Current price
            
        Returns:
            Tuple of (is_valid, reason)
        """
        # Check for valid quantity
        if quantity <= 0:
            return False, f"Invalid quantity: {quantity}"
        
        # Check for valid price
        if price <= 0:
            return False, f"Invalid price: {price}"
        
        # Check for valid side
        if side.lower() not in ["buy", "sell"]:
            return False, f"Invalid side: {side}"
        
        return True, "Trade is valid"


# For testing
if __name__ == "__main__":
    # Create risk manager
    risk = RiskManager(
        max_risk_pct=1.0,
        max_position_size=5000,
        max_positions=5,
        max_daily_trades=3
    )
    
    # Test position sizing
    account_balance = 10000
    price = 100
    stop_loss = 95
    
    position_dollars, shares = risk.calculate_position_size(
        account_balance=account_balance,
        price=price,
        stop_loss=stop_loss
    )
    
    print(f"Account: ${account_balance}")
    print(f"Price: ${price}, Stop Loss: ${stop_loss}")
    print(f"Position Size: ${position_dollars:.2f} ({shares} shares)")
    
    # Test trade validation
    is_valid, reason = risk.validate_trade("TSLA", "buy", shares, price)
    print(f"Trade valid: {is_valid}, Reason: {reason}")
    
    # Test trade tracking
    risk.record_trade()
    print(f"Daily trades: {risk.daily_trades}")
    
    # Test can_place_trade
    can_trade, reason = risk.can_place_trade(account_balance, current_positions=2)
    print(f"Can place trade: {can_trade}, Reason: {reason}") 