"""
Tool to send a structured JSON message into a shared mailbox JSON file.
See: _agent_coordination/onboarding/agent_onboarding_prompt.md
     _agent_coordination/protocols/messaging_format.md (Implicitly)
"""

import argparse
import json
import uuid
import datetime
import sys
import logging
import time
import os
from pathlib import Path
from contextlib import contextmanager

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

LOCK_RETRY_DELAY = 0.1  # seconds
LOCK_TIMEOUT = 5  # seconds

@contextmanager
def file_lock(lock_file_path: Path):
    """Context manager for acquiring and releasing a simple file lock."""
    start_time = time.monotonic()
    while True:
        try:
            # Attempt to create the lock file exclusively
            lock_fd = os.open(lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            # If successful, we have the lock
            logger.debug(f"Acquired lock: {lock_file_path}")
            break
        except FileExistsError:
            # Lock file already exists, wait and retry
            if time.monotonic() - start_time > LOCK_TIMEOUT:
                raise TimeoutError(f"Could not acquire lock on {lock_file_path} within {LOCK_TIMEOUT} seconds.")
            logger.debug(f"Waiting for lock: {lock_file_path}")
            time.sleep(LOCK_RETRY_DELAY)
        except Exception as e:
            raise OSError(f"Error acquiring lock {lock_file_path}: {e}")

    try:
        yield lock_fd # Provide the file descriptor if needed, though often just existence matters
    finally:
        # Release the lock by closing and deleting the file
        try:
            if lock_fd:
                 os.close(lock_fd)
            os.remove(lock_file_path)
            logger.debug(f"Released lock: {lock_file_path}")
        except Exception as e:
            # Log error but don't re-raise during cleanup
            logger.error(f"Error releasing lock {lock_file_path}: {e}")


def send_shared_message(mailbox_file_path: Path, command: str, params_json_str: str, sender: str):
    """Appends a new message to the specified shared mailbox JSON file."""

    lock_file = mailbox_file_path.with_suffix(mailbox_file_path.suffix + '.lock')
    logger.info(f"Attempting to send message to: {mailbox_file_path}")

    # --- Validate Params JSON ---
    try:
        params = json.loads(params_json_str)
        if not isinstance(params, dict):
            raise ValueError("Params JSON must be an object (dictionary).")
        logger.debug(f"Parsed params: {params}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON provided for --params-json: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid params JSON structure: {e}")
        sys.exit(1)

    # --- Construct New Message ---
    message_id = f"msg_{uuid.uuid4()}"
    timestamp = datetime.datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
    new_message = {
        "message_id": message_id,
        "command": command,
        "params": params,
        "sender_agent_id": sender,
        "timestamp_dispatched_utc": timestamp,
        # Optional: Add task_id if relevant context exists
        # "task_id": "task_..."
    }
    logger.debug(f"Constructed message: {new_message}")

    # --- Read, Update, Write with Lock ---
    try:
        with file_lock(lock_file):
            # --- Read existing data ---
            if not mailbox_file_path.is_file():
                logger.error(f"Target mailbox file not found: {mailbox_file_path}")
                # Depending on policy, could create a default structure, but safer to exit
                sys.exit(1)

            try:
                with open(mailbox_file_path, 'r', encoding='utf-8') as f:
                    mailbox_data = json.load(f)
                logger.debug(f"Read existing data from {mailbox_file_path}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode existing JSON in {mailbox_file_path}: {e}")
                sys.exit(1)
            except Exception as e:
                 logger.error(f"Failed to read existing file {mailbox_file_path}: {e}")
                 sys.exit(1)

            # --- Validate structure and append ---
            if not isinstance(mailbox_data, dict):
                 logger.error(f"Mailbox file {mailbox_file_path} does not contain a JSON object.")
                 sys.exit(1)

            messages_list = mailbox_data.get("messages")
            if messages_list is None:
                # Initialize if missing (adjust based on strictness required)
                logger.warning(f"'messages' key missing in {mailbox_file_path}, initializing as empty list.")
                mailbox_data["messages"] = []
            elif not isinstance(messages_list, list):
                 logger.error(f"'messages' key in {mailbox_file_path} is not a list.")
                 sys.exit(1)

            mailbox_data["messages"].append(new_message)
            logger.debug(f"Appended new message. Total messages: {len(mailbox_data['messages'])}")

            # --- Write updated data ---
            try:
                # Write atomically using temp file + replace
                temp_file_path = mailbox_file_path.with_suffix(f'.{uuid.uuid4()}.tmp')
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    json.dump(mailbox_data, f, indent=2) # Use indent for readability
                os.replace(temp_file_path, mailbox_file_path)
                logger.info(f"Successfully wrote updated data to {mailbox_file_path}")
            except Exception as e:
                logger.error(f"Failed to write updated file {mailbox_file_path}: {e}")
                # Attempt to clean up temp file
                if 'temp_file_path' in locals() and temp_file_path.exists():
                    try: temp_file_path.unlink()
                    except: pass
                sys.exit(1)

    except TimeoutError as e:
         logger.error(f"Lock acquisition failed: {e}")
         sys.exit(1)
    except OSError as e:
         logger.error(f"File or lock operation error: {e}")
         sys.exit(1)
    except Exception as e:
         logger.error(f"An unexpected error occurred: {e}", exc_info=True)
         sys.exit(1)

    # Implicit success if no exit occurred
    logger.info(f"Message {message_id} successfully sent.")


if __name__ == "__main__":
    # print("DEBUG: Script execution started.", file=sys.stderr) # Remove debug print
    # Assume CWD is project root if run directly
    default_mailbox_dir = Path.cwd() / "_agent_coordination" / "shared_mailboxes"

    parser = argparse.ArgumentParser(
        description="Send a message payload to a specific shared mailbox JSON file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--mailbox-file",
        required=True,
        help=f"Path to the target mailbox JSON file (e.g., '{default_mailbox_dir / 'mailbox_1.json'}')."
    )
    parser.add_argument(
        "--command",
        required=True,
        help="The command string for the message payload."
    )
    parser.add_argument(
        "--params-json",
        required=True,
        help="JSON object string for the command parameters (e.g., '{\"target_file\": \"src/main.py\"}')."
    )
    parser.add_argument(
        "--sender",
        default="SupervisorTool",
        help="Identifier for the sender of this message."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose DEBUG logging."
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")

    target_file = Path(args.mailbox_file).resolve() # Resolve to absolute path

    send_shared_message(
        mailbox_file_path=target_file,
        command=args.command,
        params_json_str=args.params_json,
        sender=args.sender
    ) 
