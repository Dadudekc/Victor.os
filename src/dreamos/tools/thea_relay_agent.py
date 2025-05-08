# src/dreamos/tools/thea_relay_agent.py

import asyncio  # Import asyncio for sleep
import json
import logging  # Import logging
import re  # Import re for regex validation
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional  # Added type hinting

from dreamos.core.comms.mailbox_utils import write_mailbox_message
from dreamos.core.coordination import agent_bus

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
# try:
#     from dreamos.agents.utils.agent_utils import write_mailbox_message
# except ImportError:
#     logging.warning(
#         "[TheaRelayAgent WARNING] Could not import write_mailbox_message. Using dummy implementation."  # noqa: E501
#     )
#
#     def write_mailbox_message(path: Path, content: Dict[str, Any]):
#         logging.info(f"[TheaRelayAgent DUMMY WRITE] Would write to {path}")
#         logging.debug(f"[TheaRelayAgent DUMMY CONTENT] {json.dumps(content)}")
#         path.parent.mkdir(parents=True, exist_ok=True)
#         try:
#             with open(path, "w", encoding="utf-8") as f:
#                 json.dump(content, f, indent=2)
#         except Exception as e:
#             logging.error(
#                 f"[TheaRelayAgent DUMMY WRITE] Error writing dummy file {path}: {e}"
#             )
#             raise  # Re-raise exception for dummy implementation


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

    def __init__(
        self,
        agent_id: str = "TheaRelayAgent",
        agent_bus_instance: Optional[agent_bus.AgentBus] = None,
    ):
        # Load config first using get_config()
        loaded_config = get_config()
        
        # Call super().__init__ with the loaded config
        super().__init__(
            agent_id=agent_id, config=loaded_config, agent_bus=agent_bus_instance
        )
        # self.config is now set by BaseAgent constructor

        # Use self.config (from BaseAgent) or fallbacks
        self.response_dir = getattr(self.config.paths, 'thea_responses_dir', RESPONSE_DIR) if hasattr(self.config, 'paths') else RESPONSE_DIR
        self.archive_dir = self.response_dir / "archive" # Derived
        self.error_dir = self.response_dir / "error"     # Derived
        self.mailbox_root_dir = getattr(self.config.paths, 'agent_comms', MAILBOX_ROOT_DIR) if hasattr(self.config, 'paths') else MAILBOX_ROOT_DIR
        
        poll_interval_default = POLLING_INTERVAL_SECONDS
        if hasattr(self.config, 'agent_settings') and hasattr(self.config.agent_settings, 'thea_relay_poll_interval'):
            poll_interval_default = self.config.agent_settings.thea_relay_poll_interval
        self.polling_interval = poll_interval_default

        # _ensure_dirs is async, call in async setup or run loop
        self.logger.info(f"TheaRelayAgent '{self.agent_id}' initialized.")
        self.logger.info(f"Monitoring: {self.response_dir}")
        self.logger.info(f"Archive to: {self.archive_dir}")
        self.logger.info(f"Errors to: {self.error_dir}")
        self.logger.info(f"Mailbox root: {self.mailbox_root_dir}")
        self.logger.info(f"Polling interval: {self.polling_interval}s")

    async def _ensure_dirs(self):
        """Create necessary directories if they don't exist. Async."""
        dirs_to_create = [
            self.response_dir,
            self.archive_dir,
            self.error_dir,
            self.mailbox_root_dir,  # This one is particularly important if agents don't create their own base.
        ]
        try:
            for d in dirs_to_create:
                if not await asyncio.to_thread(d.exists):
                    await asyncio.to_thread(d.mkdir, parents=True, exist_ok=True)
            self.logger.info("Monitored directories ensured (async).")
        except Exception as e:
            self.logger.error(
                f"Failed to create monitored directories (async): {e}", exc_info=True
            )
            # Consider raising to halt agent if dirs are critical
            raise  # Re-raise for now, as dir creation failure might be fatal

    async def _load_thea_response(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Loads a JSON response from the specified file path. Async."""
        self.logger.debug(f"Loading response from: {file_path.name}")

        def _sync_load():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)

        try:
            return await asyncio.to_thread(_sync_load)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON from {file_path.name}: {e}")
            return None
        except Exception as e:
            self.logger.error(
                f"Failed to read file {file_path.name}: {e}", exc_info=True
            )
            return None

    def _validate_response(
        self, response: Optional[Dict[str, Any]], filename: str
    ) -> bool:
        """Validate response against TheaMessage Pydantic schema."""
        if not response:
            self.logger.warning(f"Response data is empty for {filename}. Skipping.")
            return False
        try:
            TheaMessage(**response)  # Validate using Pydantic model
            self.logger.debug(f"Response schema validated successfully for {filename}.")
            return True
        except ValidationError as e:
            self.logger.warning(f"Invalid THEA message schema in {filename}: {e}")
            return False
        # REMOVED old basic validation
        # TODO REMOVED: Add more validation based on DEFINE-THEA-MESSAGE-SCHEMA-001

    async def _get_mailbox_path(
        self, agent_id: str, context_id: Optional[str]
    ) -> Optional[Path]:
        """Constructs the target mailbox path, validating agent ID format. Async for mkdir."""
        if not re.match(r"^Agent-\d+$", agent_id):
            self.logger.warning(
                f"Invalid recipient_agent_id format: '{agent_id}'. Expected 'Agent-X' (Should be caught by schema). Skipping."  # noqa: E501
            )
            return None

        agent_mailbox_dir = self.mailbox_root_dir / agent_id / "inbox"
        try:
            if not await asyncio.to_thread(agent_mailbox_dir.exists):
                await asyncio.to_thread(
                    agent_mailbox_dir.mkdir, parents=True, exist_ok=True
                )
        except Exception as e:
            self.logger.error(
                f"Failed to create mailbox directory {agent_mailbox_dir}: {e}",
                exc_info=True,
            )
            return None

        safe_context_id = re.sub(
            r"[^a-zA-Z0-9_\-]",
            "_",
            context_id or f"gen_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
        )
        return agent_mailbox_dir / f"MSG_FROM_THEA_{safe_context_id}.json"

    async def _dispatch_message(self, response: Dict[str, Any], filename: str) -> bool:
        """Dispatches the parsed response to the correct agent mailbox. Async."""
        agent_id = response["recipient_agent_id"]
        context_id = response.get("context_id")

        msg_path = await self._get_mailbox_path(agent_id, context_id)
        if not msg_path:
            return False

        self.logger.info(
            f"Dispatching '{filename}' to {agent_id} (Context: {context_id or 'Generated'})"
        )
        try:
            # write_mailbox_message is async
            await write_mailbox_message(msg_path, response)
            self.logger.info(
                f"Successfully dispatched to {msg_path.relative_to(Path.cwd())}"
            )
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to write mailbox message to {msg_path}: {e}", exc_info=True
            )
            return False

    async def _move_file(self, file_path: Path, target_dir: Path):
        """Moves a file to a target directory (archive or error). Async."""
        target_path = target_dir / file_path.name

        def _sync_move():
            shutil.move(str(file_path), str(target_path))

        try:
            await asyncio.to_thread(_sync_move)
            self.logger.info(f"Moved {file_path.name} to {target_dir.name} directory.")
        except Exception as e:
            self.logger.error(
                f"Failed to move {file_path.name} to {target_dir.name}: {e}",
                exc_info=True,
            )

    async def _process_files(self):
        """Processes all pending files in the response directory. Async."""
        self.logger.debug(f"Checking for responses in {self.response_dir}")
        processed_count = 0
        error_count = 0
        files_found = 0

        def _sync_glob():
            return list(self.response_dir.glob("*.json"))

        files_to_process = await asyncio.to_thread(_sync_glob)

        files_found = len(files_to_process)
        if files_found > 0:
            self.logger.info(f"Found {files_found} potential response file(s).")

        for file_path in files_to_process:  # Renamed file to file_path for clarity
            if (
                await asyncio.to_thread(file_path.is_dir)
                or file_path.parent != self.response_dir
            ):
                continue

            self.logger.info(f"Processing file: {file_path.name}")
            response_data = await self._load_thea_response(file_path)

            if not response_data:
                self.logger.error(
                    f"Failed to load/decode {file_path.name}. Moving to error directory."
                )
                await self._move_file(file_path, self.error_dir)
                error_count += 1
                continue

            if self._validate_response(response_data, file_path.name):
                if await self._dispatch_message(response_data, file_path.name):
                    await self._move_file(file_path, self.archive_dir)
                    processed_count += 1
                else:
                    self.logger.error(
                        f"Failed to dispatch {file_path.name}. Moving to error directory."
                    )
                    await self._move_file(file_path, self.error_dir)
                    error_count += 1
            else:
                self.logger.warning(
                    f"Invalid response schema in {file_path.name}. Moving to error directory."
                )
                await self._move_file(file_path, self.error_dir)
                error_count += 1

        if files_found > 0:
            self.logger.info(
                f"File processing complete. Processed: {processed_count}, Errors: {error_count}"
            )

    async def run(self):
        """Main execution loop for the TheaRelayAgent."""
        self.logger.info(f"TheaRelayAgent '{self.agent_id}' starting run loop.")
        await self._ensure_dirs()  # Ensure directories are created before starting loop

        try:
            while True:  # Assuming BaseAgent or main loop will handle graceful shutdown
                await self._process_files()
                self.logger.debug(
                    f"Waiting for {self.polling_interval} seconds before next scan..."
                )
                await asyncio.sleep(self.polling_interval)
        except asyncio.CancelledError:
            self.logger.info(f"TheaRelayAgent '{self.agent_id}' run loop cancelled.")
        except Exception as e:
            self.logger.critical(
                f"TheaRelayAgent '{self.agent_id}' run loop encountered a critical error: {e}",
                exc_info=True,
            )
        finally:
            self.logger.info(f"TheaRelayAgent '{self.agent_id}' run loop stopped.")


# Example usage (if run as a standalone script for testing)
# This would need to be adapted for async execution, e.g.:
# async def main():
#     # Setup AppConfig, AgentBus as needed
#     config = AppConfig.load() # Or mock AppConfig
#     # agent_bus = AgentBus()
#     relay_agent = TheaRelayAgent(config=config, agent_bus=None) # Pass None for bus if not testing bus interactions
#     await relay_agent.run()
#
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         logger.info("TheaRelayAgent standalone test stopped by user.")
