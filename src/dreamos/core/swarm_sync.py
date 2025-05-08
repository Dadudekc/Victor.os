#!/usr/bin/env python3
"""
Swarm State Synchronizer (Module 5)

Provides functions for agents to read the shared swarm state and update their
own status atomically using a write-to-temp-rename strategy.
"""

import json
import logging
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List

from dreamos.identity.store import get_identity_store

# --- Path Setup ---
# project_root = Path(__file__).resolve().parents[3] # REMOVED - path to be handled by AppConfig

# --- Configuration ---
# Constants moved to AppConfig
# DEFAULT_STATE_FILE_PATH_STR = "runtime/swarm_state.json" # Example default if key missing
# DEFAULT_MAX_UPDATE_ATTEMPTS = 3
# DEFAULT_RETRY_DELAY_MIN_MS = 50
# DEFAULT_RETRY_DELAY_MAX_MS = 200

# --- Logging Setup ---
logger = logging.getLogger("SwarmSync")
if not logger.hasHandlers():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )


# --- Helper Functions ---

def _get_sync_config() -> Dict[str, Any]:
    """Internal helper to fetch swarm sync specific configurations."""
    from dreamos.core.config import get_config
    config = get_config()
    # Default values if swarm_sync section or specific keys are missing
    defaults = {
        "state_file_name": "swarm_state.json",
        "lock_file_name": "swarm_state.lock",
        "max_lock_wait_seconds": 10,
        "max_history_entries": 100,
    }
    if hasattr(config, 'swarm_sync') and config.swarm_sync:
        # Pydantic models would be config.swarm_sync.state_file_name etc.
        # If it's just a dict in config:
        return {**defaults, **config.swarm_sync} 
    return defaults


def _get_state_file_path() -> Path:
    from dreamos.core.config import get_config
    config = get_config()
    sync_config = _get_sync_config()
    sync_state_dir = Path(config.paths.agent_comms) / "swarm_state"
    sync_state_dir.mkdir(parents=True, exist_ok=True)
    return sync_state_dir / sync_config["state_file_name"]


# --- Core Functions ---


def read_swarm_state() -> Optional[Dict[str, Any]]:
    """Reads the current swarm state from the shared file."""
    state_file = _get_state_file_path()
    if not state_file.exists():
        logger.warning(
            f"Swarm state file not found: {state_file}. Returning empty state."
        )
        return {}

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
            if not isinstance(state, dict):
                logger.error(
                    f"Swarm state file {state_file} does not contain a valid JSON object. Returning empty state."
                )
                return {}
            logger.debug(f"Read swarm state successfully from {state_file}.")
            return state
    except json.JSONDecodeError:
        logger.error(
            f"Swarm state file {state_file} contains invalid JSON. Returning empty state.",
            exc_info=True,
        )
        return {}
    except OSError as e:
        logger.error(
            f"Error reading swarm state file {state_file}: {e}. Returning empty state.",
            exc_info=True,
        )
        return {}
    except Exception as e:
        logger.error(
            f"Unexpected error reading swarm state: {e}. Returning empty state.",
            exc_info=True,
        )
        return {}


def update_agent_state(
    agent_id: str,
    status: str,
    capabilities: Optional[List[str]] = None,
    current_task_id: Optional[str] = None,
    last_error: Optional[str] = None,
) -> bool:
    """Updates the state of a specific agent in the swarm state file."""
    state_file = _get_state_file_path()
    sync_conf = _get_sync_config()
    lock_file_path = state_file.with_name(sync_conf["lock_file_name"])

    try:
        identity_store = get_identity_store()
        valid_agent_ids = identity_store.get_agent_ids()
    except Exception as e:
        logger.error(
            f"Failed to load agent IDs from AgentIdentityStore: {e}", exc_info=True
        )
        return False

    if not valid_agent_ids:
        logger.error(
            "AgentIdentityStore returned no agent IDs. Cannot validate agent for state update."
        )
        return False

    if agent_id not in valid_agent_ids:
        logger.error(
            f"Attempted to update state for unknown or unregistered agent_id: {agent_id}. Valid IDs: {valid_agent_ids}"
        )
        return False

    new_state_entry = {
        "last_updated_utc": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "status": status,
        "capabilities": capabilities,
        "current_task_id": current_task_id,
        "last_error": last_error,
    }

    tmp_filename = Path("")  # Initialize for potential cleanup access
    for attempt in range(sync_conf["max_lock_wait_seconds"]):
        logger.debug(
            f"Attempt {attempt + 1}/{sync_conf['max_lock_wait_seconds']} to update state for {agent_id}"
        )
        try:
            with open(lock_file_path, "w", encoding="utf-8") as f_lock:
                f_lock.write(str(os.getpid()))
            with open(state_file, "r", encoding="utf-8") as f_read:
                current_state = json.load(f_read)
            current_state[agent_id] = new_state_entry
            tmp_filename = (
                state_file.parent
                / f"{state_file.name}.tmp.{os.getpid()}.{uuid.uuid4()}"
            )
            # Ensure parent directory exists for tmp_filename
            tmp_filename.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp_filename, "w", encoding="utf-8") as f_tmp:
                json.dump(current_state, f_tmp, indent=2)
            os.replace(tmp_filename, state_file)
            logger.info(
                f"Successfully updated state for {agent_id} (Status: {status})"
            )
            return True
        except OSError as e:
            logger.warning(
                f"Attempt {attempt + 1} failed for {agent_id}: OS error during file operation: {e}"
            )
            if tmp_filename.exists():
                try:
                    tmp_filename.unlink()
                except OSError:
                    pass
        except Exception as e:
            logger.error(
                f"Attempt {attempt + 1} failed for {agent_id}: Unexpected error: {e}",
                exc_info=True,
            )
            if tmp_filename.exists():
                try:
                    tmp_filename.unlink()
                except OSError:
                    pass
        if attempt < sync_conf["max_lock_wait_seconds"] - 1:
            delay = random.uniform(0, 1)
            logger.info(f"Retrying update for {agent_id} after {delay:.3f}s delay.")
            time.sleep(delay)
    logger.error(
        f"Failed to update state for {agent_id} after {sync_conf['max_lock_wait_seconds']} attempts."
    )
    return False


# --- Example Usage (for testing/demonstration) ---
if __name__ == "__main__":
    from dreamos.core.config import AppConfig, get_config

    print("Demonstrating Swarm Sync functions (with AppConfig)...")
    # For this demo, AppConfig would need to be set up with coordination.swarm_sync keys
    # or defaults will be used.
    # Example: You might create a temporary AppConfig instance for the demo if needed.
    # demo_app_config = AppConfig() # Or load a specific test config

    # Ensure runtime directory exists for default state file path
    default_state_file_path = Path(
        _get_sync_config()["state_file_name"]
    )
    default_state_file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        print("Initializing identity store for demo...")
        demo_store = get_identity_store()
        if not demo_store.get_agent_ids():
            print("Demo identity store is empty. Registering demo agents...")
            demo_store.register_agent("Agent-1 (Rustbyte)", "Demo Agent")
            demo_store.register_agent("Agent-2 (Glasspulse)", "Demo Agent")
            print(f"Registered demo agents. Current IDs: {demo_store.get_agent_ids()}")
    except Exception as e:
        print(
            f"Error initializing/populating demo identity store: {e}", file=sys.stderr
        )

    print("\nAgent 1 updating state...")
    success1 = update_agent_state(
        agent_id="Agent-1 (Rustbyte)",
        status="Active",
    )
    print(f"Agent 1 Update Success: {success1}")

    print("\nAgent 2 updating state...")
    success2 = update_agent_state(
        agent_id="Agent-2 (Glasspulse)",
        status="Idle",
    )
    print(f"Agent 2 Update Success: {success2}")

    print("\nAgent 1 reading state...")
    current_swarm_state = (
        read_swarm_state()
    )  # Uses default AppConfig implicitly via _get_sync_config
    print("Current Swarm State:")
    print(json.dumps(current_swarm_state, indent=2))

    print("\nSimulating update with invalid Agent ID...")
    success_fail = update_agent_state(
        agent_id="Agent-9 (Ghost)",  # This agent is not in the hardcoded list or demo store
        status="Error",
    )
    print(f"Invalid Agent Update Success: {success_fail}")

    print("\nDemonstration complete.")
