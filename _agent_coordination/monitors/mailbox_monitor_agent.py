# _agent_coordination/monitors/mailbox_monitor_agent.py

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import os
import sys
# import fcntl # fcntl is Unix-specific
import portalocker # Use portalocker for cross-platform file locking
from typing import List, Dict, Optional # Add typing
import argparse

# --- Path Setup ---
# Assumes this file is in _agent_coordination/monitors/
SCRIPT_DIR = Path(__file__).parent
AGENT_COORDINATION_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = AGENT_COORDINATION_DIR.parent

# Add project root to sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# ------------------

# Use the central logger setup from _agent_coordination
try:
    from _agent_coordination.core.utils.logging import get_logger
    logger = get_logger(__name__, component="MailboxMonitorAgent")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("MailboxMonitorAgent [fallback]")
    logger.warning("Could not import central logger. Using basic config.")

# --- Configuration ---
AGENT_ID = "agent_mailbox_monitor"
# Monitor all agent mailboxes in shared_mailboxes
SHARED_MAILBOX_DIR = AGENT_COORDINATION_DIR / "shared_mailboxes"
MAILBOX_DIR = SHARED_MAILBOX_DIR
# Remove single-file supervisor mailbox; process all *.json files in MAILBOX_DIR
TASK_LIST_FILE = PROJECT_ROOT / "runtime" / "task_list.json"
CHECK_INTERVAL_SECONDS = 5

# Ensure directories exist on import
MAILBOX_DIR.mkdir(parents=True, exist_ok=True)
TASK_LIST_FILE.parent.mkdir(parents=True, exist_ok=True)

# Ensure TASK_LIST_FILE exists and is a JSON list on import
try:
    if not TASK_LIST_FILE.exists():
        TASK_LIST_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TASK_LIST_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
except Exception as e:
    logger.error(f"Error initializing task list file {TASK_LIST_FILE}: {e}", exc_info=True)

# --- Cross-Platform File Locking Utilities (using portalocker) ---
def acquire_lock(file_path, lock_flags=portalocker.LOCK_EX | portalocker.LOCK_NB):
    """Acquires a lock on the file using portalocker with specified flags."""
    try:
        # Open file in read/write mode, create if not exists
        mode = 'r+' if os.path.exists(file_path) else 'w+'
        lock_file = open(file_path, mode)
        portalocker.lock(lock_file, lock_flags)
        logger.debug(f"Acquired lock for {file_path} with flags {lock_flags}")
        return lock_file
    except portalocker.exceptions.LockException:
        logger.warning(f"Could not acquire lock for {file_path}, already locked.")
        try:
            lock_file.close()
        except:
            pass
        return None
    except Exception as e:
        logger.error(f"Error acquiring lock for {file_path}: {e}", exc_info=True)
        try:
            lock_file.close()
        except:
            pass
        return None

def release_lock(lock_file):
    """Releases the lock and closes the file handle."""
    if lock_file:
        try:
            portalocker.unlock(lock_file)
            lock_file.close()
            logger.debug(f"Released lock for {lock_file.name}")
        except Exception as e:
            logger.error(f"Error releasing lock for {lock_file.name}: {e}", exc_info=True)
            # Ensure file is closed even if unlock fails
            if not lock_file.closed:
                lock_file.close()

# --- Mailbox Processing Logic ---
class MailboxMonitorAgent:

    def __init__(self):
        self.running = False
        logger.info(f"[{AGENT_ID}] Initialized.")

    def _read_mailbox_file(self, mailbox_file: Path) -> List[Dict]:
        """Safely reads the specified mailbox file using portalocker."""
        if not mailbox_file.exists():
            return []
        
        # Use shared lock for reading to allow concurrent readers
        lock_file = acquire_lock(mailbox_file, portalocker.LOCK_SH | portalocker.LOCK_NB)
        if not lock_file:
             return [] # Could not get lock, try again later

        try:
            # Lock acquired, now read the actual content
            # Re-open in read mode (or seek to beginning if needed)
            with open(mailbox_file, 'r', encoding='utf-8') as f:
                try:
                    content = f.read()
                except PermissionError:
                    logger.debug(f"Permission denied reading mailbox file {mailbox_file}, skipping.")
                    return []
                if not content.strip():
                    return []
                mailbox = json.loads(content)
                return mailbox if isinstance(mailbox, list) else []
        except json.JSONDecodeError:
            logger.error(f"Mailbox file {mailbox_file} contains invalid JSON.")
            return []
        except Exception as e:
            logger.error(f"Error reading mailbox file {mailbox_file}: {e}", exc_info=True)
            return []
        finally:
            release_lock(lock_file)

    def _write_mailbox(self, mailbox_file: Path, mailbox_data: List[Dict]) -> bool:
        """Safely writes the updated mailbox data back to the file using portalocker."""
        lock_file = acquire_lock(mailbox_file)
        if not lock_file:
            return False

        try:
            # Lock acquired, now write the content (this will overwrite)
            with open(mailbox_file, 'w', encoding='utf-8') as f:
                # Need to seek to beginning if opened in append mode before locking
                # f.seek(0)
                # f.truncate() # Clear file before writing new content
                json.dump(mailbox_data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error writing mailbox file {mailbox_file}: {e}", exc_info=True)
            return False
        finally:
            release_lock(lock_file)

    def _add_task_to_list(self, task_data: Dict) -> bool:
        """Safely adds a new task to the main task list file using portalocker."""
        lock_file = acquire_lock(TASK_LIST_FILE)
        if not lock_file:
            return False
        
        task_list = [] # Initialize task_list
        try:
            # Re-open in read mode to get current content
            if TASK_LIST_FILE.exists() and TASK_LIST_FILE.stat().st_size > 0:
                 with open(TASK_LIST_FILE, 'r', encoding='utf-8') as f:
                    content = f.read()
                    task_list = json.loads(content) if content.strip() else []
                    if not isinstance(task_list, list):
                        logger.error(f"Task list file {TASK_LIST_FILE} is not a valid JSON list. Overwriting.")
                        task_list = []
            else:
                task_list = [] # Ensure it's a list if file empty or doesn't exist

            # Add the new task
            task_list.append(task_data)

            # Re-open in write mode to save
            with open(TASK_LIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(task_list, f, indent=2)
                
            logger.info(f"Added task {task_data.get('task_id')} to {TASK_LIST_FILE}.")
            return True
        except json.JSONDecodeError:
            logger.error(f"Task list file {TASK_LIST_FILE} contains invalid JSON. Cannot add task.")
            return False
        except Exception as e:
            logger.error(f"Error updating task list file {TASK_LIST_FILE}: {e}", exc_info=True)
            return False
        finally:
            release_lock(lock_file)

    def _get_mailbox_files(self) -> List[Path]:
        """Returns a list of all JSON mailbox files in the mailbox directory."""
        return sorted(MAILBOX_DIR.glob('*.json'))

    def _process_unread_messages(self):
        """Processes unread messages across all agent mailboxes and enqueues tasks."""
        for mailbox_file in self._get_mailbox_files():
            mailbox = self._read_mailbox_file(mailbox_file)
            if not mailbox:
                continue
            updated = False
            for message in mailbox:
                if isinstance(message, dict) and message.get('status') == 'unread':
                    # process message as before, then mark and write back per mailbox_file
                    task_data = self._transform_message_to_task(message)
                    if task_data and self._add_task_to_list(task_data):
                        message['status'] = 'processed'
                        updated = True
                    else:
                        message['status'] = 'failed'
            if updated:
                self._write_mailbox(mailbox_file, mailbox)

    def _transform_message_to_task(self, message: Dict) -> Optional[Dict]:
        """Transforms a mailbox message into a task list entry dictionary."""
        try:
            payload = message.get("payload", {})
            task_type = payload.get("task_type")
            params = payload.get("params", {})
            target_agent = message.get("target_agent")
            message_id = message.get("message_id", uuid.uuid4().hex[:8]) # Fallback ID

            if not task_type:
                logger.warning(f"Message {message_id} missing 'task_type' in payload.")
                return None

            # Generate task_id based on message
            # Ensure task_type part is safe for filename/id use
            safe_task_type = "".join(c if c.isalnum() else '_' for c in task_type)[:15]
            task_id = f"mailbox_{safe_task_type}_{message_id[:8]}"

            task_entry = {
                "task_id": task_id,
                "task_type": task_type,
                "status": "PENDING",
                "params": params,
                "target_agent": target_agent, # Can be None/"broadcast" if dispatcher handles routing
                "source": "supervisor_mailbox",
                "source_message_id": message.get("message_id"),
                "timestamp_created": datetime.now(timezone.utc).isoformat() + "Z",
                "origin_sender": message.get("sender")
            }
            return task_entry
        except Exception as e:
            logger.error(f"Error transforming message {message.get('message_id')} to task: {e}", exc_info=True)
            return None

    async def run(self):
        """Main loop for the MailboxMonitorAgent."""
        self.running = True
        logger.info(f"[{AGENT_ID}] Starting run loop (checking every {CHECK_INTERVAL_SECONDS}s)...")
        while self.running:
            try:
                logger.debug(f"Checking {MAILBOX_DIR}...")
                self._process_unread_messages()
            except Exception as e:
                logger.error(f"[{AGENT_ID}] Error in main loop: {e}", exc_info=True)
            
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        logger.info(f"[{AGENT_ID}] Run loop stopped.")

    def stop(self):
        """Stops the agent's run loop."""
        logger.info(f"[{AGENT_ID}] Received stop signal.")
        self.running = False

# --- Example Usage --- 
async def main():
    # Example: Add a dummy message to the mailbox for testing
    MAILBOX_DIR.mkdir(exist_ok=True)
    test_message = {
        "message_id": f"test_{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "sender": "test_script",
        "target_agent": "DummyAgent",
        "message_type": "directive",
        "payload": {
            "task_type": "test_task",
            "params": {"data": "example payload"}
        },
        "status": "unread"
    }
    # Write initial mailbox if it doesn't exist or is empty
    # Use locking here as well for safety in test setup
    lock = acquire_lock(MAILBOX_DIR / "test_message.json")
    mailbox_content = []
    try:
        if lock:
            if MAILBOX_DIR.exists() and MAILBOX_DIR.stat().st_size > 0:
                 try:
                      with open(MAILBOX_DIR / "test_message.json", 'r') as f:
                           mailbox_content = json.load(f)
                           if not isinstance(mailbox_content, list):
                                mailbox_content = []
                 except json.JSONDecodeError:
                      mailbox_content = [] # Start fresh if corrupted
            
            # Check if test message already exists (simple check)
            if not any(m.get("message_id") == test_message["message_id"] for m in mailbox_content):
                mailbox_content.append(test_message)
                with open(MAILBOX_DIR / "test_message.json", 'w') as f:
                    json.dump(mailbox_content, f, indent=2)
                logger.info(f"Added/updated test message in mailbox: {MAILBOX_DIR / 'test_message.json'}")
            else:
                logger.info("Test message already exists in mailbox.")
    finally:
         if lock:
              release_lock(lock)

    agent = MailboxMonitorAgent()
    try:
        await agent.run()
    except KeyboardInterrupt:
        agent.stop()
    finally:
        agent.stop() # Ensure stop is called

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mailbox Monitor Agent CLI")
    parser.add_argument('--once', action='store_true', help='Process all mailboxes once and exit')
    args = parser.parse_args()
    print(f"Mailbox Monitor Agent starting. Mailbox dir: {MAILBOX_DIR}")
    if args.once:
        # Single-run mode for testing
        agent = MailboxMonitorAgent()
        agent._process_unread_messages()
        print("Processed mailboxes once and exiting.")
        sys.exit(0)
    # Continuous run mode
    print(f"Running continuously (interval: {CHECK_INTERVAL_SECONDS}s). Press Ctrl+C to stop.")
    print(f"Monitoring mailbox: {MAILBOX_DIR}")
    print(f"Adding tasks to: {TASK_LIST_FILE}")
    try:
        import portalocker  # Ensure locking available
        asyncio.run(main())
    except ImportError:
        print("\nPlease install portalocker: pip install portalocker")
    except KeyboardInterrupt:
        print("\nMailbox Monitor Agent stopped by user.") 