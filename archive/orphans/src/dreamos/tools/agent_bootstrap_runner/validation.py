"""
Validation utilities for Dream.OS agent bootstrap runner.

Ensures directory structure and message formats comply with docs/agent_system/agent_directory_structure.md
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .config import AgentConfig


@dataclass
class ValidationResult:
    """Result of a validation check."""

    passed: bool
    error: Optional[str] = None


def validate_directory_structure(
    logger: logging.Logger, config: "AgentConfig"
) -> ValidationResult:
    """
    Validate agent directory structure follows documentation.

    Args:
        logger: Logger instance
        config: Agent configuration

    Returns:
        ValidationResult: Validation result
    """
    required_dirs = [
        config.inbox_dir,
        config.outbox_dir,
        config.processed_dir,
        config.state_dir,
        config.workspace_dir,
    ]

    for dir_path in required_dirs:
        if not dir_path.exists():
            return ValidationResult(
                passed=False, error=f"Missing required directory: {dir_path}"
            )

    return ValidationResult(passed=True)


def validate_message_format(message_data: Dict[str, Any]) -> ValidationResult:
    """
    Validate message format follows standard.

    Args:
        message_data: Message data dictionary

    Returns:
        ValidationResult: Validation result
    """
    required_fields = [
        "message_id",
        "sender_agent_id",
        "recipient_agent_id",
        "timestamp_utc",
        "subject",
        "type",
        "body",
    ]

    for field in required_fields:
        if field not in message_data:
            return ValidationResult(
                passed=False, error=f"Missing required field: {field}"
            )

    # Validate agent IDs follow standard format
    for field in ["sender_agent_id", "recipient_agent_id"]:
        agent_id = message_data[field]
        if not agent_id.startswith("Agent-") or not agent_id[-1].isdigit():
            return ValidationResult(
                passed=False, error=f"Invalid agent ID format in {field}: {agent_id}"
            )

    return ValidationResult(passed=True)


def validate_message_file(message_path: Path) -> ValidationResult:
    """
    Validate a message file's format and contents.

    Args:
        message_path: Path to message file

    Returns:
        ValidationResult: Validation result
    """
    try:
        # Check file extension
        if message_path.suffix != ".json":
            return ValidationResult(
                passed=False, error=f"Invalid message file extension: {message_path}"
            )

        # Read and parse JSON
        with message_path.open("r", encoding="utf-8") as f:
            message_data = json.load(f)

        # Validate message format
        return validate_message_format(message_data)

    except json.JSONDecodeError:
        return ValidationResult(
            passed=False, error=f"Invalid JSON format in message file: {message_path}"
        )
    except Exception as e:
        return ValidationResult(
            passed=False, error=f"Error validating message file {message_path}: {e}"
        )


def validate_all_files(
    logger: logging.Logger, config: "AgentConfig", is_onboarding: bool = False
) -> ValidationResult:
    """
    Validate all required files and directories.

    Args:
        logger: Logger instance
        config: Agent configuration
        is_onboarding: Whether this validation is being done during onboarding

    Returns:
        ValidationResult: Validation result
    """
    # Check directory structure
    dir_result = validate_directory_structure(logger, config)
    if not dir_result.passed:
        return dir_result

    # Check coordinates files
    if not config.coords_file.exists():
        return ValidationResult(
            passed=False, error=f"Missing coordinates file: {config.coords_file}"
        )
    if not config.copy_coords_file.exists():
        return ValidationResult(
            passed=False,
            error=f"Missing copy coordinates file: {config.copy_coords_file}",
        )

    # Validate coordinates contain agent entries
    try:
        with config.coords_file.open("r", encoding="utf-8") as f:
            coords = json.load(f)
            if config.agent_id not in coords:
                return ValidationResult(
                    passed=False, error=f"Missing coordinates for {config.agent_id}"
                )
    except Exception as e:
        return ValidationResult(
            passed=False, error=f"Error validating coordinates file: {e}"
        )

    try:
        with config.copy_coords_file.open("r", encoding="utf-8") as f:
            copy_coords = json.load(f)
            if config.agent_id_for_retriever not in copy_coords:
                return ValidationResult(
                    passed=False,
                    error=f"Missing copy coordinates for {config.agent_id_for_retriever}",
                )
    except Exception as e:
        return ValidationResult(
            passed=False, error=f"Error validating copy coordinates file: {e}"
        )

    # Check inbox messages
    for message_path in config.inbox_dir.glob("*.json"):
        message_result = validate_message_file(message_path)
        if not message_result.passed:
            return message_result

    return ValidationResult(passed=True)


def validate_coords(logger: logging.Logger, config: AgentConfig) -> ValidationResult:
    """
    Validate coordinate files exist and contain required entries.
    """
    try:
        if not config.coords_file.exists():
            return ValidationResult(
                False, f"Coordinates file not found: {config.coords_file}"
            )

        if not config.copy_coords_file.exists():
            return ValidationResult(
                False, f"Copy coordinates file not found: {config.copy_coords_file}"
            )

        # Load and validate coordinates
        with open(config.coords_file) as f:
            coords = json.load(f)

        with open(config.copy_coords_file) as f:
            copy_coords = json.load(f)

        # Check for required entries
        if config.agent_id not in coords:
            return ValidationResult(False, f"Missing coordinates for {config.agent_id}")

        if config.agent_id_for_retriever not in copy_coords:
            return ValidationResult(
                False, f"Missing copy coordinates for {config.agent_id}"
            )

        return ValidationResult(True)

    except json.JSONDecodeError as e:
        return ValidationResult(False, f"Invalid JSON in coordinates file: {e}")
    except Exception as e:
        return ValidationResult(False, f"Error validating coordinates: {e}")


def validate_json_file(logger: logging.Logger, file_path: Path) -> ValidationResult:
    """
    Validate a JSON file exists and is well-formed.
    """
    try:
        if not file_path.exists():
            return ValidationResult(False, f"File not found: {file_path}")

        with open(file_path) as f:
            json.load(f)

        return ValidationResult(True)

    except json.JSONDecodeError as e:
        return ValidationResult(False, f"Invalid JSON in {file_path}: {e}")
    except Exception as e:
        return ValidationResult(False, f"Error validating {file_path}: {e}")


def validate_message(content: str) -> ValidationResult:
    """
    Validate a message's content.
    """
    try:
        if not content.strip():
            return ValidationResult(False, "Empty message content")

        # Add any additional message validation rules here

        return ValidationResult(True)

    except Exception as e:
        return ValidationResult(False, f"Error validating message: {e}")


def validate_file_size(size_bytes: int, max_size_bytes: int) -> ValidationResult:
    """
    Validate file size

    Args:
        size_bytes: Size of file in bytes
        max_size_bytes: Maximum allowed size in bytes

    Returns:
        ValidationResult indicating if validation passed
    """
    if size_bytes > max_size_bytes:
        return ValidationResult(
            passed=False,
            error=f"File size {size_bytes} bytes exceeds maximum of {max_size_bytes} bytes",
        )
    return ValidationResult(passed=True)


def validate_line_count(line_count: int, max_lines: int) -> ValidationResult:
    """
    Validate number of lines

    Args:
        line_count: Number of lines
        max_lines: Maximum allowed lines

    Returns:
        ValidationResult indicating if validation passed
    """
    if line_count > max_lines:
        return ValidationResult(
            passed=False,
            error=f"Line count {line_count} exceeds maximum of {max_lines} lines",
        )
    return ValidationResult(passed=True)
