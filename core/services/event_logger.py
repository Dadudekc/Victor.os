import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

# Setup logger for this module
logger = logging.getLogger(__name__)

# TODO: Make the log file path configurable (e.g., via environment variable, config file, or class init)
DEFAULT_LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', "runtime")) # Default to <project_root>/runtime
DEFAULT_LOG_FILENAME = "structured_events.jsonl"

def get_log_filepath(log_dir: Optional[str] = None, log_filename: Optional[str] = None) -> str:
    """Determines the target log file path."""
    target_dir = log_dir or DEFAULT_LOG_DIR
    target_filename = log_filename or DEFAULT_LOG_FILENAME
    return os.path.join(target_dir, target_filename)

def log_structured_event(event_type: str, data: Dict[str, Any], source: str, log_filepath: Optional[str] = None) -> bool:
    """
    Logs a structured event to a JSONL file.

    Args:
        event_type (str): Type of event being logged (e.g., 'TASK_STARTED', 'AGENT_ERROR').
        data (dict): Event data/payload.
        source (str): Source system/component generating the event (e.g., 'AgentX', 'LLMBridge').
        log_filepath (Optional[str]): Full path to the log file. If None, uses default.

    Returns:
        bool: True if logging succeeded, False otherwise.
    """
    target_file = log_filepath or get_log_filepath()
    try:
        # Ensure log directory exists
        os.makedirs(os.path.dirname(target_file), exist_ok=True)

        event = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "source": source,
            "data": data
        }

        with open(target_file, "a", encoding='utf-8') as f:
            json.dump(event, f)
            f.write("\n")
        logger.debug(f"Logged event '{event_type}' from '{source}' to {os.path.basename(target_file)}")
        return True

    except Exception as e:
        logger.error(f"Failed to log event to {target_file}: {e}", exc_info=True)
        return False

def get_structured_events(event_type: Optional[str] = None, 
                          source: Optional[str] = None, 
                          limit: int = 100, 
                          log_filepath: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves structured events from the JSONL log file, with optional filtering.

    Args:
        event_type (Optional[str]): Filter by event type.
        source (Optional[str]): Filter by source.
        limit (int): Maximum number of events to return (most recent first).
        log_filepath (Optional[str]): Full path to the log file. If None, uses default.

    Returns:
        List[Dict[str, Any]]: A list of matching event dictionaries.
    """
    target_file = log_filepath or get_log_filepath()
    try:
        if not os.path.exists(target_file):
            logger.warning(f"Event log file not found: {target_file}")
            return []

        events = []
        # Read lines efficiently, potentially reversing if needed for 'most recent'
        # For simplicity now, reading all and filtering
        # TODO: Optimize for large files if needed (e.g., read last N lines)
        with open(target_file, "r", encoding='utf-8') as f:
            lines = f.readlines()
        
        # Iterate backwards to get most recent first up to the limit
        for line in reversed(lines):
            if len(events) >= limit:
                 break
            try:
                event = json.loads(line.strip())
                type_match = not event_type or event.get("type") == event_type
                source_match = not source or event.get("source") == source
                
                if type_match and source_match:
                    events.append(event)
            except json.JSONDecodeError:
                logger.warning(f"Skipping malformed line in {target_file}: {line.strip()[:100]}...")
                continue
            except Exception as e:
                 logger.warning(f"Error processing line in {target_file}: {e} - Line: {line.strip()[:100]}...")
                 continue
        
        # Events are currently newest-to-oldest due to reversed read
        logger.debug(f"Retrieved {len(events)} events matching criteria from {os.path.basename(target_file)}.")
        return events

    except Exception as e:
        logger.error(f"Failed to retrieve events from {target_file}: {e}", exc_info=True)
        return []

# Example Usage (can be run directly: python -m core.services.event_logger)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Running Event Logger example...")

    # Use a temporary log file for the example
    temp_log_dir = os.path.join(DEFAULT_LOG_DIR, "temp_test")
    temp_log_file = get_log_filepath(log_dir=temp_log_dir, log_filename="test_events.jsonl")
    print(f"Using temporary log file: {temp_log_file}")

    # Ensure clean start for example
    if os.path.exists(temp_log_file):
        os.remove(temp_log_file)

    # Log some events
    log_structured_event("TEST_START", {"param": 1}, "ExampleRunner", log_filepath=temp_log_file)
    log_structured_event("TEST_STEP", {"step": "A"}, "ExampleRunner", log_filepath=temp_log_file)
    log_structured_event("TEST_ERROR", {"code": 123}, "ComponentX", log_filepath=temp_log_file)
    log_structured_event("TEST_STEP", {"step": "B"}, "ExampleRunner", log_filepath=temp_log_file)
    log_structured_event("TEST_END", {"status": "success"}, "ExampleRunner", log_filepath=temp_log_file)

    print("\n--- Retrieving all events --- (Newest first)")
    all_events = get_structured_events(limit=10, log_filepath=temp_log_file)
    print(json.dumps(all_events, indent=2))

    print("\n--- Retrieving TEST_STEP events --- (Newest first)")
    step_events = get_structured_events(event_type="TEST_STEP", limit=10, log_filepath=temp_log_file)
    print(json.dumps(step_events, indent=2))

    print("\n--- Retrieving events from ComponentX --- (Newest first)")
    comp_x_events = get_structured_events(source="ComponentX", limit=10, log_filepath=temp_log_file)
    print(json.dumps(comp_x_events, indent=2))

    # Clean up
    # try:
    #     os.remove(temp_log_file)
    #     os.rmdir(temp_log_dir)
    #     print(f"Cleaned up temporary log file and directory.")
    # except OSError as e:
    #      print(f"Error cleaning up: {e}")

    logger.info("Event Logger example finished.") 