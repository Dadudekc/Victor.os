"""Utilities specifically for agent onboarding processes."""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Import filelock library - Assuming it's a standard dependency
# If not, this task might need to propose adding it first.
try:
    import filelock

    FILELOCK_AVAILABLE = True
except ImportError:
    FILELOCK_AVAILABLE = False
    logger.warning(
        "filelock library not found. Contract updates will not be concurrency-safe."
    )

logger = logging.getLogger(__name__)


def calculate_file_sha256(file_path: str | Path) -> str | None:
    """
    Calculates the SHA256 hash of a file.

    Args:
        file_path: The path to the file.

    Returns:
        The hex digest of the SHA256 hash, or None if the file cannot be read.
    """
    try:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as file:
            while True:
                chunk = file.read(4096)  # Read in chunks
                if not chunk:
                    break
                hasher.update(chunk)
        hex_hash = hasher.hexdigest()
        logger.debug(f"Calculated SHA256 hash for {file_path}: {hex_hash}")
        return hex_hash
    except FileNotFoundError:
        logger.error(f"Cannot calculate hash: File not found at {file_path}")
        return None
    except IOError as e:
        logger.error(f"Cannot calculate hash: IO error reading file {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error calculating hash for {file_path}: {e}", exc_info=True
        )
        return None


# Define the expected path relative to project root (adjust if needed based on config)
DEFAULT_CONTRACT_FILE_PATH = "runtime/agent_registry/agent_onboarding_contracts.yaml"
LOCK_TIMEOUT_SECONDS = 15  # Add a timeout for acquiring the lock


# Helper to get current timestamp
def _get_current_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def update_onboarding_contract(
    agent_id: str,
    protocol_file_path: str | Path,
    contract_file_path: str | Path = DEFAULT_CONTRACT_FILE_PATH,
    project_root: str | Path = ".",
) -> bool:
    """
    Automates the agent onboarding contract affirmation step.
    Calculates the hash of the protocol file and updates the contract YAML file.

    Args:
        agent_id: The ID of the agent affirming the contract.
        protocol_file_path: Path to the protocol document (e.g., onboarding_protocols.md).
        contract_file_path: Path to the YAML contract registry file.
        project_root: The root directory of the project, used for resolving relative paths.

    Returns:
        True if the contract was successfully updated, False otherwise.
    """
    project_root_path = Path(project_root).resolve()
    full_protocol_path = (project_root_path / protocol_file_path).resolve()
    full_contract_path = (project_root_path / contract_file_path).resolve()

    logger.info(
        f"[{agent_id}] Attempting contract affirmation. Protocol: {full_protocol_path}, Registry: {full_contract_path}"
    )

    # 1. Calculate protocol hash
    protocol_hash = calculate_file_sha256(full_protocol_path)
    if not protocol_hash:
        logger.error(
            f"[{agent_id}] Contract affirmation failed: Could not calculate hash for {full_protocol_path}"
        )
        return False

    # 2. Define lock file path
    lock_file_path = full_contract_path.with_suffix(full_contract_path.suffix + ".lock")
    lock = None

    try:
        # 3. Acquire Lock (if library available)
        if FILELOCK_AVAILABLE:
            try:
                lock = filelock.FileLock(lock_file_path, timeout=LOCK_TIMEOUT_SECONDS)
                lock.acquire()
                logger.info(f"[{agent_id}] Acquired lock: {lock_file_path}")
            except filelock.Timeout:
                logger.error(
                    f"[{agent_id}] Contract affirmation failed: Timeout acquiring lock {lock_file_path} after {LOCK_TIMEOUT_SECONDS} seconds."
                )
                return False
            except Exception as e:
                logger.error(
                    f"[{agent_id}] Contract affirmation failed: Error acquiring lock {lock_file_path}: {e}",
                    exc_info=True,
                )
                return False
        else:
            # Fallback or warning if filelock isn't available
            logger.warning(
                f"[{agent_id}] Proceeding without file lock due to missing library."
            )

        # 4. Load existing contract data (now inside lock context)
        contracts = {}
        try:
            # Ensure directory exists
            full_contract_path.parent.mkdir(parents=True, exist_ok=True)

            if full_contract_path.exists():
                with open(full_contract_path, "r", encoding="utf-8") as f:
                    contracts = yaml.safe_load(f) or {}
            else:
                logger.warning(
                    f"Contract file not found at {full_contract_path}, creating a new one."
                )
                # contracts already initialized to {}

        except yaml.YAMLError as e:
            logger.error(
                f"[{agent_id}] Contract affirmation failed (inside lock): Error reading YAML file {full_contract_path}: {e}"
            )
            return False  # Exit before writing
        except IOError as e:
            logger.error(
                f"[{agent_id}] Contract affirmation failed (inside lock): IO error reading file {full_contract_path}: {e}"
            )
            return False  # Exit before writing
        except Exception as e:
            logger.error(
                f"[{agent_id}] Unexpected error loading contract file {full_contract_path} (inside lock): {e}",
                exc_info=True,
            )
            return False  # Exit before writing

        # 5. Prepare updated entry
        affirmation_timestamp = _get_current_utc_iso()
        new_entry = {
            "protocol_hash": protocol_hash.upper(),  # Match case from simulation
            "timestamp_utc": affirmation_timestamp,
        }

        # 6. Update or add the agent's entry
        contracts[agent_id] = new_entry
        logger.info(
            f"[{agent_id}] Prepared contract entry. Hash: {protocol_hash.upper()}, Timestamp: {affirmation_timestamp}"
        )

        # 7. Write updated data back (atomically if possible, otherwise basic write)
        try:
            # Basic write (less safe during concurrent access, but simpler)
            # Write with default_flow_style=False for block style YAML
            with open(full_contract_path, "w", encoding="utf-8") as f:
                yaml.dump(contracts, f, default_flow_style=False, sort_keys=False)
            logger.info(
                f"[{agent_id}] Successfully updated onboarding contract file: {full_contract_path}"
            )
            # Success happens here, before releasing lock
            return True
        except IOError as e:
            logger.error(
                f"[{agent_id}] Contract affirmation failed (inside lock): IO error writing file {full_contract_path}: {e}"
            )
            return False
        except yaml.YAMLError as e:
            logger.error(
                f"[{agent_id}] Contract affirmation failed (inside lock): Error writing YAML file {full_contract_path}: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"[{agent_id}] Unexpected error writing contract file {full_contract_path} (inside lock): {e}",
                exc_info=True,
            )
            return False

    finally:
        # 8. Release Lock (if acquired)
        if lock and lock.is_locked:
            try:
                lock.release()
                logger.info(f"[{agent_id}] Released lock: {lock_file_path}")
            except Exception as e:
                # Log error but don't prevent potential return value from try block
                logger.error(
                    f"[{agent_id}] Error releasing lock {lock_file_path}: {e}",
                    exc_info=True,
                )

    # Fallthrough case (shouldn't be reached if logic is correct, but ensures False return if error occurs before explicit returns)
    return False

    # TODO (Future): Implement safer atomic write using temporary files + rename
    #               (Can be done within the file lock for extra safety)
    # -- Original non-locked write logic removed --
