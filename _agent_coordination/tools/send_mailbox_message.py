"""
Tool to send a structured JSON message to a specified agent's mailbox.
See: _agent_coordination/onboarding/TOOLS_GUIDE.md
"""

import argparse
import json
import uuid
import datetime
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def send_message(recipient, payload_json_str, sender, mailbox_root_str):
    """Validates inputs, determines paths, creates message, and writes to file."""
    
    # --- Validate Payload --- #
    try:
        payload = json.loads(payload_json_str)
        if not isinstance(payload, dict):
             raise ValueError("Payload must be a JSON object.")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload provided: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid JSON payload structure: {e}")
        sys.exit(1)
        
    if not recipient:
         logger.error("Recipient agent name is required (--recipient).")
         sys.exit(1)

    # --- Determine Mailbox Root Path --- #
    try:
        if mailbox_root_str:
            mailbox_root = Path(mailbox_root_str).resolve()
        else:
            # Default: ./mailboxes relative to current working directory (assumed project root)
            mailbox_root = Path.cwd() / 'mailboxes'
            logger.info(f"No --mailbox-root specified, defaulting to: {mailbox_root}")
            
        if not mailbox_root.exists():
             logger.warning(f"Mailbox root directory does not exist: {mailbox_root}. Attempting to create.")
             # Attempt creation - might fail due to permissions
             # mailbox_root.mkdir(parents=True, exist_ok=True)
             # Let inbox creation handle it, log warning here.
        elif not mailbox_root.is_dir():
             logger.error(f"Specified mailbox root path is not a directory: {mailbox_root}")
             sys.exit(1)
             
        recipient_inbox = mailbox_root / recipient / 'inbox'

    except Exception as e:
        logger.error(f"Error resolving mailbox paths: {e}", exc_info=True)
        sys.exit(1)

    # --- Create Message --- #
    message_id = f"msg_{uuid.uuid4()}"
    timestamp = datetime.datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
    
    full_message = {
        "message_id": message_id,
        "sender_agent_id": sender,
        "timestamp_dispatched": timestamp,
        **payload # Merge validated payload dict
    }

    # --- Write File --- #
    try:
        # Ensure the specific inbox directory exists
        recipient_inbox.mkdir(parents=True, exist_ok=True)
        
        message_file = recipient_inbox / f"{message_id}.json"
        
        # Write atomically if possible (rename is generally atomic)
        temp_file_path = message_file.with_suffix(f'.{uuid.uuid4()}.tmp')
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(full_message, f, indent=2)
        temp_file_path.rename(message_file)
        
        logger.info(f"Success: Message '{message_id}' written to {message_file}")
        # No explicit exit(0) needed, indicates success by default

    except OSError as e:
         logger.error(f"OS error writing message file {message_file}: {e}")
         sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error writing message file {message_file}: {e}", exc_info=True)
        # Clean up temp file if it exists
        if 'temp_file_path' in locals() and temp_file_path.exists():
             try: temp_file_path.unlink() 
             except: pass
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send JSON message to an agent's mailbox.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--recipient", required=True, help="Name of the target agent.")
    parser.add_argument("--payload-json", required=True, help="JSON string payload (e.g., '{"command":"test"}').")
    parser.add_argument("--sender", default="UnknownSender", help="Name of the sending agent.")
    parser.add_argument("--mailbox-root", help="Path to the root mailboxes/ directory (defaults to ./mailboxes).", default=None)
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")

    # Call the main function with parsed arguments
    send_message(
        recipient=args.recipient,
        payload_json_str=args.payload_json,
        sender=args.sender,
        mailbox_root_str=args.mailbox_root
    ) 