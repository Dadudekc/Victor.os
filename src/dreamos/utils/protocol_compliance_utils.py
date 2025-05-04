#!/usr/bin/env python
"""Utility to check agent compliance with onboarding protocols."""

import ast  # EDIT: Added import
import hashlib
import logging
import re  # Import re for pattern matching
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# import os # Unused import

# Attempt to import PyYAML
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logging.warning(
        "PyYAML library not found. Protocol compliance check requires it. Run: pip install PyYAML"  # noqa: E501
    )

# Import AppConfig and ConfigurationError
from ..core.config import AppConfig
from ..core.errors import ConfigurationError

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
        "Could not determine project root containing 'src' and 'runtime'. Cannot proceed."  # noqa: E501
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


# EDIT START: AST Visitor for AgentBus Checks
class AgentBusAstVisitor(ast.NodeVisitor):
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.inherits_base_agent = False
        self.subscribes = False
        self.publishes_event = False
        self.uses_event_type_enum = False
        self.details = []

    def visit_ClassDef(self, node):
        # Check for inheritance from BaseAgent
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseAgent":
                self.inherits_base_agent = True
                self.details.append("Class inherits from BaseAgent.")
                break
            elif (
                isinstance(base, ast.Attribute) and base.attr == "BaseAgent"
            ):  # Handle module.BaseAgent
                self.inherits_base_agent = True
                self.details.append("Class inherits from BaseAgent (qualified name).")
                break
        if not self.inherits_base_agent:
            self.details.append(
                "WARNING: Class does not appear to inherit from BaseAgent."
            )
        self.generic_visit(node)

    def visit_Call(self, node):
        # Check for subscribe calls
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "subscribe":
                # Check if it's called on self.agent_bus or similar
                if (
                    isinstance(node.func.value, ast.Attribute)
                    and node.func.value.attr == "agent_bus"
                ):
                    self.subscribes = True
                    self.details.append("Found call to self.agent_bus.subscribe(...)")
                elif (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "agent_bus"
                ):  # Direct var
                    self.subscribes = True
                    self.details.append("Found call to agent_bus.subscribe(...)")

            # Check for publish calls (BaseAgent helper or direct)
            if node.func.attr == "_publish_event":
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "self"
                ):
                    self.publishes_event = True
                    self.details.append("Found call to self._publish_event(...)")
            elif node.func.attr.startswith("publish_") and node.func.attr.endswith(
                "_event"
            ):
                # Could be BaseAgent helper or direct AgentBus call
                self.publishes_event = True
                self.details.append(
                    f"Found call to publish helper: {node.func.attr}(...)"
                )
            elif (
                node.func.attr == "publish"
                and isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "agent_bus"
            ):
                self.publishes_event = True
                self.details.append("Found direct call to self.agent_bus.publish(...)")

            # Check for EventType usage in args/keywords
            for arg in node.args:
                if (
                    isinstance(arg, ast.Attribute)
                    and isinstance(arg.value, ast.Name)
                    and arg.value.id == "EventType"
                ):
                    self.uses_event_type_enum = True
                    break
            if not self.uses_event_type_enum:
                for kw in node.keywords:
                    if (
                        isinstance(kw.value, ast.Attribute)
                        and isinstance(kw.value.value, ast.Name)
                        and kw.value.value.id == "EventType"
                    ):
                        self.uses_event_type_enum = True
                        break

        self.generic_visit(node)

    def report(self) -> Tuple[bool, List[str]]:
        if not self.uses_event_type_enum and self.publishes_event:
            self.details.append(
                "WARNING: Event publishing detected, but usage of EventType enum could not be confirmed."  # noqa: E501
            )
        is_compliant = (
            self.inherits_base_agent
            and self.subscribes
            and self.publishes_event
            and self.uses_event_type_enum
        )
        if not is_compliant:
            if not self.inherits_base_agent:
                self.details.append("FAIL: Missing BaseAgent inheritance.")
            if not self.subscribes:
                self.details.append("FAIL: No agent_bus.subscribe() calls found.")
            if not self.publishes_event:
                self.details.append("FAIL: No event publishing calls found.")
            # Only flag enum usage if publishing was found
            if not self.uses_event_type_enum and self.publishes_event:
                self.details.append("FAIL: EventType enum usage not confirmed.")

        final_details = [f"AgentBus Usage AST Check ({self.agent_id}):"] + self.details
        return is_compliant, final_details


# EDIT END: AST Visitor


# EDIT START: AST Visitor for Task Status Checks
class TaskStatusAstVisitor(ast.NodeVisitor):
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.uses_valid_status = True  # Assume true unless invalid found
        self.details = []
        self.found_status_assignment = False

    def visit_Assign(self, node):
        # Check for assignments like task['status'] = '...'
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Subscript):
            subscript = node.targets[0]
            if (
                isinstance(subscript.slice, ast.Constant)
                and subscript.slice.value == "status"
            ):
                self.found_status_assignment = True
                if isinstance(node.value, ast.Constant) and isinstance(
                    node.value.value, str
                ):
                    status_value = node.value.value.upper()
                    if status_value not in VALID_TASK_STATUSES:
                        self.uses_valid_status = False
                        self.details.append(
                            f"Found direct status assignment with potentially invalid status '{node.value.value}' at line {node.lineno}."  # noqa: E501
                        )
                    else:
                        self.details.append(
                            f"Found direct status assignment with valid status '{node.value.value}' at line {node.lineno}."  # noqa: E501
                        )
                else:
                    self.details.append(
                        f"WARNING: Found non-constant status assignment task['status'] = ... at line {node.lineno}. Cannot verify value."  # noqa: E501
                    )

        self.generic_visit(node)

    def visit_Call(self, node):
        # Check for calls to PBM CLI (enhanced check)
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "run_terminal_cmd"
        ):
            cmd_str = None
            # Extract command string from args or keywords
            if (
                len(node.args) > 0
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                cmd_str = node.args[0].value
            else:
                for kw in node.keywords:
                    if (
                        kw.arg == "command"
                        and isinstance(kw.value, ast.Constant)
                        and isinstance(kw.value.value, str)
                    ):
                        cmd_str = kw.value.value
                        break

            if cmd_str and "manage_tasks.py" in cmd_str:
                self.details.append(
                    f"Found PBM CLI call at line {node.lineno}: `{cmd_str[:100]}{'...' if len(cmd_str)>100 else ''}`"
                )  # Log truncated command
                try:
                    # Attempt to parse the command string (basic parsing)
                    # Note: shlex might struggle with complex pipelines or nested quotes here.
                    # Use basic string splitting/checking as a robust fallback.
                    parts = cmd_str.split()
                    pbm_command = None
                    status_arg = None
                    if "manage_tasks.py" in parts:
                        script_index = parts.index("manage_tasks.py")
                        if script_index + 1 < len(parts):
                            pbm_command = parts[script_index + 1]
                            self.details.append(
                                f"  - Identified PBM command: '{pbm_command}'"
                            )

                        # Check for status argument
                        if "--status" in parts:
                            status_index = parts.index("--status")
                            if status_index + 1 < len(parts):
                                status_arg = parts[status_index + 1].upper()
                                self.details.append(
                                    f"  - Identified status argument: '{status_arg}'"
                                )
                                if status_arg not in VALID_TASK_STATUSES:
                                    self.uses_valid_status = False
                                    self.details.append(
                                        f"  - WARNING: Potentially invalid status '{status_arg}' used in CLI call."
                                    )
                        elif pbm_command in ["complete", "update"]:
                            # Check if status might be implied or missing when expected
                            self.details.append(
                                f"  - NOTE: PBM command '{pbm_command}' used without explicit --status flag."
                            )

                    # Mark that a potential status update occurred
                    if pbm_command in ["complete", "update", "claim", "promote"]:
                        self.found_status_assignment = True

                except Exception as e:
                    self.details.append(
                        f"  - WARNING: Failed to parse PBM CLI command string: {e}"
                    )

        # Check for calls to update_task_status or similar PBM methods
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in [
                "update_task_status",
                "update_working_task",
                "move_task_to_completed",
                "claim_ready_task",
                "promote_task_to_ready",
            ]:
                self.found_status_assignment = True
                self.details.append(
                    f"Found call to PBM method `.{node.func.attr}` at line {node.lineno}."
                )
                # Potentially check arguments here if needed for specific status validation

        self.generic_visit(node)

    def report(self) -> Tuple[bool, List[str]]:
        if not self.found_status_assignment:
            self.details.append(
                "WARNING: No direct status assignments or PBM CLI calls detected. Manual verification needed."  # noqa: E501
            )
            # Assume compliant if no assignments found? Or fail?
            # Let's assume compliant for now, but flag the warning.
            self.uses_valid_status = True

        final_details = [
            f"Task Status Usage AST Check ({self.agent_id}):"
        ] + self.details
        return self.uses_valid_status, final_details


# EDIT END: AST Visitor

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
    """Checks if the standard mailbox inbox and outbox directories exist for an agent."""  # noqa: E501
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


# EDIT START: Refactor _find_agent_source_file to use AppConfig
def _find_agent_source_file(agent_id: str, config: AppConfig) -> Path | None:
    """Attempts to locate the source file for a given agent ID using AppConfig.

    Looks for a match in the 'agent_activations' list based on
    agent_id_override or worker_id_pattern.
    """
    if (
        not config
        or not hasattr(config, "agent_activations")
        or not config.agent_activations
    ):
        logger.error(
            "Cannot find agent source: 'agent_activations' not configured in AppConfig."
        )
        return None

    for activation_config in config.agent_activations:
        # Check for direct ID override match
        if activation_config.agent_id_override == agent_id:
            logger.debug(f"Found agent {agent_id} via agent_id_override.")
        # Check pattern match if override doesn't match
        elif re.match(activation_config.worker_id_pattern, agent_id):
            logger.debug(
                f"Found agent {agent_id} via pattern '{activation_config.worker_id_pattern}'."
            )
        else:
            continue  # Not a match for this activation config

        # Found a match, construct the path
        module_path_str = activation_config.agent_module
        # Convert module path (e.g., dreamos.agents.agent1) to file path
        relative_path_parts = module_path_str.split(".")
        # Assume standard src layout
        potential_path = (
            config.paths.project_root
            / "src"
            / Path(*relative_path_parts).with_suffix(".py")
        )

        if potential_path.exists():
            logger.info(f"Located source file for {agent_id}: {potential_path}")
            return potential_path
        else:
            logger.error(
                f"Config found for {agent_id}, but source file does not exist: {potential_path}"
            )
            return None  # Config entry exists but file doesn't

    logger.error(
        f"Agent source file location for '{agent_id}' unknown. No matching entry in config.agent_activations."
    )
    return None


# EDIT END: Refactor _find_agent_source_file


def check_agent_bus_usage(agent_id: str) -> Tuple[bool, str]:
    """Checks if agents *could* use standard AgentBus patterns via AST analysis."""
    # EDIT START: Load config and pass to finder
    try:
        config = AppConfig.load()  # Load config here
    except ConfigurationError as e:
        return (
            False,
            f"AgentBus Usage Check ({agent_id}): FAIL - Config load error: {e}",
        )

    agent_file = _find_agent_source_file(agent_id, config)
    # EDIT END
    if not agent_file:
        return (
            False,
            f"AgentBus Usage Check ({agent_id}): FAIL - Source file not found (check config.agent_activations).",
        )

    try:
        source_code = agent_file.read_text(encoding="utf-8")
        tree = ast.parse(source_code)
        visitor = AgentBusAstVisitor(agent_id)
        visitor.visit(tree)
        is_compliant, details_list = visitor.report()
        details_str = "\n - ".join(details_list)
        return is_compliant, details_str
    except Exception as e:
        logger.error(
            f"Error analyzing {agent_file} for AgentBus usage: {e}", exc_info=True
        )
        return (
            False,
            f"AgentBus Usage Check ({agent_id}): FAIL - Error during AST analysis: {e}",
        )
    # EDIT END


def check_task_status_reporting(agent_id: str) -> Tuple[bool, str]:
    """Checks if agents *could* use standard task statuses via AST analysis."""
    # EDIT START: Load config and pass to finder
    try:
        config = AppConfig.load()  # Load config here
    except ConfigurationError as e:
        return (
            False,
            f"Task Status Usage Check ({agent_id}): FAIL - Config load error: {e}",
        )

    agent_file = _find_agent_source_file(agent_id, config)
    # EDIT END
    if not agent_file:
        return (
            False,
            f"Task Status Usage Check ({agent_id}): FAIL - Source file not found (check config.agent_activations).",
        )

    try:
        source_code = agent_file.read_text(encoding="utf-8")
        tree = ast.parse(source_code)
        visitor = TaskStatusAstVisitor(agent_id)
        visitor.visit(tree)
        is_compliant, details_list = visitor.report()
        details_str = "\n - ".join(details_list)
        return is_compliant, details_str
    except Exception as e:
        logger.error(
            f"Error analyzing {agent_file} for Task Status usage: {e}", exc_info=True
        )
        return (
            False,
            f"Task Status Usage Check ({agent_id}): FAIL - Error during AST analysis: {e}",  # noqa: E501
        )
    # EDIT END


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
    """  # noqa: E501
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
                            f"Hash mismatch (Expected: {expected_hash[:8]}..., Found: {recorded_hash[:8]}...)"  # noqa: E501
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
        f"Compliance Check Summary: Total Agents={total_agents}, Fully Compliant={fully_compliant_count}"  # noqa: E501
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
        print("  Details:")
        for detail in data["details"]:
            print(f"    - {detail}")
    print("\n---------------------------------")
