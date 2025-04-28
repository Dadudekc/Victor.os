# TODO: Content should be copied from main_copy.py

print("--- main.py started ---"); sys.stdout.flush() # Force output early + flush
#!/usr/bin/env python3
"""Dream.OS Main Entry Point"""

import sys
import logging
# Placeholder for AppConfig
class AppConfig: pass 
# ... existing imports ...
# EDIT START: Add ConversationLogger import and initialization
from ..coordination.agent_bus import AgentBus # Assuming AgentBus is available via singleton
from ..hooks.conversation_logger import ConversationLogger
# EDIT END

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

def main(): # Assuming a main function exists or similar entry point
    print("--- main() started ---"); sys.stdout.flush()
    # Load configuration (replace with actual config loading)
    config = AppConfig()
    # ... (config loading logic) ...

    # Setup logging based on the loaded config
    setup_logging(config)
    logger = logging.getLogger(__name__) # Re-get logger after setup if needed
    sys.stdout.flush() # Flush after calling setup_logging

    logger.info(f"Dream.OS starting...") # Simplified message
    sys.stdout.flush() # Flush after first logger.info call

    # EDIT START: Initialize AgentBus and ConversationLogger
    try:
        agent_bus = AgentBus() # Get singleton instance
        logger.info("AgentBus obtained."); sys.stdout.flush()

        conversation_logger = ConversationLogger(agent_bus=agent_bus)
        logger.info("ConversationLogger initialized."); sys.stdout.flush()

        conversation_logger.register_event_handlers()
        logger.info("ConversationLogger handlers registered."); sys.stdout.flush()

    except Exception as e:
        logger.critical(f"Failed to initialize AgentBus or ConversationLogger: {e}", exc_info=True)
        sys.stdout.flush()
        sys.exit(1) # Exit if core components fail
    # EDIT END

    # ... (rest of application startup logic, e.g., starting services, UI) ...
    logger.info("Dream.OS initialization complete."); sys.stdout.flush()

    # Keep alive logic or start main loop
    try:
        # Replace with actual application run logic
        print("Application running... Press Ctrl+C to exit.")
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")
    finally:
        # EDIT START: Ensure logger is closed on shutdown
        if 'conversation_logger' in locals() and conversation_logger:
            logger.info("Closing ConversationLogger database connection...")
            conversation_logger.close()
        # EDIT END
        logger.info("Dream.OS shutdown complete.")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
