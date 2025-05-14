import json
import logging
import os
import shutil
import time
from pathlib import Path
from datetime import datetime

# Assuming AutonomyEngine is in runtime.autonomy.engine
# Adjust the import path if AutonomyEngine is located elsewhere
from runtime.autonomy.engine import AutonomyEngine, Message

# Configuration
BRIDGE_INBOX_DIR = Path("runtime/bridge/inbox")
BRIDGE_PROCESSED_DIR = Path("runtime/bridge/processed")
BRIDGE_ERROR_DIR = Path("runtime/bridge/error") # For messages that can\'t be processed
LOG_FILE = Path("runtime/logs/mock_bridge_loop.log")
POLL_INTERVAL_SECONDS = 5 # Check for new messages every 5 seconds
DEFAULT_TARGET_AGENT_ID = "Agent-1" # Fallback agent if not specified in message

# Setup logging
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler() # Also print to console
    ]
)
logger = logging.getLogger(__name__)

def ensure_directories():
    """Create necessary directories if they don\'t exist."""
    BRIDGE_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    BRIDGE_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    BRIDGE_ERROR_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured bridge directories exist: {BRIDGE_INBOX_DIR}, {BRIDGE_PROCESSED_DIR}, {BRIDGE_ERROR_DIR}")

def process_message_file(message_file_path: Path, engine: AutonomyEngine) -> bool:
    """
    Processes a single message file from the bridge inbox.
    Reads the JSON, attempts to send it via AutonomyEngine,
    and moves the file to processed or error directory.
    """
    try:
        with open(message_file_path, 'r') as f:
            message_data = json.load(f)
        logger.info(f"Read message file: {message_file_path.name} with content: {message_data}")

        # Validate basic message structure (can be expanded)
        if not isinstance(message_data, dict):
            logger.error(f"Invalid message format (not a dict) in {message_file_path.name}. Moving to error.")
            shutil.move(str(message_file_path), str(BRIDGE_ERROR_DIR / message_file_path.name))
            return False

        # Determine target agent
        # User messages might specify 'agent_id' or 'target_agent' or use a default
        target_agent = message_data.get("target_agent_id") or \
                       message_data.get("agent_id") or \
                       message_data.get("recipient_agent_id") or \
                       DEFAULT_TARGET_AGENT_ID
        
        # Ensure the core message content for AutonomyEngine is properly structured
        # AutonomyEngine expects a dict, and our Message dataclass handles internal fields.
        # The message_data itself could be the dict for send_message.
        # Let\'s assume the JSON file contains the full message payload for AutonomyEngine.
        
        # Example: if message_data is already like {"type": "some_type", "content": "...", ...}
        # then it can be passed directly.

        if "type" not in message_data or "content" not in message_data:
            logger.warning(f"Message {message_file_path.name} missing 'type' or 'content'. Attempting to send anyway, but this might fail engine validation.")

        # Add a timestamp if not present, as engine might expect it or log it
        if "timestamp" not in message_data:
            message_data["timestamp"] = datetime.utcnow().isoformat() + "Z"
            logger.info(f"Added timestamp to message {message_file_path.name}")

        logger.info(f"Attempting to send message from {message_file_path.name} to agent: {target_agent}")
        
        # Relay message using AutonomyEngine
        # The AutonomyEngine.send_message expects agent_id and the message dictionary.
        if engine.send_message(target_agent, message_data):
            logger.info(f"Successfully relayed message from {message_file_path.name} to {target_agent}.")
            shutil.move(str(message_file_path), str(BRIDGE_PROCESSED_DIR / message_file_path.name))
            logger.info(f"Moved {message_file_path.name} to {BRIDGE_PROCESSED_DIR}")
            return True
        else:
            logger.error(f"AutonomyEngine failed to send message from {message_file_path.name} to {target_agent}.")
            shutil.move(str(message_file_path), str(BRIDGE_ERROR_DIR / message_file_path.name))
            return False

    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {message_file_path.name}. Moving to error.")
        shutil.move(str(message_file_path), str(BRIDGE_ERROR_DIR / message_file_path.name))
        return False
    except Exception as e:
        logger.error(f"Unexpected error processing {message_file_path.name}: {e}", exc_info=True)
        try:
            shutil.move(str(message_file_path), str(BRIDGE_ERROR_DIR / message_file_path.name))
        except Exception as move_e:
            logger.error(f"Could not move {message_file_path.name} to error directory: {move_e}")
        return False

def main_loop():
    """
    Main operational loop for the mock bridge.
    Monitors inbox, processes messages, and relays them.
    """
    logger.info("Mock Bridge Loop started. Monitoring directory: %s", BRIDGE_INBOX_DIR)
    ensure_directories()
    
    try:
        engine = AutonomyEngine() # Initialize once
        logger.info("AutonomyEngine initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize AutonomyEngine: {e}. Bridge loop cannot start.", exc_info=True)
        return

    try:
        while True:
            logger.debug(f"Scanning {BRIDGE_INBOX_DIR} for new messages...")
            message_files = sorted(list(BRIDGE_INBOX_DIR.glob("*.json"))) # Process in order

            if not message_files:
                logger.debug("No new messages found.")
            else:
                logger.info(f"Found {len(message_files)} new message(s) in bridge inbox.")
                for message_file in message_files:
                    logger.info(f"Processing message: {message_file.name}")
                    process_message_file(message_file, engine)
            
            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info("Mock Bridge Loop shutting down due to KeyboardInterrupt.")
    except Exception as e:
        logger.error(f"Mock Bridge Loop encountered an unhandled exception: {e}", exc_info=True)
    finally:
        logger.info("Mock Bridge Loop stopped.")

if __name__ == "__main__":
    main_loop() 