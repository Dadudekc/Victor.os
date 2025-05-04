import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import yaml

# Import the async FileLock
from dreamos.core.utils.file_locking import (
    FileLock,
    LockAcquisitionError,
    LockDirectoryError,
)

# Type checking imports
if TYPE_CHECKING:
    from dreamos.core.config import AppConfig  # Import AppConfig for type hint

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# REMOVED Hardcoded Paths
# ONBOARDING_PROTOCOLS_PATH = ...
# CONTRACTS_YAML_PATH = ...
MAX_LOCK_WAIT_SECONDS = 30


async def affirm_onboarding_contract(
    agent_id: str,
    agent_name: str,
    config: "AppConfig",  # Accept config object
) -> bool:
    """
    Automates the agent onboarding contract affirmation process (async).

    Reads the onboarding protocols (path from config), calculates its hash,
    gets the current timestamp, and updates the agent_onboarding_contracts.yaml
    file (path from config) with the agent's affirmation using the standardized
    list format under the 'agents' key.
    Uses an async file lock to prevent race conditions.

    Args:
        agent_id: The unique identifier of the agent.
        agent_name: The name of the agent.
        config: The application configuration object containing paths.

    Returns:
        True if the contract was successfully affirmed and updated, False otherwise.
    """
    logger = logging.getLogger(__name__)
    logger.info(
        f"Starting onboarding contract affirmation for Agent {agent_id} ({agent_name})."
    )

    # Get paths from config
    try:
        onboarding_protocols_path = (
            config.paths.runtime.parent / "docs" / "swarm" / "onboarding_protocols.md"
        )  # Adjust path derivation based on config structure
        contracts_yaml_path = (
            config.paths.runtime / "agent_registry" / "agent_onboarding_contracts.yaml"
        )
        # Basic check if paths seem valid (could be more robust)
        if (
            not onboarding_protocols_path.is_absolute()
            or not contracts_yaml_path.is_absolute()
        ):
            raise ValueError("Configuration paths must be absolute")
    except AttributeError as e:
        logger.error(f"Configuration object missing required path attributes: {e}")
        return False
    except ValueError as e:
        logger.error(f"Invalid path configuration: {e}")
        return False

    protocol_hash = None
    utc_timestamp = None

    # 1. Read protocols and calculate hash
    try:
        # Assuming protocols path is now correct from config
        with open(onboarding_protocols_path, "rb") as f:
            protocol_content = f.read()
            protocol_hash = hashlib.sha256(protocol_content).hexdigest()
        logger.info(
            f"Calculated SHA256 hash for {onboarding_protocols_path}: {protocol_hash}"
        )
    except FileNotFoundError:
        logger.error(
            f"Error: Onboarding protocols file not found at {onboarding_protocols_path}"
        )
        return False
    except IOError as e:
        logger.error(
            f"Error reading onboarding protocols file {onboarding_protocols_path}: {e}"
        )
        return False

    # 2. Get timestamp
    utc_timestamp = datetime.now(timezone.utc).isoformat()
    logger.info(f"Generated UTC timestamp: {utc_timestamp}")

    # 3. Acquire lock and update YAML
    try:
        # Use contracts path from config
        async with FileLock(contracts_yaml_path, timeout=MAX_LOCK_WAIT_SECONDS):
            logger.info(f"Acquired lock for: {contracts_yaml_path}")

            # 4. Read YAML
            contracts_data = {"agents": []}  # Initialize with standard structure
            try:
                # Ensure file exists before trying to read YAML
                if contracts_yaml_path.exists():
                    # Use asyncio.to_thread for sync file I/O
                    def read_yaml_sync():
                        with open(contracts_yaml_path, "r", encoding="utf-8") as f:
                            loaded_data = yaml.safe_load(f)
                            # Ensure top-level 'agents' list exists
                            if (
                                isinstance(loaded_data, dict)
                                and "agents" in loaded_data
                                and isinstance(loaded_data["agents"], list)
                            ):
                                return loaded_data
                            else:
                                logger.warning(
                                    f"YAML file {contracts_yaml_path} has unexpected structure. Re-initializing."  # noqa: E501
                                )
                                return {"agents": []}  # Reset if structure is wrong

                    contracts_data = await asyncio.to_thread(read_yaml_sync)
                    logger.info(f"Read existing contracts from {contracts_yaml_path}")
                else:
                    logger.warning(
                        f"{contracts_yaml_path} not found. Will create a new file."
                    )
                    # contracts_data remains {'agents': []}

            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML file {contracts_yaml_path}: {e}")
                return False  # Do not proceed if YAML is corrupt
            except IOError as e:
                logger.error(f"Error reading contracts file {contracts_yaml_path}: {e}")
                return False

            # 5. Update YAML data (Standardized list format)
            agent_list = contracts_data.setdefault("agents", [])
            agent_found = False
            for i, agent_entry in enumerate(agent_list):
                if isinstance(agent_entry, dict) and agent_entry.get("id") == agent_id:
                    # Update existing entry
                    agent_list[i] = {
                        "id": agent_id,
                        "name": agent_name,
                        "contract_hash": protocol_hash,
                        "timestamp_utc": utc_timestamp,
                        "notes": agent_entry.get(
                            "notes", ""
                        ),  # Preserve existing notes if any
                    }
                    agent_found = True
                    logger.info(
                        f"Updated existing contract entry for Agent {agent_id}."
                    )
                    break

            if not agent_found:
                # Append new entry
                agent_list.append(
                    {
                        "id": agent_id,
                        "name": agent_name,
                        "contract_hash": protocol_hash,
                        "timestamp_utc": utc_timestamp,
                        "notes": f"Contract affirmed by {agent_name} ({agent_id}).",  # Add default note  # noqa: E501
                    }
                )
                logger.info(f"Appended new contract entry for Agent {agent_id}.")

            # 6. Write YAML
            try:
                # Use asyncio.to_thread for sync file I/O
                def write_yaml_sync():
                    with open(contracts_yaml_path, "w", encoding="utf-8") as f:
                        yaml.dump(
                            contracts_data, f, default_flow_style=False, sort_keys=False
                        )

                await asyncio.to_thread(write_yaml_sync)
                logger.info(
                    f"Successfully wrote updated contracts to {contracts_yaml_path}"
                )
                # Lock is released automatically by context manager
                logger.info(f"Released lock for: {contracts_yaml_path}")
                return True  # Success!

            except IOError as e:
                logger.error(f"Error writing contracts file {contracts_yaml_path}: {e}")
                return False
            except yaml.YAMLError as e:
                # Less likely during dump, but possible
                logger.error(
                    f"Error formatting data for YAML file {contracts_yaml_path}: {e}"
                )
                return False

    except (LockAcquisitionError, LockDirectoryError) as e:
        logger.error(
            f"Failed to acquire lock or access directory for {contracts_yaml_path}: {e}"
        )
        return False
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred during contract affirmation for {agent_id}: {e}"  # noqa: E501
        )
        return False


# Example usage (optional, for testing) - Needs to be run in an async context
# async def run_example():
#     test_agent_id = "AgentTest001"
#     test_agent_name = "TestAgent"
#     if await affirm_onboarding_contract(test_agent_id, test_agent_name):
#         logger.info(f"Successfully affirmed contract for {test_agent_id}")
#     else:
#         logger.error(f"Failed to affirm contract for {test_agent_id}")

# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     asyncio.run(run_example())
