# src/dreamos/tools/thea_relay_agent.py

import asyncio  # Import asyncio for sleep
import json
import logging  # Import logging
import re  # Import re for regex validation
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Type  # Added Type

from dreamos.utils import file_io  # ADDED IMPORT

# from dreamos.core.comms.mailbox_utils import write_mailbox_message # Will be made conditional
# from dreamos.core.coordination import agent_bus # Will be made conditional
from pydantic import (  # Import Pydantic
    BaseModel,
    ValidationError,
    field_validator,
)


# EDIT START: Add helper to find project root for _MockConfig
def _find_mock_project_root(marker: str = ".git") -> Path:
    """Finds the project root for mock config by searching upwards for a marker."""
    current_path = Path(__file__).resolve()
    while current_path != current_path.parent:
        if (current_path / marker).exists():
            return current_path
        current_path = current_path.parent
    # Fallback if marker not found (e.g., running in a context without .git)
    # Using current file's grandparent as a simple fallback, adjust if needed.
    return Path(__file__).resolve().parent.parent


# EDIT END


# --- Mock/Standalone Configuration and Dummies (defined globally) ---
class _MockConfigPaths:
    def __init__(self):
        # EDIT START: Add project_root to _MockConfigPaths
        self.project_root = _find_mock_project_root()
        # EDIT END
        self.thea_responses_dir = (
            self.project_root / "runtime/mock_thea_responses_standalone"
        )
        self.agent_comms = (
            self.project_root / "runtime/mock_agent_comms_standalone/agent_mailboxes"
        )


class _MockConfigAgentSettings:
    def __init__(self):
        self.thea_relay_poll_interval = 3  # Faster polling for standalone testing


class _MockConfig:
    def __init__(self):
        self.paths = _MockConfigPaths()
        self.agent_settings = _MockConfigAgentSettings()
        self.agent_id = "MockConfigForStandaloneAgent"  # Example if BaseAgent uses it


def get_config():  # This will be the mock config provider for this script
    """Returns a mock configuration object for testing."""
    return _MockConfig()


class _StandaloneDummyBaseAgent:
    def __init__(
        self,
        agent_id="TheaRelayAgent_Dummy",
        log_level=logging.INFO,
        config=None,
        agent_bus=None,
        **kwargs,
    ):
        self.agent_id = agent_id
        self.logger = logging.getLogger(agent_id)  # Use self.logger consistently
        self.logger.setLevel(log_level)
        self.config = (
            config if config is not None else get_config()
        )  # Ensure config is present
        self.agent_bus = agent_bus

        # Ensure basic logging handler for standalone mode if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.logger.info(
            f"_StandaloneDummyBaseAgent '{self.agent_id}' initialized with config: {type(self.config).__name__}."
        )

    async def run(self):
        self.logger.error(
            f"_StandaloneDummyBaseAgent '{self.agent_id}' run() called - it's a placeholder and TheaRelayAgent should implement its own run logic."
        )


async def _dummy_async_write_mailbox_message(path: Path, content: Dict[str, Any]):
    logger = logging.getLogger("Dummy_write_mailbox_message")
    # Ensure logger has a handler if basicConfig hasn't run when this is first called
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)  # Or DEBUG for more verbosity

    logger.info(f"[DUMMY WRITE] Attempting to write to {path.resolve()}")
    logger.debug(f"[DUMMY CONTENT] {json.dumps(content, indent=2)}")

    # Ensure parent directory exists (using asyncio.to_thread for sync Path methods)
    parent_dir = path.parent
    if not await asyncio.to_thread(parent_dir.exists):
        logger.info(
            f"[DUMMY WRITE] Parent directory {parent_dir.resolve()} does not exist. Creating."
        )
        try:
            await asyncio.to_thread(parent_dir.mkdir, parents=True, exist_ok=True)
            logger.info(
                f"[DUMMY WRITE] Created parent directory {parent_dir.resolve()}"
            )
        except Exception as e_mkdir:
            logger.error(
                f"[DUMMY WRITE] Error creating directory {parent_dir.resolve()}: {e_mkdir}",
                exc_info=True,
            )
            raise  # Re-raise if directory creation is critical

    try:

        def _sync_file_write():
            with open(path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2)

        await asyncio.to_thread(_sync_file_write)
        logger.info(f"[DUMMY WRITE] Successfully wrote dummy file to {path.resolve()}")
    except Exception as e_write:
        logger.error(
            f"[DUMMY WRITE] Error writing dummy file {path.resolve()}: {e_write}",
            exc_info=True,
        )
        raise


# --- Conditional Imports and Component Selection ---
_BaseAgent_cls: Type
_write_mailbox_message_fn: Any
_AgentBusType: Type

if __name__ == "__main__":
    print(
        "[TheaRelayAgent INFO] Running in STANDALONE mode. Using dummy/mock implementations for DreamOS core components."
    )
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )  # Setup logging early for standalone
    _BaseAgent_cls = _StandaloneDummyBaseAgent
    _write_mailbox_message_fn = _dummy_async_write_mailbox_message
    _AgentBusType = Any  # For type hinting, as real agent_bus module is not imported
else:
    print(
        "[TheaRelayAgent INFO] Running in INTEGRATED mode. Attempting to import real DreamOS core components."
    )
    try:
        from dreamos.core.comms.mailbox_utils import (
            write_mailbox_message as real_write_mailbox_message,
        )
        from dreamos.core.coordination import (
            agent_bus as real_agent_bus_module,  # For AgentBus type
        )
        from dreamos.core.coordination.base_agent import BaseAgent as RealBaseAgent

        _BaseAgent_cls = RealBaseAgent
        _write_mailbox_message_fn = real_write_mailbox_message
        _AgentBusType = real_agent_bus_module.AgentBus
        print(
            "[TheaRelayAgent INFO] Successfully imported REAL BaseAgent, write_mailbox_message, and agent_bus.AgentBus type."
        )
    except ImportError as e:
        print(
            f"[TheaRelayAgent CRITICAL] Failed to import real DreamOS components in INTEGRATED mode: {e}. This agent will likely NOT function correctly.",
            exc_info=True,
        )
        # Fallback to prevent immediate crash, but this is a fatal error for integration.
        _BaseAgent_cls = _StandaloneDummyBaseAgent
        _write_mailbox_message_fn = _dummy_async_write_mailbox_message
        _AgentBusType = Any
        print(
            "[TheaRelayAgent WARNING] INTEGRATED mode fell back to dummy components due to import error. THIS IS UNEXPECTED AND LIKELY AN ISSUE."
        )
        # In a real integrated scenario, we might want to re-raise e or sys.exit()
        # For now, allowing it to proceed with dummies to avoid script death at import.
        # raise e

# --- Global constants (can be overridden by mock config for paths) ---
RESPONSE_DIR = Path("runtime/thea_responses")
ARCHIVE_DIR = RESPONSE_DIR / "archive"
ERROR_DIR = RESPONSE_DIR / "error"
MAILBOX_ROOT_DIR = Path("runtime/agent_comms/agent_mailboxes")
POLLING_INTERVAL_SECONDS = 5


# --- Pydantic Schema for Validation (DEFINE-THEA-MESSAGE-SCHEMA-001) ---
class TheaMessage(BaseModel):
    recipient_agent_id: str
    context_id: Optional[str] = None
    payload: Dict[str, Any]

    @field_validator("recipient_agent_id")
    @classmethod
    def validate_agent_id_format(cls, v: str) -> str:
        if not re.match(r"^Agent-\\d+$", v):
            raise ValueError("recipient_agent_id must follow 'Agent-X' format")
        return v


class TheaRelayAgent(_BaseAgent_cls):  # Inherits from conditionally chosen BaseAgent
    """
    An agent that monitors a directory for THEA responses, parses them,
    and dispatches them to the appropriate agent mailboxes.
    """

    def __init__(
        self,
        agent_id: str = "TheaRelayAgent",
        agent_bus_instance: Optional[
            _AgentBusType
        ] = None,  # Use conditional AgentBusType
    ):
        loaded_config = (
            get_config()
        )  # Always use our (mock) get_config for this script's execution

        super().__init__(
            agent_id=agent_id, config=loaded_config, agent_bus=agent_bus_instance
        )
        # self.config is now set by BaseAgent constructor (either dummy or real, with our mock config)

        # Use self.config (which is our mock_config) or fallbacks.
        # Note: RESPONSE_DIR etc. are global fallbacks, loaded_config paths take precedence.
        self.response_dir = getattr(
            loaded_config.paths, "thea_responses_dir", RESPONSE_DIR
        )
        self.archive_dir = self.response_dir / "archive"
        self.error_dir = self.response_dir / "error"
        self.mailbox_root_dir = getattr(
            loaded_config.paths, "agent_comms", MAILBOX_ROOT_DIR
        )

        poll_interval_default = POLLING_INTERVAL_SECONDS
        if hasattr(loaded_config, "agent_settings") and hasattr(
            loaded_config.agent_settings, "thea_relay_poll_interval"
        ):
            poll_interval_default = (
                loaded_config.agent_settings.thea_relay_poll_interval
            )
        self.polling_interval = poll_interval_default

        # _ensure_dirs is async, call in async setup or run loop
        self.logger.info(
            f"TheaRelayAgent '{self.agent_id}' initialized (using {type(self).__bases__[0].__name__})."
        )
        self.logger.info(f"Monitoring: {self.response_dir.resolve()}")
        self.logger.info(f"Archive to: {self.archive_dir.resolve()}")
        self.logger.info(f"Errors to: {self.error_dir.resolve()}")
        self.logger.info(f"Mailbox root: {self.mailbox_root_dir.resolve()}")
        self.logger.info(f"Polling interval: {self.polling_interval}s")

    async def _ensure_dirs(self):
        """Create necessary directories if they don't exist. Async."""
        setup_logger = logging.getLogger(f"{self.agent_id}.Setup")

        dirs_to_create = [
            self.response_dir,
            self.archive_dir,
            self.error_dir,
            self.mailbox_root_dir,
        ]
        setup_logger.info(
            f"Ensuring directories exist: {[str(d.resolve()) for d in dirs_to_create]}"
        )
        all_dirs_ensured = True
        try:
            for d in dirs_to_create:
                # MODIFIED: Use file_io.ensure_directory
                if not await asyncio.to_thread(file_io.ensure_directory, d):
                    setup_logger.error(
                        f"Failed to ensure directory {d.resolve()} using file_io.ensure_directory."
                    )
                    all_dirs_ensured = (
                        False  # Mark as failed but continue trying others
                    )

            if all_dirs_ensured:
                setup_logger.info(
                    "Monitored directories ensured successfully using file_io."
                )
            else:
                setup_logger.error(
                    "One or more directories could not be ensured. Check previous errors."
                )
                # Optionally raise an error if any directory creation failed
                # raise OSError("Failed to ensure all necessary directories for TheaRelayAgent.")

        except (
            Exception
        ) as e:  # Catch any unexpected errors from asyncio.to_thread or loop itself
            setup_logger.error(
                f"Unexpected critical error during _ensure_dirs loop: {e}",
                exc_info=True,
            )
            raise  # Re-raise critical errors

    async def _load_thea_response(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Loads a JSON response from the specified file path. Async."""
        self.logger.debug(
            f"Loading response from: {file_path.name} (full path: {file_path.resolve()})"
        )

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
            self.logger.warning(
                f"Response data is empty for {filename}. Skipping validation."
            )
            return False
        try:
            TheaMessage(**response)
            self.logger.debug(f"Response schema validated successfully for {filename}.")
            return True
        except ValidationError as e:
            self.logger.warning(f"Invalid THEA message schema in {filename}: {e}")
            return False

    async def _get_mailbox_path(
        self, agent_id: str, context_id: Optional[str]
    ) -> Optional[Path]:
        """Constructs the target mailbox path, validating agent ID format. Async for mkdir."""
        if not re.match(
            r"^Agent-\\d+$", agent_id
        ):  # Ensure regex is correctly escaped for string
            self.logger.warning(
                f"Invalid recipient_agent_id format: '{agent_id}'. Expected 'Agent-X'. Skipping."
            )
            return None

        agent_mailbox_dir = self.mailbox_root_dir / agent_id / "inbox"
        try:
            if not await asyncio.to_thread(agent_mailbox_dir.exists):
                self.logger.info(
                    f"Mailbox directory {agent_mailbox_dir.resolve()} does not exist. Creating."
                )
                await asyncio.to_thread(
                    agent_mailbox_dir.mkdir, parents=True, exist_ok=True
                )
                self.logger.info(
                    f"Created mailbox directory {agent_mailbox_dir.resolve()}."
                )
        except Exception as e:
            self.logger.error(
                f"Failed to create mailbox directory {agent_mailbox_dir.resolve()}: {e}",
                exc_info=True,
            )
            return None

        safe_context_id = re.sub(
            r"[^a-zA-Z0-9_\\-]",  # Correctly escaped for regex
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
            return False  # Error already logged by _get_mailbox_path

        self.logger.info(
            f"Dispatching '{filename}' to {agent_id} (Context: {context_id or 'Generated'}) -> {msg_path.resolve()}"
        )
        try:
            # Use the conditionally defined write_mailbox_message function
            await _write_mailbox_message_fn(msg_path, response)
            self.logger.info(
                f"Successfully dispatched to {msg_path.relative_to(Path.cwd())}"
            )
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to write mailbox message to {msg_path.resolve()}: {e}",
                exc_info=True,
            )
            return False

    async def _move_file(self, file_path: Path, target_dir: Path):
        """Moves a file to a target directory (archive or error). Async.
        Now uses centralized file_io.move_file.
        """
        self.logger.info(
            f"Attempting to move {file_path.resolve()} to {target_dir.resolve()} using file_io.move_file"
        )

        # MODIFIED: Use file_io.move_file
        # The create_destination_dir is True by default in file_io.move_file,
        # so the previous explicit mkdir in the old _sync_move is handled.
        moved_path = await asyncio.to_thread(
            file_io.move_file,
            source_path=file_path,
            destination_dir=target_dir,
            # new_filename can be omitted to keep original name
            # create_destination_dir is True by default
        )

        if moved_path:
            self.logger.info(
                f"Moved {file_path.name} to {target_dir.name} directory ({moved_path.resolve()})."
            )
        else:
            # file_io.move_file already logs errors extensively.
            # This log indicates that the operation, as a whole, failed from the agent's perspective.
            self.logger.error(
                f"Failed to move {file_path.name} to {target_dir.name} using file_io.move_file. See previous errors from file_io."
            )
            # Decide if to raise an error here or let the agent continue trying to process other files.
            # For now, logging the failure and not raising, to allow other files to be processed.

    async def _process_files(self):
        """Processes all pending files in the response directory. Async."""
        self.logger.debug(f"Checking for responses in {self.response_dir.resolve()}")
        processed_count = 0
        error_count = 0
        files_found = 0

        # Ensure response_dir exists before globbing. If not, _ensure_dirs should have created it or raised.
        # If _ensure_dirs failed, agent might not even reach here.
        # Adding a check just in case.
        if not await asyncio.to_thread(self.response_dir.exists):
            self.logger.error(
                f"Response directory {self.response_dir.resolve()} does not exist. Cannot process files. Check _ensure_dirs."
            )
            # Optional: Sleep for a bit before retrying or exiting loop if this is persistent.
            return  # Skip this processing cycle

        def _sync_glob():
            return list(self.response_dir.glob("*.json"))

        files_to_process = await asyncio.to_thread(_sync_glob)

        files_found = len(files_to_process)
        if files_found > 0:
            self.logger.info(
                f"Found {files_found} potential response file(s) in {self.response_dir.resolve()}."
            )

        for file_path in files_to_process:
            # Ensure we are processing files only, not directories, and directly in response_dir
            if await asyncio.to_thread(file_path.is_dir):
                self.logger.debug(f"Skipping directory: {file_path.name}")
                continue
            # This check might be redundant if glob is specific enough, but good for safety
            if file_path.parent.resolve() != self.response_dir.resolve():
                self.logger.warning(
                    f"Skipping file not directly in response_dir: {file_path.resolve()} (parent: {file_path.parent.resolve()})"
                )
                continue

            self.logger.info(
                f"Processing file: {file_path.name} (from {file_path.resolve()})"
            )
            response_data = await self._load_thea_response(file_path)

            if not response_data:
                self.logger.error(
                    f"Failed to load/decode {file_path.name}. Moving to error directory: {self.error_dir.resolve()}"
                )
                await self._move_file(file_path, self.error_dir)
                error_count += 1
                continue

            if self._validate_response(response_data, file_path.name):
                if await self._dispatch_message(response_data, file_path.name):
                    await self._move_file(file_path, self.archive_dir)
                    processed_count += 1
                else:  # dispatch_message already logs error
                    self.logger.error(
                        f"Failed to dispatch {file_path.name}. Moving to error directory: {self.error_dir.resolve()}"
                    )
                    await self._move_file(file_path, self.error_dir)
                    error_count += 1
            else:  # _validate_response logs warning
                self.logger.warning(
                    f"Invalid response schema in {file_path.name}. Moving to error directory: {self.error_dir.resolve()}"
                )
                await self._move_file(file_path, self.error_dir)
                error_count += 1

        if files_found > 0:  # Log summary only if files were initially found
            self.logger.info(
                f"File processing cycle complete for {self.response_dir.resolve()}. Processed: {processed_count}, Errors: {error_count} (out of {files_found} found)."
            )
        else:
            self.logger.debug(
                f"No .json files found in {self.response_dir.resolve()} this cycle."
            )

    async def run(self):
        """Main execution loop for the TheaRelayAgent."""
        self.logger.info(
            f"TheaRelayAgent '{self.agent_id}' starting run loop (Base class: {type(self).__bases__[0].__name__})."
        )
        try:
            await (
                self._ensure_dirs()
            )  # Ensure directories are created before starting loop
        except Exception as e_ensure_dirs:
            self.logger.critical(
                f"Failed during initial directory setup: {e_ensure_dirs}. Agent cannot run.",
                exc_info=True,
            )
            return  # Stop agent if essential dirs can't be made

        try:
            while True:
                await self._process_files()
                self.logger.debug(
                    f"Waiting for {self.polling_interval} seconds before next scan of {self.response_dir.resolve()}..."
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
if __name__ == "__main__":
    # Logging is configured in the __main__ block's conditional import section already if it's standalone.
    # If not, basicConfig might be needed here if this script were importable and runnable without __main__ path.
    # For this user's case, the logging setup in the `if __name__ == "__main__":` above is sufficient.

    print("[TheaRelayAgent Main] Starting TheaRelayAgent in standalone mode...")

    # The global get_config() is already the mock one.
    # The conditional imports handle BaseAgent and write_mailbox_message.
    # agent_bus_instance is None for standalone.

    async def main_standalone_runner():
        relay_agent = TheaRelayAgent(
            agent_id="TestTheaRelayStandalone", agent_bus_instance=None
        )
        await relay_agent.run()

    try:
        asyncio.run(main_standalone_runner())
    except KeyboardInterrupt:
        # Use a logger that's guaranteed to be configured
        logging.getLogger("TheaRelayAgentMain").info(
            "TheaRelayAgent standalone test stopped by user."
        )
    except Exception as e_main:
        logging.getLogger("TheaRelayAgentMain").critical(
            f"TheaRelayAgent standalone test CRASHED: {e_main}", exc_info=True
        )
