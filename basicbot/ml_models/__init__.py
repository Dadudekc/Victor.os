"""
ML models package for BasicBot trading system.

This package contains machine learning models used for:
- Market regime detection
- Price movement prediction
- Signal generation

These models enhance the trading strategies with adaptive behavior.
"""

from pathlib import Path

# Ensure models directory exists
model_dir = Path(__file__).parent / "models"
model_dir.mkdir(exist_ok=True) 