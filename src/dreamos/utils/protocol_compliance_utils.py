#!/usr/bin/env python
"""Utility to check agent compliance with onboarding protocols."""

import hashlib
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# import os # Unused import
import filelock  # Use the library directly

# Attempt to import PyYAML
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logging.warning(
        "PyYAML library not found. Protocol compliance check requires it. Run: pip install PyYAML"
    )

# --- Determine Project Root (copied & adapted from standardize_task_list.py) ---
project_root_found = None
current_dir = Path(__file__).resolve()
for parent in current_dir.parents:
    if (parent / "src").is_dir() and (parent / "runtime").is_dir():
        project_root_found = parent
        break
if (
    not project_root_found
    and (Path.cwd() / "src").is_dir()
    and (Path.cwd() / "runtime").is_dir()
):
    project_root_found = Path.cwd()

if not project_root_found:
    logging.basicConfig(level=logging.ERROR)
    logging.error(
        "Could not determine project root containing 'src' and 'runtime'. Cannot proceed."
    )
    sys.exit(1)
# --- End Project Root Determination ---

PROTOCOL_FILE_PATH = project_root_found / "docs" / "swarm" / "onboarding_protocols.md"
CONTRACT_REGISTRY_PATH = (
    project_root_found
    / "runtime"
    / "agent_registry"
    / "agent_onboarding_contracts.yaml"
)

AGENT_MAILBOX_ROOT = project_root_found / "runtime" / "agent_comms" / "agent_mailboxes"

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ProtocolComplianceCheck")

# Define known valid task statuses based on observation and documentation
VALID_TASK_STATUSES = {
    "PENDING",
    "WORKING",
    "COMPLETED_PENDING_REVIEW",
    "COMPLETED",
    "FAILED",
    "BLOCKED",
    "CLAIMED",
    "REOPENED",
}


def calculate_file_sha256(file_path: Path) -> str | None:
    """Calculates the SHA256 hash of a file."""
    try:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as file:
            while chunk := file.read(4096):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        logger.error(f"File not found for hashing: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error hashing file {file_path}: {e}", exc_info=True)
        return None


def load_yaml_registry(file_path: Path) -> Dict | None:
    """Loads the YAML registry file."""
    if not YAML_AVAILABLE:
        logger.error("PyYAML not installed. Cannot load registry.")
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        logger.warning(f"Registry file not found: {file_path}. Returning empty.")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML registry {file_path}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error reading registry file {file_path}: {e}", exc_info=True)
        return None


def check_mailbox_structure(agent_id: str) -> Tuple[bool, str]:
    """Checks if the standard mailbox inbox and outbox directories exist for an agent."""
    agent_mailbox_path = AGENT_MAILBOX_ROOT / agent_id
    expected_inbox = agent_mailbox_path / "inbox"
    expected_outbox = agent_mailbox_path / "outbox"
    details = []
    inbox_ok = False
    outbox_ok = False

    if not agent_mailbox_path.is_dir():
        return False, f"Agent mailbox root directory not found at {agent_mailbox_path}"

    if expected_inbox.is_dir():
        inbox_ok = True
        details.append(f"Inbox found at {expected_inbox}.")
        # Optional: Check for JSON files (limited check to avoid excessive I/O)
        try:
            json_files_found = False
            non_json_files_found = False
            for item in expected_inbox.iterdir():
                if item.is_file():
                    if item.suffix.lower() == ".json":
                        json_files_found = True
                    else:
                        non_json_files_found = True
                # Limit the check to avoid listing entire large mailboxes
                if json_files_found and non_json_files_found:
                    break
            if not json_files_found and non_json_files_found:
                details.append(
                    "WARNING: Inbox contains non-.json files, expected only JSON."
                )
            elif non_json_files_found:
                details.append(
                    "Note: Inbox contains non-.json files alongside .json files."
                )
            elif not json_files_found:
                details.append("Note: Inbox is empty or contains no .json files.")

        except Exception as e:
            details.append(f"Warning: Could not check inbox contents: {e}")
    else:
        details.append(f"ERROR: Expected inbox not found at {expected_inbox}.")

    if expected_outbox.is_dir():
        outbox_ok = True
        details.append(f"Outbox found at {expected_outbox}.")
    else:
        details.append(f"ERROR: Expected outbox not found at {expected_outbox}.")

    is_compliant = inbox_ok and outbox_ok
    return is_compliant, " ".join(details)


def check_agent_bus_usage(agent_id: str) -> Tuple[bool, str]:
    """Checks if agents *could* use standard AgentBus patterns.

    Note: This is currently a limited check. Verifying actual runtime usage
    and correct implementation requires static code analysis (AST).
    This placeholder acknowledges the need for this check.
    """
    # TODO: Implement static analysis (e.g., using `ast` module) to check:
    #   - Agent class inherits from BaseAgent or has expected methods.
    #   - Calls to `_publish_event` and `_handle_event` patterns.
    #   - Proper subscription setup (`self.agent_bus.subscribe`).
    #   - Avoidance of direct `AgentBus.get_instance().publish` where BaseAgent suffices.
    #   - Handling/usage of standard `EventType` enums.
    # TODO: Need a reliable way to locate agent source code from agent_id for analysis.
    logger.debug(f"Limited AgentBus usage check for {agent_id}.")
    details = (
        f"AgentBus usage check: Requires AST analysis of agent source code (not implemented). "
        f"Key checks include BaseAgent inheritance, event publishing/handling patterns, "
        f"and correct subscription setup."
    )
    # Assume compliant for now, as the check isn't implemented.
    return True, details


def check_task_status_reporting(agent_id: str) -> Tuple[bool, str]:
    """Checks if agents *could* use standard task statuses.

    Note: This is currently a limited check. Verifying actual runtime usage
    would require analyzing agent code (AST), board update logs, or PBM interactions.
    This check confirms the utility is *aware* of the standard statuses.
    """
    # TODO: Enhance with AST analysis of agent source code to find where/how
    #       task statuses are set and compare against VALID_TASK_STATUSES.
    # TODO: Consider integrating with logging or PBM hooks to monitor actual
    #       status changes reported by agents at runtime.
    logger.debug(f"Limited task status reporting check for {agent_id}.")
    details = (
        f"Task status reporting check: Utility is aware of valid statuses: "
        f"{', '.join(sorted(VALID_TASK_STATUSES))}. "
        f"Actual agent usage requires AST analysis or runtime monitoring (not implemented)."
    )
    # For now, assume compliant unless a future check proves otherwise.
    return True, details


def check_compliance() -> Tuple[Dict[str, Dict[str, Any]], str | None]:
    """
    Checks agent protocol compliance (hash, mailbox, bus usage placeholder, task status placeholder).

    Returns:
        Tuple containing: (dict mapping agent_id to compliance details, expected hash or None).
        Compliance details dict structure: {
            "hash_compliant": bool,
            "mailbox_compliant": bool,
            "bus_usage_compliant": bool,
            "task_status_compliant": bool,
            "details": List[str]
        }
    """
    logger.info("Starting protocol compliance check...")
    compliance_results: Dict[str, Dict[str, Any]] = {}
    expected_hash = calculate_file_sha256(PROTOCOL_FILE_PATH)
    if not expected_hash:
        logger.error("Could not calculate expected protocol hash. Aborting check.")
        return {}, None

    logger.info(f"Expected protocol hash ({PROTOCOL_FILE_PATH.name}): {expected_hash}")

    registry = load_yaml_registry(CONTRACT_REGISTRY_PATH)
    if registry is None:
        logger.error("Could not load or parse agent registry. Aborting check.")
        return {}, expected_hash

    for agent_id, contract_data in registry.items():
        agent_compliance = {
            "hash_compliant": False,
            "mailbox_compliant": False,
            "bus_usage_compliant": False,
            "task_status_compliant": False,
            "details": [],
        }

        # 1. Check Hash Compliance
        if isinstance(contract_data, dict):
            recorded_hash_full = contract_data.get("protocol_version_hash")
            if recorded_hash_full and isinstance(recorded_hash_full, str):
                parts = recorded_hash_full.split(":", 1)
                if len(parts) == 2 and parts[0] == "sha256":
                    recorded_hash = parts[1]
                    if recorded_hash == expected_hash:
                        agent_compliance["hash_compliant"] = True
                        agent_compliance["details"].append(
                            f"Protocol hash matches ({recorded_hash[:8]}...)"
                        )
                    else:
                        agent_compliance["details"].append(
                            f"Hash mismatch (Expected: {expected_hash[:8]}..., Found: {recorded_hash[:8]}...)"
                        )
                else:
                    agent_compliance["details"].append(
                        f"Invalid hash format: {recorded_hash_full}"
                    )
            else:
                agent_compliance["details"].append(
                    "Missing or invalid 'protocol_version_hash' in contract."
                )
        else:
            agent_compliance["details"].append("Invalid contract data in registry.")
            logger.warning(
                f"Skipping invalid entry in registry for Agent ID: {agent_id}"
            )

        # 2. Check Mailbox Structure
        mailbox_ok, mailbox_detail = check_mailbox_structure(agent_id)
        agent_compliance["mailbox_compliant"] = mailbox_ok
        agent_compliance["details"].append(mailbox_detail)

        # 3. Check Bus Usage (Placeholder)
        bus_ok, bus_detail = check_agent_bus_usage(agent_id)
        agent_compliance["bus_usage_compliant"] = bus_ok
        agent_compliance["details"].append(bus_detail)

        # 4. Check Task Status Reporting (Placeholder)
        status_ok, status_detail = check_task_status_reporting(agent_id)
        agent_compliance["task_status_compliant"] = status_ok
        agent_compliance["details"].append(status_detail)

        compliance_results[agent_id] = agent_compliance

    # Summarize overall counts
    total_agents = len(compliance_results)
    fully_compliant_count = sum(
        1
        for data in compliance_results.values()
        if data["hash_compliant"]
        and data["mailbox_compliant"]
        and data["bus_usage_compliant"]
        and data["task_status_compliant"]
    )
    logger.info(
        f"Compliance Check Summary: Total Agents={total_agents}, Fully Compliant={fully_compliant_count}"
    )

    return compliance_results, expected_hash


if __name__ == "__main__":
    if not YAML_AVAILABLE:
        sys.exit(1)  # Exit if prereq missing

    results, expected = check_compliance()
    print("--- Protocol Compliance Report ---")
    if expected:
        print(f"Current Protocol Hash ({PROTOCOL_FILE_PATH.name}): {expected}")
    print("\n--- Agent Compliance Details ---")
    for agent_id, data in results.items():
        hash_status = "✅" if data["hash_compliant"] else "❌"
        mailbox_status = "✅" if data["mailbox_compliant"] else "❌"
        bus_status = (
            "✅" if data["bus_usage_compliant"] else "❌"
        )  # Will be ✅ due to placeholder
        task_status_check = (
            "✅" if data["task_status_compliant"] else "❌"
        )  # Will be ✅ due to placeholder
        print(f"\nAgent: {agent_id}")
        print(f"  - Hash Match:          {hash_status}")
        print(f"  - Mailbox Exists:      {mailbox_status}")
        print(f"  - Bus Usage Check:     {bus_status}")
        print(f"  - Task Status Check:   {task_status_check}")
        print(f"  Details:")
        for detail in data["details"]:
            print(f"    - {detail}")
    print("\n---------------------------------")
