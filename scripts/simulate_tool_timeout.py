#!/usr/bin/env python3
"""
Simulate Tool Timeout Script

This script introduces artificial delays or raises timeout exceptions
when specific paths or operations are targeted, allowing for testing
of resilience in tool wrappers and fallback logic.
"""

import time
import random
import argparse
import sys
from pathlib import Path
import logging

# --- Configuration ---
DEFAULT_DELAY_SECONDS = 5.0
DEFAULT_TIMEOUT_PROBABILITY = 0.3 # 30% chance of forced timeout

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ToolTimeoutSimulator")

# --- Simulation Logic ---

def simulate_potential_timeout(target_path_str: str, operation: str):
    """
    Introduces a delay and potentially raises a TimeoutError based on configuration.

    Args:
        target_path_str: The file or directory path being operated on.
        operation: A description of the operation (e.g., 'list_dir', 'read_file').
    """
    target_path = Path(target_path_str)
    delay = DEFAULT_DELAY_SECONDS
    timeout_prob = DEFAULT_TIMEOUT_PROBABILITY

    # --- Customization Hooks (Extend as needed) ---
    # Example: Increase delay for specific directories
    if "runtime/agent_comms/agent_mailboxes" in target_path_str:
        delay *= 1.5
        logger.info(f"Increased delay for mailbox path: {target_path_str}")

    # Example: Always timeout reads for a specific problematic file
    if operation == 'read_file' and target_path.name == 'task_backlog.json':
         logger.warning(f"Forcing timeout for critical file read: {target_path_str}")
         raise TimeoutError(f"Simulated forced timeout during '{operation}' on '{target_path_str}'")

    # --- Standard Simulation ---
    logger.info(f"Simulating operation '{operation}' on '{target_path_str}'...")
    logger.info(f"Applying delay of {delay:.2f} seconds...")
    time.sleep(delay)

    if random.random() < timeout_prob:
        logger.error(f"Simulating random timeout exception for '{operation}' on '{target_path_str}' (Prob: {timeout_prob:.2f})")
        raise TimeoutError(f"Simulated random timeout during '{operation}' on '{target_path_str}'")
    else:
        logger.info(f"Operation '{operation}' on '{target_path_str}' completed without simulated timeout.")


# --- Command Line Interface ---

def main():
    parser = argparse.ArgumentParser(description="Simulate tool timeouts for testing resilience.")
    parser.add_argument("target_path", type=str, help="The target file or directory path for the simulated operation.")
    parser.add_argument("operation", type=str, help="Description of the simulated operation (e.g., 'read_file', 'list_dir').")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS, help="Base delay in seconds.")
    parser.add_argument("--prob", type=float, default=DEFAULT_TIMEOUT_PROBABILITY, help="Probability (0.0 to 1.0) of a random timeout.")

    args = parser.parse_args()

    # Update globals from args if provided
    global DEFAULT_DELAY_SECONDS, DEFAULT_TIMEOUT_PROBABILITY
    DEFAULT_DELAY_SECONDS = args.delay
    DEFAULT_TIMEOUT_PROBABILITY = args.prob

    logger.info(f"Starting simulation: Operation='{args.operation}', Target='{args.target_path}', Delay={args.delay}s, TimeoutProb={args.prob}")

    try:
        simulate_potential_timeout(args.target_path, args.operation)
        logger.info("Simulation finished successfully (no timeout triggered).")
        sys.exit(0) # Explicit success exit code
    except TimeoutError as e:
        logger.error(f"Simulation resulted in a TimeoutError: {e}")
        sys.exit(1) # Explicit failure exit code for timeout
    except Exception as e:
        logger.critical(f"Simulation encountered unexpected error: {e}", exc_info=True)
        sys.exit(2) # Different failure code for other errors

if __name__ == "__main__":
    main() 