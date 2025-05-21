"""
Data management module for backtesting framework.

This module provides the DataManager class for loading and preprocessing historical data
used in backtesting strategies.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Dict, Any
import pandas as pd

from .utils import ValidationError, BacktestError

logger = logging.getLogger(__name__)

class DataManager:
    """Manages historical data loading and preprocessing for backtesting."""
    
    def __init__(self, data_dir: Union[str, Path]):
        """
        Initialize the data manager.
        
        Args:
            data_dir: Directory containing historical data files
        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise ValidationError(f"Data directory does not exist: {data_dir}")
            
    def load_data(
        self,
        start_date: datetime,
        end_date: datetime,
        data_type: str = "market",
        symbols: Optional[list] = None
    ) -> pd.DataFrame:
        """
        Load historical data for the specified period.
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            data_type: Type of data to load (e.g., "market", "fundamental")
            symbols: Optional list of symbols to load
            
        Returns:
            DataFrame containing the historical data
        """
        try:
            # Validate dates
            if start_date >= end_date:
                raise ValidationError("Start date must be before end date")
                
            # Load data based on type
            if data_type == "market":
                return self._load_market_data(start_date, end_date, symbols)
            elif data_type == "fundamental":
                return self._load_fundamental_data(start_date, end_date, symbols)
            else:
                raise ValidationError(f"Unsupported data type: {data_type}")
                
        except Exception as e:
            logger.error(f"Failed to load data: {str(e)}")
            raise BacktestError(f"Failed to load data: {str(e)}")
            
    def _load_market_data(
        self,
        start_date: datetime,
        end_date: datetime,
        symbols: Optional[list]
    ) -> pd.DataFrame:
        """
        Load market data from CSV files.
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            symbols: Optional list of symbols to load
            
        Returns:
            DataFrame containing market data
        """
        try:
            # Get list of data files
            data_files = list(self.data_dir.glob("*.csv"))
            if not data_files:
                raise BacktestError("No data files found")
                
            # Load and combine data
            dfs = []
            for file in data_files:
                df = pd.read_csv(file, parse_dates=['timestamp'])
                df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
                
                if symbols:
                    df = df[df['symbol'].isin(symbols)]
                    
                dfs.append(df)
                
            if not dfs:
                return pd.DataFrame()
                
            # Combine all data
            combined_df = pd.concat(dfs, ignore_index=True)
            combined_df.sort_values('timestamp', inplace=True)
            
            return combined_df
            
        except Exception as e:
            logger.error(f"Failed to load market data: {str(e)}")
            raise BacktestError(f"Failed to load market data: {str(e)}")
            
    def _load_fundamental_data(
        self,
        start_date: datetime,
        end_date: datetime,
        symbols: Optional[list]
    ) -> pd.DataFrame:
        """
        Load fundamental data from JSON files.
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            symbols: Optional list of symbols to load
            
        Returns:
            DataFrame containing fundamental data
        """
        try:
            # Get list of data files
            data_files = list(self.data_dir.glob("*.json"))
            if not data_files:
                raise BacktestError("No fundamental data files found")
                
            # Load and combine data
            dfs = []
            for file in data_files:
                import json
                with open(file, 'r') as f:
                    data = json.load(f)
                    
                df = pd.DataFrame(data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
                
                if symbols:
                    df = df[df['symbol'].isin(symbols)]
                    
                dfs.append(df)
                
            if not dfs:
                return pd.DataFrame()
                
            # Combine all data
            combined_df = pd.concat(dfs, ignore_index=True)
            combined_df.sort_values('timestamp', inplace=True)
            
            return combined_df
            
        except Exception as e:
            logger.error(f"Failed to load fundamental data: {str(e)}")
            raise BacktestError(f"Failed to load fundamental data: {str(e)}")
            
    def preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess the loaded data for backtesting.
        
        Args:
            data: Raw data DataFrame
            
        Returns:
            Preprocessed DataFrame
        """
        try:
            # Make a copy to avoid modifying original
            df = data.copy()
            
            # Handle missing values
            df.fillna(method='ffill', inplace=True)
            df.fillna(method='bfill', inplace=True)
            
            # Calculate returns
            if 'price' in df.columns:
                df['returns'] = df.groupby('symbol')['price'].pct_change()
                
            # Calculate moving averages
            if 'price' in df.columns:
                df['sma_20'] = df.groupby('symbol')['price'].transform(
                    lambda x: x.rolling(window=20).mean()
                )
                df['sma_50'] = df.groupby('symbol')['price'].transform(
                    lambda x: x.rolling(window=50).mean()
                )
                
            return df
            
        except Exception as e:
            logger.error(f"Failed to preprocess data: {str(e)}")
            raise BacktestError(f"Failed to preprocess data: {str(e)}") 