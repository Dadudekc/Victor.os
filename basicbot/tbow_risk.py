"""
TBOW Tactics Risk Management Module

This module provides risk management functionality for the TBOW Tactics system:
1. Position sizing based on account equity and risk parameters
2. Risk-reward ratio calculations
3. Volatility-based position adjustments
4. Red zone warnings for drawdowns
"""

import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np

class TBOWRisk:
    """
    TBOW Tactics risk management system.
    
    This class handles:
    - Position sizing
    - Risk-reward calculations
    - Volatility adjustments
    - Drawdown monitoring
    """
    
    def __init__(
        self,
        account_equity: float,
        max_risk_per_trade: float = 0.01,  # 1% per trade
        max_daily_drawdown: float = 0.03,  # 3% daily
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize risk management system.
        
        Args:
            account_equity: Current account equity
            max_risk_per_trade: Maximum risk per trade as decimal
            max_daily_drawdown: Maximum daily drawdown as decimal
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.account_equity = account_equity
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_drawdown = max_daily_drawdown
        
        # Risk state
        self.daily_pnl = 0.0
        self.current_drawdown = 0.0
        self.trades_today = 0
        
        self.logger.info(
            f"Risk management initialized with {account_equity:.2f} equity, "
            f"{max_risk_per_trade*100:.1f}% max risk per trade"
        )
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        volatility_factor: float = 1.0
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate position size based on risk parameters.
        
        Args:
            entry_price: Planned entry price
            stop_loss: Stop loss price
            volatility_factor: Volatility adjustment factor
            
        Returns:
            Tuple of (position_size, risk_details)
        """
        try:
            # Calculate risk per share
            risk_per_share = abs(entry_price - stop_loss)
            if risk_per_share == 0:
                self.logger.warning("Invalid stop loss - same as entry price")
                return 0, {"error": "Invalid stop loss"}
            
            # Calculate dollar risk
            dollar_risk = self.account_equity * self.max_risk_per_trade
            
            # Apply volatility adjustment
            adjusted_risk = dollar_risk * volatility_factor
            
            # Calculate position size
            position_size = int(adjusted_risk / risk_per_share)
            
            # Calculate position value
            position_value = position_size * entry_price
            
            # Check if position size is too large
            if position_value > self.account_equity * 0.5:  # Max 50% of equity
                position_size = int((self.account_equity * 0.5) / entry_price)
                self.logger.warning("Position size reduced due to equity limit")
            
            # Prepare risk details
            risk_details = {
                "position_size": position_size,
                "position_value": position_size * entry_price,
                "dollar_risk": position_size * risk_per_share,
                "risk_percent": (position_size * risk_per_share) / self.account_equity,
                "volatility_adjustment": volatility_factor
            }
            
            return position_size, risk_details
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0, {"error": str(e)}
    
    def calculate_rr_ratio(
        self,
        entry_price: float,
        stop_loss: float,
        target_price: float
    ) -> Dict[str, Any]:
        """
        Calculate risk-reward ratio for a trade.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            target_price: Target price
            
        Returns:
            Dictionary with RR details
        """
        try:
            # Calculate risk and reward
            risk = abs(entry_price - stop_loss)
            reward = abs(target_price - entry_price)
            
            if risk == 0:
                return {"error": "Invalid stop loss"}
            
            # Calculate RR ratio
            rr_ratio = reward / risk
            
            # Calculate profit target percentage
            profit_target = (target_price - entry_price) / entry_price
            
            return {
                "rr_ratio": rr_ratio,
                "risk": risk,
                "reward": reward,
                "profit_target": profit_target,
                "is_valid": rr_ratio >= 2.0  # Minimum 2:1 RR
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating RR ratio: {e}")
            return {"error": str(e)}
    
    def adjust_for_volatility(
        self,
        atr: float,
        avg_atr: float
    ) -> float:
        """
        Calculate volatility adjustment factor.
        
        Args:
            atr: Current ATR
            avg_atr: Average ATR
            
        Returns:
            Volatility adjustment factor
        """
        try:
            # Calculate volatility ratio
            vol_ratio = atr / avg_atr
            
            # Adjust position size based on volatility
            if vol_ratio > 1.5:  # High volatility
                return 0.5  # Reduce position size by 50%
            elif vol_ratio > 1.2:  # Elevated volatility
                return 0.75  # Reduce position size by 25%
            elif vol_ratio < 0.8:  # Low volatility
                return 1.25  # Increase position size by 25%
            else:
                return 1.0  # Normal volatility
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility adjustment: {e}")
            return 1.0
    
    def update_pnl(self, pnl: float):
        """
        Update daily P&L and drawdown.
        
        Args:
            pnl: Trade P&L
        """
        self.daily_pnl += pnl
        self.current_drawdown = min(0, self.daily_pnl)
        self.trades_today += 1
        
        # Check for red zone
        if self.current_drawdown <= -self.account_equity * self.max_daily_drawdown:
            self.logger.warning(
                f"RED ZONE: Daily drawdown limit reached "
                f"({self.current_drawdown/self.account_equity*100:.1f}%)"
            )
    
    def check_red_zone(self) -> Dict[str, Any]:
        """
        Check if account is in red zone.
        
        Returns:
            Dictionary with red zone status
        """
        drawdown_pct = self.current_drawdown / self.account_equity
        
        return {
            "in_red_zone": drawdown_pct <= -self.max_daily_drawdown,
            "drawdown": self.current_drawdown,
            "drawdown_pct": drawdown_pct,
            "trades_today": self.trades_today,
            "daily_pnl": self.daily_pnl
        }
    
    def reset_daily(self):
        """Reset daily risk metrics."""
        self.daily_pnl = 0.0
        self.current_drawdown = 0.0
        self.trades_today = 0
        self.logger.info("Daily risk metrics reset")
    
    def update_account_equity(self, new_equity: float):
        """
        Update account equity.
        
        Args:
            new_equity: New account equity
        """
        self.account_equity = new_equity
        self.logger.info(f"Account equity updated to {new_equity:.2f}") 