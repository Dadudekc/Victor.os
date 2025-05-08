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
from typing import Any, Dict, Optional

from dreamos.core.config import AppConfig, get_config
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


# --- Helper to get swarm sync config ---
def _get_sync_config(key: str, default: Any, config: Optional[AppConfig] = None) -> Any:
    """Safely retrieves a configuration value related to swarm synchronization.

    Looks for the key within the 'coordination.swarm_sync' section of the AppConfig.
    If the key is not found or the section doesn't exist, returns the provided default.

    Args:
        key: The specific configuration key to retrieve (e.g., 'state_file_path').
        default: The default value to return if the key is not found.
        config: An optional AppConfig instance. If None, a default AppConfig is used.

    Returns:
        The retrieved configuration value or the default.
    """
    app_config = config if config is not None else AppConfig()
    return get_config(f"coordination.swarm_sync.{key}", default, config_obj=app_config)


# --- Core Functions ---


def read_swarm_state(app_config: Optional[AppConfig] = None) -> Dict[str, Any]:
    """Reads the entire current swarm state from the shared file.
    File path is determined by AppConfig, defaulting to runtime/swarm_sync_state.json.
    """
    state_file_path_str = _get_sync_config(
        "state_file_path", "runtime/swarm_sync_state.json", app_config
    )
    state_file_path = Path(state_file_path_str)
    # Ensure path is resolved (AppConfig should ideally handle this, but being explicit here)
    if not state_file_path.is_absolute():
        # Basic assumption: relative to a project root known to AppConfig or runtime dir
        # This might need AppConfig.resolve_path(state_file_path_str) if such method exists
        # For now, simple resolve, assuming AppConfig sets up project_root correctly if needed.
        try:
            # Try to get project_root if available in config, else CWD
            # This is a transitional step. Ideally AppConfig.get_path("coordination.swarm_sync.state_file_path") handles full resolution.
            runtime_base = Path(
                get_config(
                    "paths.runtime",
                    ".",
                    config_obj=app_config if app_config else AppConfig(),
                )
            )
            state_file_path = (runtime_base / state_file_path).resolve()
        except Exception:
            state_file_path = state_file_path.resolve()
            logger.warning(
                f"Could not robustly resolve relative state_file_path '{state_file_path_str}'. Using CWD-resolved: {state_file_path}"
            )

    if not state_file_path.exists():
        logger.warning(
            f"Swarm state file not found: {state_file_path}. Returning empty state."
        )
        return {}

    try:
        with open(state_file_path, "r", encoding="utf-8") as f:
            state = json.load(f)
            if not isinstance(state, dict):
                logger.error(
                    f"Swarm state file {state_file_path} does not contain a valid JSON object. Returning empty state."
                )
                return {}
            logger.debug(f"Read swarm state successfully from {state_file_path}.")
            return state
    except json.JSONDecodeError:
        logger.error(
            f"Swarm state file {state_file_path} contains invalid JSON. Returning empty state.",
            exc_info=True,
        )
        return {}
    except OSError as e:
        logger.error(
            f"Error reading swarm state file {state_file_path}: {e}. Returning empty state.",
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
    current_module: str,
    current_cycle: int,
    status: str,
    health_notes: str = "OK",
    app_config_override: Optional[AppConfig] = None,
) -> bool:
    """Updates the state for a specific agent in the shared file using an atomic rename.
    Uses AppConfig for file paths (defaulting to runtime/swarm_sync_state.json) and retry parameters.
    """
    cfg_instance = (
        app_config_override if app_config_override is not None else AppConfig()
    )
    state_file_path_str = _get_sync_config(
        "state_file_path", "runtime/swarm_sync_state.json", cfg_instance
    )
    state_file_path = Path(state_file_path_str)
    # Path resolution similar to read_swarm_state
    if not state_file_path.is_absolute():
        try:
            runtime_base = Path(
                get_config("paths.runtime", ".", config_obj=cfg_instance)
            )
            state_file_path = (runtime_base / state_file_path).resolve()
        except Exception:
            state_file_path = state_file_path.resolve()
            logger.warning(
                f"Could not robustly resolve relative state_file_path '{state_file_path_str}'. Using CWD-resolved: {state_file_path}"
            )

    max_attempts = _get_sync_config("max_update_attempts", 3, cfg_instance)
    min_delay_ms = _get_sync_config("retry_delay_min_ms", 50, cfg_instance)
    max_delay_ms = _get_sync_config("retry_delay_max_ms", 200, cfg_instance)

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
        "current_module": current_module,
        "current_cycle": current_cycle,
        "status": status,
        "health_notes": health_notes,
    }

    tmp_filename = Path("")  # Initialize for potential cleanup access
    for attempt in range(max_attempts):
        logger.debug(
            f"Attempt {attempt + 1}/{max_attempts} to update state for {agent_id}"
        )
        try:
            current_state = read_swarm_state(app_config=cfg_instance)  # Pass config
            current_state[agent_id] = new_state_entry
            tmp_filename = (
                state_file_path.parent
                / f"{state_file_path.name}.tmp.{os.getpid()}.{uuid.uuid4()}"
            )
            # Ensure parent directory exists for tmp_filename
            tmp_filename.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp_filename, "w", encoding="utf-8") as f_tmp:
                json.dump(current_state, f_tmp, indent=2)
            os.replace(tmp_filename, state_file_path)
            logger.info(
                f"Successfully updated state for {agent_id} (Module: {current_module}, Cycle: {current_cycle}, Status: {status})"
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
        if attempt < max_attempts - 1:
            delay = random.uniform(min_delay_ms, max_delay_ms) / 1000.0
            logger.info(f"Retrying update for {agent_id} after {delay:.3f}s delay.")
            time.sleep(delay)
    logger.error(
        f"Failed to update state for {agent_id} after {max_attempts} attempts."
    )
    return False


# --- Example Usage (for testing/demonstration) ---
if __name__ == "__main__":
    print("Demonstrating Swarm Sync functions (with AppConfig)...")
    # For this demo, AppConfig would need to be set up with coordination.swarm_sync keys
    # or defaults will be used.
    # Example: You might create a temporary AppConfig instance for the demo if needed.
    # demo_app_config = AppConfig() # Or load a specific test config

    # Ensure runtime directory exists for default state file path
    default_state_file_path = Path(
        _get_sync_config("state_file_path", "runtime/swarm_sync_state.json", None)
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
        current_module="Module 5: Swarm State Synchronizer",
        current_cycle=15,
        status="Active",
        health_notes="Implementing core logic",
    )
    print(f"Agent 1 Update Success: {success1}")

    print("\nAgent 2 updating state...")
    success2 = update_agent_state(
        agent_id="Agent-2 (Glasspulse)",
        current_module="Module X: Unknown",
        current_cycle=5,
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
        current_module="N/A",
        current_cycle=0,
        status="Error",
    )
    print(f"Invalid Agent Update Success: {success_fail}")

    print("\nDemonstration complete.")
