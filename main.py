# TODO: Content should be copied from main_copy.py

print("--- main.py started ---"); sys.stdout.flush() # Force output early + flush
#!/usr/bin/env python3
"""Dream.OS Main Entry Point"""

import sys
# ... existing imports ...

# Initial basic logging config (will be overridden by setup_logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Use __name__ for module-level logger
sys.stdout.flush() # Flush after initial basicConfig

# ... rest of the file ...

def setup_logging(config: AppConfig):
    """Configures the root logger based on the loaded configuration."""
    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)
    log_format = '%(asctime)s - [%(levelname)s] - %(name)s - %(message)s'

    root_logger = logging.getLogger() # Get root logger
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set level on root logger
    root_logger.setLevel(log_level)

    # Configure console handler (always add)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    console_handler.setLevel(log_level) # Set level on handler too
    root_logger.addHandler(console_handler)

    # Configure file handler if specified
    # ... (file handler code) ...

    # Flush stdout again after setting up the main handler
    sys.stdout.flush()

# ... main function ...

    # Setup logging based on the loaded config
    setup_logging(config)
    logger = logging.getLogger(__name__) # Re-get logger after setup if needed
    sys.stdout.flush() # Flush after calling setup_logging

    logger.info(f"Dream.OS starting in '{config.mode}' mode.")
    sys.stdout.flush() # Flush after first logger.info call

# ... rest of main function ...