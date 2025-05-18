#!/usr/bin/env python
"""
model_trainer.py - ML Model Training Harness for BasicBot

This script provides a command-line interface for training machine learning models
used in the BasicBot trading system, including:
- Market regime detection model
- Price movement prediction model (future)
- Portfolio optimization models (future)

Usage:
    python model_trainer.py --model regime --symbols SPY --start 2018-01-01 --end 2023-01-01
"""

import os
import sys
import argparse
import logging
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure parent directory is in path for imports
script_dir = Path(__file__).resolve().parent
parent_dir = script_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Import ML models
from basicbot.ml_models.regime_detector import RegimeDetector
from basicbot.logger import setup_logging

# Configure logging
logger = setup_logging("model_trainer")


def download_data(
    symbols: List[str],
    start_date: str,
    end_date: str,
    timeframe: str = "1d"
) -> Dict[str, pd.DataFrame]:
    """
    Download historical price data for training.
    
    Args:
        symbols: List of ticker symbols
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        timeframe: Data timeframe (1d, 1h, etc.)
        
    Returns:
        Dictionary of DataFrames with price data for each symbol
    """
    logger.info(f"Downloading data for {len(symbols)} symbols: {', '.join(symbols)}")
    
    data_dict = {}
    
    try:
        import yfinance as yf
        
        for symbol in symbols:
            logger.info(f"Downloading {symbol} data from {start_date} to {end_date}")
            
            # Handle timeframe conversion for yfinance
            interval = timeframe
            if timeframe == "1d":
                interval = "1d"
            elif timeframe in ["1h", "60m"]:
                interval = "1h"
            
            # Download data
            df = yf.download(symbol, start=start_date, end=end_date, interval=interval)
            
            # Convert column names to lowercase
            df.columns = [col.lower() for col in df.columns]
            
            # Store data
            if not df.empty:
                logger.info(f"Downloaded {len(df)} rows for {symbol}")
                data_dict[symbol] = df
            else:
                logger.warning(f"No data found for {symbol}")
        
    except ImportError:
        logger.error("yfinance not installed. Please install with: pip install yfinance")
        return {}
    except Exception as e:
        logger.error(f"Error downloading data: {e}")
        return {}
    
    return data_dict


def prepare_data(
    data_dict: Dict[str, pd.DataFrame],
    training_window: int = 252 * 3  # ~3 years of daily data
) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Prepare data for model training by splitting into train/test sets.
    
    Args:
        data_dict: Dictionary of DataFrames with price data
        training_window: Number of bars to use for training
        
    Returns:
        Dictionary with train/test splits for each symbol
    """
    prepared_data = {}
    
    for symbol, df in data_dict.items():
        logger.info(f"Preparing data for {symbol}")
        
        # Ensure we have enough data
        if len(df) < training_window:
            logger.warning(f"Insufficient data for {symbol}: {len(df)} < {training_window}")
            continue
        
        # Split into train/test (using last 20% for testing)
        train_size = int(len(df) * 0.8)
        
        train_data = df.iloc[:train_size]
        test_data = df.iloc[train_size:]
        
        logger.info(f"{symbol}: {len(train_data)} training rows, {len(test_data)} testing rows")
        
        prepared_data[symbol] = {
            "train": train_data,
            "test": test_data,
            "full": df
        }
    
    return prepared_data


def train_regime_model(
    data_dict: Dict[str, Dict[str, pd.DataFrame]],
    optimize: bool = True,
    model_dir: str = None
) -> Dict[str, Any]:
    """
    Train regime detection model.
    
    Args:
        data_dict: Dictionary with prepared data
        optimize: Whether to perform hyperparameter optimization
        model_dir: Directory to save trained models
        
    Returns:
        Dictionary with training results
    """
    results = {}
    
    # Initialize regime detector
    model_path = Path(model_dir) if model_dir else (script_dir / "models")
    detector = RegimeDetector(model_dir=str(model_path), logger=logger)
    
    # Train on each symbol
    for symbol, data_sets in data_dict.items():
        logger.info(f"Training regime model for {symbol}...")
        
        try:
            # Train on training data
            metrics = detector.train(data_sets["train"], optimize=optimize)
            
            # Test on test data
            test_prediction = detector.predict(data_sets["test"].iloc[-50:])
            
            # Get strategy recommendation
            strategy = detector.get_regime_strategy(test_prediction)
            
            # Store results
            results[symbol] = {
                "metrics": metrics,
                "current_regime": test_prediction,
                "recommended_strategy": strategy
            }
            
            logger.info(f"Regime model for {symbol} trained successfully")
            logger.info(f"Current regime: {test_prediction['regime']} (confidence: {test_prediction['confidence']:.2f})")
            
        except Exception as e:
            logger.error(f"Error training regime model for {symbol}: {e}")
            results[symbol] = {"error": str(e)}
    
    return results


def train_models(args):
    """Train models based on command line arguments."""
    # Download data
    data_dict = download_data(args.symbols, args.start, args.end, args.timeframe)
    
    if not data_dict:
        logger.error("No data available for training. Exiting.")
        return
    
    # Prepare data
    prepared_data = prepare_data(data_dict, args.window)
    
    if not prepared_data:
        logger.error("Failed to prepare training data. Exiting.")
        return
    
    # Train specified model
    if args.model.lower() == "regime":
        results = train_regime_model(
            prepared_data,
            optimize=not args.no_optimize,
            model_dir=args.model_dir
        )
        
        # Print summary
        print("\n===== Regime Model Training Summary =====")
        for symbol, res in results.items():
            if "error" in res:
                print(f"\n{symbol}: ERROR - {res['error']}")
                continue
                
            metrics = res["metrics"]
            regime = res["current_regime"]
            strategy = res["recommended_strategy"]
            
            print(f"\n{symbol}:")
            print(f"  Accuracy: {metrics['accuracy']:.4f}")
            print(f"  Current Regime: {regime['regime']} (confidence: {regime['confidence']:.2f})")
            print(f"  Recommended Strategy: {strategy['strategy_type']}")
            print(f"  Position Size: {strategy['position_size_modifier']:.2f}x")
            
    else:
        logger.error(f"Unknown model type: {args.model}")
        return


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Train ML models for BasicBot")
    
    parser.add_argument(
        "--model", type=str, required=True,
        choices=["regime", "price", "portfolio"],
        help="Type of model to train"
    )
    
    parser.add_argument(
        "--symbols", type=str, nargs="+", required=True,
        help="Ticker symbols to train on"
    )
    
    parser.add_argument(
        "--start", type=str, default="2018-01-01",
        help="Start date for training data (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--end", type=str, 
        default=datetime.now().strftime("%Y-%m-%d"),
        help="End date for training data (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--timeframe", type=str, default="1d",
        choices=["1d", "1h", "15m"],
        help="Data timeframe"
    )
    
    parser.add_argument(
        "--window", type=int, default=756,
        help="Training window size (number of bars)"
    )
    
    parser.add_argument(
        "--model-dir", type=str, default=None,
        help="Directory to save trained models"
    )
    
    parser.add_argument(
        "--no-optimize", action="store_true",
        help="Skip hyperparameter optimization"
    )
    
    args = parser.parse_args()
    
    # Run training
    train_models(args)


if __name__ == "__main__":
    main() 