"""
Command-line interface for Dream.OS Backtesting Framework.
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
import json

from . import BacktestEngine, MovingAverageCrossover, MeanReversion
from .utils import ValidationError, BacktestError, DataError

logger = logging.getLogger(__name__)

def setup_logging(verbose: bool = False) -> None:
    """
    Set up logging configuration.
    
    Args:
        verbose: Whether to enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Dream.OS Backtesting Framework CLI"
    )
    
    # Required arguments
    parser.add_argument(
        '--data-dir',
        type=Path,
        required=True,
        help='Directory containing market data'
    )
    parser.add_argument(
        '--results-dir',
        type=Path,
        required=True,
        help='Directory to save backtest results'
    )
    parser.add_argument(
        '--strategy',
        choices=['ma_crossover', 'mean_reversion'],
        required=True,
        help='Strategy to use for backtesting'
    )
    parser.add_argument(
        '--start-date',
        type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
        required=True,
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
        required=True,
        help='End date (YYYY-MM-DD)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--initial-capital',
        type=float,
        default=100000.0,
        help='Initial capital for backtesting (default: 100000.0)'
    )
    parser.add_argument(
        '--parameters',
        type=json.loads,
        default='{}',
        help='Strategy parameters as JSON string'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to save results (default: results_dir/backtest_results.json)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()

def create_strategy(strategy_name: str, parameters: dict) -> object:
    """
    Create strategy instance based on name and parameters.
    
    Args:
        strategy_name: Name of the strategy
        parameters: Strategy parameters
        
    Returns:
        Strategy instance
        
    Raises:
        ValueError: If strategy name is invalid
    """
    if strategy_name == 'ma_crossover':
        return MovingAverageCrossover(
            name="MA Crossover",
            parameters=parameters
        )
    elif strategy_name == 'mean_reversion':
        return MeanReversion(
            name="Mean Reversion",
            parameters=parameters
        )
    else:
        raise ValueError(f"Invalid strategy: {strategy_name}")

def main() -> int:
    """
    Main entry point for the CLI.
    
    Returns:
        Exit code
    """
    try:
        # Parse arguments
        args = parse_args()
        
        # Set up logging
        setup_logging(args.verbose)
        
        # Create strategy
        strategy = create_strategy(args.strategy, args.parameters)
        
        # Initialize engine
        engine = BacktestEngine(
            data_dir=args.data_dir,
            results_dir=args.results_dir
        )
        
        # Run backtest
        logger.info("Starting backtest...")
        results = engine.run_backtest(
            strategy=strategy,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_capital=args.initial_capital
        )
        
        # Save results
        output_path = args.output or args.results_dir / "backtest_results.json"
        engine.save_results(results, output_path)
        
        # Print metrics
        print("\nBacktest Results:")
        print("-" * 50)
        print(engine.analyzer.format_metrics(results['metrics']))
        
        logger.info(f"Results saved to {output_path}")
        return 0
        
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return 1
    except BacktestError as e:
        logger.error(f"Backtest error: {str(e)}")
        return 1
    except DataError as e:
        logger.error(f"Data error: {str(e)}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 