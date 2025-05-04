# src/dreamos/tools/thea_relay_agent.py

import asyncio  # Import asyncio for sleep
import json
import logging  # Import logging
import re  # Import re for regex validation
import shutil
import sys  # Added for sys.modules check
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional  # Added type hinting

from dreamos.core.comms.mailbox_utils import write_mailbox_message

# Correct import path
from pydantic import (  # Import Pydantic
    BaseModel,
    ValidationError,
    field_validator,
)

# Attempt to import BaseAgent - Path needs verification
try:
    from dreamos.core.coordination.base_agent import BaseAgent
except ImportError:
    print("[TheaRelayAgent ERROR] Failed to import BaseAgent. Agent cannot run.")

    # Define a dummy BaseAgent if the real one can't be imported
    class BaseAgent:
        def __init__(self, agent_id="TheaRelayAgent_Dummy", log_level=logging.INFO):
            self.agent_id = agent_id
            self.log = logging.getLogger(agent_id)
            self.log.setLevel(log_level)
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            if not self.log.handlers:
                self.log.addHandler(handler)
            self.log.warning("Using Dummy BaseAgent implementation.")

        async def run(self):
            self.log.error("Dummy BaseAgent cannot run.")


# Attempt to import mailbox utility
try:
    from dreamos.agents.utils.agent_utils import write_mailbox_message
except ImportError:
    logging.warning(
        "[TheaRelayAgent WARNING] Could not import write_mailbox_message. Using dummy implementation."  # noqa: E501
    )

    def write_mailbox_message(path: Path, content: Dict[str, Any]):
        logging.info(f"[TheaRelayAgent DUMMY WRITE] Would write to {path}")
        logging.debug(f"[TheaRelayAgent DUMMY CONTENT] {json.dumps(content)}")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2)
        except Exception as e:
            logging.error(
                f"[TheaRelayAgent DUMMY WRITE] Error writing dummy file {path}: {e}"
            )
            raise  # Re-raise exception for dummy implementation


# --- Configuration ---
# Ideally, load from a config file or agent initialization parameters
RESPONSE_DIR = Path("runtime/thea_responses")
ARCHIVE_DIR = RESPONSE_DIR / "archive"
ERROR_DIR = RESPONSE_DIR / "error"  # Added directory for error files
MAILBOX_ROOT_DIR = Path("runtime/agent_comms/agent_mailboxes")
POLLING_INTERVAL_SECONDS = 5  # How often to check the directory


# --- Pydantic Schema for Validation (DEFINE-THEA-MESSAGE-SCHEMA-001) ---
class TheaMessage(BaseModel):
    recipient_agent_id: str
    context_id: Optional[str] = None  # Allow context_id to be optional
    payload: Dict[str, Any]  # Example: Assume a generic payload dict
    # Add other required fields based on actual schema

    @field_validator("recipient_agent_id")
    @classmethod
    def validate_agent_id_format(cls, v: str) -> str:
        # ENFORCE-MAILBOX-STD-001 (Agent ID format part)
        if not re.match(r"^Agent-\d+$", v):
            raise ValueError("recipient_agent_id must follow 'Agent-X' format")
        return v


class TheaRelayAgent(BaseAgent):
    """
    An agent that monitors a directory for THEA responses, parses them,
    and dispatches them to the appropriate agent mailboxes.
    """

    def __init__(self, agent_id="TheaRelayAgent", log_level=logging.INFO):
        super().__init__(agent_id=agent_id, log_level=log_level)
        self.response_dir = RESPONSE_DIR
        self.archive_dir = ARCHIVE_DIR
        self.error_dir = ERROR_DIR
        self.mailbox_root_dir = MAILBOX_ROOT_DIR
        self.polling_interval = POLLING_INTERVAL_SECONDS
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create necessary directories if they don't exist."""
        try:
            self.response_dir.mkdir(parents=True, exist_ok=True)
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            self.error_dir.mkdir(parents=True, exist_ok=True)
            self.mailbox_root_dir.mkdir(parents=True, exist_ok=True)
            self.log.info("Monitored directories ensured.")
        except Exception as e:
            self.log.error(
                f"Failed to create monitored directories: {e}", exc_info=True
            )
            # Depending on BaseAgent, might need to signal critical failure here

    def _load_thea_response(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Loads a JSON response from the specified file path."""
        self.log.debug(f"Loading response from: {file_path.name}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.log.error(f"Failed to decode JSON from {file_path.name}: {e}")
            return None
        except Exception as e:
            self.log.error(f"Failed to read file {file_path.name}: {e}", exc_info=True)
            return None

    def _validate_response(
        self, response: Optional[Dict[str, Any]], filename: str
    ) -> bool:
        """Validate response against TheaMessage Pydantic schema."""
        if not response:
            self.log.warning(f"Response data is empty for {filename}. Skipping.")
            return False
        try:
            TheaMessage(**response)  # Validate using Pydantic model
            self.log.debug(f"Response schema validated successfully for {filename}.")
            return True
        except ValidationError as e:
            self.log.warning(f"Invalid THEA message schema in {filename}: {e}")
            return False
        # REMOVED old basic validation
        # TODO REMOVED: Add more validation based on DEFINE-THEA-MESSAGE-SCHEMA-001

    def _get_mailbox_path(self, agent_id: str, context_id: str) -> Optional[Path]:
        """Constructs the target mailbox path, validating agent ID format based on ENFORCE-MAILBOX-STD-001."""
        # Validation now handled by Pydantic model, but keep log message
        if not re.match(r"^Agent-\d+$", agent_id):
            self.log.warning(
                f"Invalid recipient_agent_id format: '{agent_id}'. Expected 'Agent-X' (Should have been caught by schema validation). Skipping."  # noqa: E501
            )
            return None
        # TODO REMOVED: Align validation with ENFORCE-MAILBOX-STD-001 standard

        # Ensure target agent mailbox exists (ENFORCE-MAILBOX-STD-001 - Path part)
        agent_mailbox_dir = self.mailbox_root_dir / agent_id / "inbox"
        try:
            agent_mailbox_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.log.error(
                f"Failed to create mailbox directory {agent_mailbox_dir}: {e}",
                exc_info=True,
            )
            return None
        # Define message naming convention (ENFORCE-MAILBOX-STD-001 - Naming part)
        # Use context_id if available, otherwise generate one
        safe_context_id = re.sub(
            r"[^a-zA-Z0-9_\-]",
            "_",
            context_id or f"gen_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
        )  # Sanitize context_id
        return agent_mailbox_dir / f"MSG_FROM_THEA_{safe_context_id}.json"

    def _dispatch_message(self, response: Dict[str, Any], filename: str) -> bool:
        """Dispatches the parsed response to the correct agent mailbox."""
        # Extract validated data (Pydantic ensures recipient_agent_id exists)
        agent_id = response["recipient_agent_id"]
        context_id = response.get("context_id")  # Already validated as optional

        msg_path = self._get_mailbox_path(agent_id, context_id)
        if not msg_path:
            return False

        self.log.info(
            f"Dispatching '{filename}' to {agent_id} (Context: {context_id or 'Generated'})"
        )  # Adjust log
        try:
            write_mailbox_message(msg_path, response)
            self.log.info(
                f"Successfully dispatched to {msg_path.relative_to(Path.cwd())}"
            )
            return True
        except Exception as e:
            self.log.error(
                f"Failed to write mailbox message to {msg_path}: {e}", exc_info=True
            )
            return False

    def _move_file(self, file_path: Path, target_dir: Path):
        """Moves a file to a target directory (archive or error)."""
        target_path = target_dir / file_path.name
        try:
            shutil.move(str(file_path), str(target_path))
            self.log.info(f"Moved {file_path.name} to {target_dir.name} directory.")
        except Exception as e:
            self.log.error(
                f"Failed to move {file_path.name} to {target_dir.name}: {e}",
                exc_info=True,
            )
            # If moving fails, the file might be processed again. Critical error.

    async def _process_files(self):
        """Processes all pending files in the response directory."""
        self.log.debug(f"Checking for responses in {self.response_dir}")
        processed_count = 0
        error_count = 0
        files_found = 0

        # Prioritize JSON files
        files_to_process = list(self.response_dir.glob("*.json"))
        # Add .txt as fallback if specified in requirements later
        # files_to_process.extend(list(self.response_dir.glob("*.txt")))

        files_found = len(files_to_process)
        if files_found > 0:
            self.log.info(f"Found {files_found} potential response file(s).")

        for file in files_to_process:
            if file.is_dir() or file.parent != self.response_dir:
                continue  # Skip directories and files not directly in response_dir

            self.log.info(f"Processing file: {file.name}")
            response_data = self._load_thea_response(file)

            if not response_data:
                # Loading failed (e.g., decode error), move to error directory
                self.log.error(
                    f"Failed to load/decode {file.name}. Moving to error directory."
                )
                self._move_file(file, self.error_dir)
                error_count += 1
                continue

            if self._validate_response(response_data, file.name):
                if self._dispatch_message(response_data, file.name):
                    # Dispatch successful, archive the file
                    self._move_file(file, self.archive_dir)
                    processed_count += 1
                else:
                    # Dispatch failed, move to error directory
                    self.log.error(
                        f"Dispatch failed for {file.name}. Moving to error directory."
                    )
                    self._move_file(file, self.error_dir)
                    error_count += 1
            else:
                # Invalid response content, move to error directory
                self.log.warning(
                    f"Invalid response content in {file.name}. Moving to error directory."  # noqa: E501
                )
                self._move_file(file, self.error_dir)
                error_count += 1

        if files_found > 0:
            self.log.info(
                f"Processing cycle complete. Processed: {processed_count}, Errors/Skipped: {error_count}."  # noqa: E501
            )

    # This run method assumes BaseAgent uses asyncio
    async def run(self):
        """Main agent loop."""
        self.log.info(f"{self.agent_id} starting run loop.")
        try:
            while True:  # Add proper shutdown mechanism later
                await self._process_files()
                self.log.debug(f"Sleeping for {self.polling_interval} seconds.")
                await asyncio.sleep(self.polling_interval)
        except asyncio.CancelledError:
            self.log.info(f"{self.agent_id} run loop cancelled.")
        except Exception as e:
            self.log.critical(
                f"{self.agent_id} encountered critical error in run loop: {e}",
                exc_info=True,
            )
            # Consider signaling failure to supervisor/coordinator if possible
        finally:
            self.log.info(f"{self.agent_id} shutting down.")


# Basic execution for testing if run directly (requires BaseAgent definition)
# This won't work correctly without the full agent runner infrastructure
if __name__ == "__main__":
    print(
        "Attempting basic execution of TheaRelayAgent (for testing purposes only - single pass)."  # noqa: E501
    )
    logging.basicConfig(level=logging.INFO)  # Setup basic logging for standalone test

    # Check if a dummy BaseAgent is being used
    if "dreamos.core.coordination.base_agent" not in sys.modules:
        print(
            "WARNING: Running with Dummy BaseAgent. Real agent execution environment required."  # noqa: E501
        )

    agent = TheaRelayAgent()

    # Basic way to run the async method for a single pass for testing
    try:
        print("Starting single processing pass...")
        asyncio.run(
            agent._process_files()
        )  # MODIFIED: Call _process_files instead of run()
        print("Single processing pass complete.")
    except Exception as e:
        print(f"An error occurred during standalone execution: {e}")
