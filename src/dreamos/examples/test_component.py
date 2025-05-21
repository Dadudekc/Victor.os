#!/usr/bin/env python3
"""
Dream.OS Test Component

A simple test component for testing the Dream.OS Launcher's process management.
This component will:
1. Print information about itself
2. Count up to a specified number, printing each count
3. Respect signals for graceful shutdown
"""

import os
import sys
import time
import signal
import argparse
import logging
from datetime import datetime
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dreamos.examples.test_component")

# Flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    """Handle signals for graceful shutdown."""
    global running
    signal_name = signal.Signals(sig).name
    logger.info(f"Received signal {signal_name} ({sig}), initiating graceful shutdown")
    running = False

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Dream.OS Test Component")
    parser.add_argument("--count", type=int, default=60, 
                      help="Number to count up to (default: 60)")
    parser.add_argument("--interval", type=float, default=1.0, 
                      help="Interval between counts in seconds (default: 1.0)")
    parser.add_argument("--checkpoint", action="store_true", 
                      help="Enable checkpoint support")
    return parser.parse_args()

def save_checkpoint(count, max_count):
    """Save a checkpoint."""
    checkpoint_id = f"test_component_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    checkpoint_data = {
        "checkpoint_id": checkpoint_id,
        "timestamp": datetime.now().isoformat(),
        "count": count,
        "max_count": max_count,
        "progress_percent": (count / max_count) * 100
    }
    
    # Save to a checkpoint file
    try:
        checkpoint_dir = os.path.join("runtime", "checkpoints")
        os.makedirs(checkpoint_dir, exist_ok=True)
        checkpoint_path = os.path.join(checkpoint_dir, f"{checkpoint_id}.json")
        
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
            
        logger.info(f"Saved checkpoint to {checkpoint_path}")
    except Exception as e:
        logger.error(f"Error saving checkpoint: {e}")

def main():
    """Main entry point."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse arguments
    args = parse_args()
    
    # Print component information
    logger.info("Starting Dream.OS Test Component")
    logger.info(f"Process ID: {os.getpid()}")
    logger.info(f"Working Directory: {os.getcwd()}")
    logger.info(f"Python Executable: {sys.executable}")
    logger.info(f"Python Version: {sys.version}")
    logger.info(f"Arguments: {args}")
    logger.info(f"Environment Variables: {[k for k, v in os.environ.items() if k.startswith('DREAMOS_')]}")
    
    # Count up to specified number
    count = 0
    while running and count < args.count:
        count += 1
        progress = (count / args.count) * 100
        logger.info(f"Count: {count}/{args.count} ({progress:.1f}%)")
        
        # Save checkpoint if enabled (every 10%)
        if args.checkpoint and count % max(1, args.count // 10) == 0:
            save_checkpoint(count, args.count)
            
        # Sleep for interval
        start_time = time.time()
        while running and (time.time() - start_time) < args.interval:
            time.sleep(0.1)
            
    # Final checkpoint if enabled
    if args.checkpoint and running:
        save_checkpoint(count, args.count)
        
    # Print completion
    if running:
        logger.info("Test component completed successfully")
    else:
        logger.info("Test component exiting due to signal")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 