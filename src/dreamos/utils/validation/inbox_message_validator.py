#!/usr/bin/env python3
"""
Inbox Message Validator for Dream.OS

Validates incoming messages against the defined inbox_message_schema_v1.json.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Attempt to import jsonschema, provide a clear error if not found.
try:
    from jsonschema import validate
    from jsonschema.exceptions import SchemaError, ValidationError
except ImportError:
    print(
        "ERROR: jsonschema library not found. Please install it: pip install jsonschema"
    )
    # Allow script to be imported but validation will fail if jsonschema is missing.
    # This helps in environments where jsonschema might be conditionally available
    # or for initial setup before all dependencies are installed.
    validate = None
    ValidationError = None
    SchemaError = None

# Define the path to the schema file relative to this script or a known location.
# Assuming the script is in src/dreamos/utils/validation/
# and the schema is in runtime/governance/protocols/
DEFAULT_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "runtime"
    / "governance"
    / "protocols"
    / "inbox_message_schema_v1.json"
)


class MessageValidator:
    """Validates messages against the Dream.OS inbox message schema."""

    def __init__(self, schema_path: Path = DEFAULT_SCHEMA_PATH):
        """
        Initializes the validator with a schema.

        Args:
            schema_path: Path to the JSON schema file.
        """
        self.schema_path = schema_path
        self.schema = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        """Loads the JSON schema from the specified path."""
        if not self.schema_path.exists():
            # Fallback if the default path logic is incorrect or file moved
            alt_path = Path("runtime/governance/protocols/inbox_message_schema_v1.json")
            if alt_path.exists():
                self.schema_path = alt_path
            else:
                print(
                    f"ERROR: Schema file not found at {self.schema_path} or {alt_path}"
                )
                return None

        try:
            with open(self.schema_path, "r") as f:
                schema_data = json.load(f)
            # Basic check to ensure it's a schema
            if "$schema" not in schema_data or "properties" not in schema_data:
                print(
                    f"ERROR: {self.schema_path} does not appear to be a valid JSON Schema."
                )
                return None
            return schema_data
        except json.JSONDecodeError as e:
            print(
                f"ERROR: Could not decode JSON from schema file {self.schema_path}: {e}"
            )
            return None
        except Exception as e:
            print(
                f"ERROR: An unexpected error occurred while loading schema {self.schema_path}: {e}"
            )
            return None

    def validate_message(self, message_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates a message dictionary against the loaded schema.

        Args:
            message_data: The message content as a Python dictionary.

        Returns:
            A tuple: (is_valid: bool, errors: List[str])
            errors will be a list of human-readable error messages if validation fails.
        """
        if not validate or not ValidationError or not SchemaError:
            return False, [
                "jsonschema library is not installed. Validation cannot be performed."
            ]

        if not self.schema:
            return False, [
                f"Schema not loaded from {self.schema_path}. Cannot validate."
            ]

        try:
            validate(instance=message_data, schema=self.schema)
            return True, []
        except ValidationError as e:
            # Construct a more user-friendly error message
            error_path = " -> ".join(map(str, e.path)) if e.path else "N/A"
            error_message = (
                f"Validation Error: {e.message}\n"
                f"  Schema Path: {error_path}\n"
                f"  Validator: {e.validator} = {e.validator_value}\n"
                f"  Problematic Instance Value: {e.instance}"
            )
            return False, [error_message]
        except SchemaError as e:
            # This indicates a problem with the schema itself
            return False, [
                f"Schema Error: The schema file {self.schema_path} is invalid. {e.message}"
            ]
        except Exception as e:
            return False, [f"An unexpected error occurred during validation: {e}"]


def main():
    """CLI entry point for basic validation testing."""
    print("Dream.OS Inbox Message Validator")
    print("---------------------------------")

    validator = MessageValidator()
    if not validator.schema:
        print("Exiting due to schema loading failure.")
        return

    print(f"Successfully loaded schema: {validator.schema_path.name}")
    print("\n--- Validating Sample Messages ---")

    # --- Sample valid message ---
    valid_message = {
        "message_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "timestamp_created": "2024-07-29T10:00:00Z",
        "version": "1.0",
        "to_agent_id": "Agent-1",
        "from_agent_id": "Agent-Supervisor",
        "subject": "Test Message",
        "body": "This is a test message body.",
        "body_type": "text/plain",
        "priority": "NORMAL",
        "metadata": {"source_script": "validator_test"},
    }
    is_valid, errors = validator.validate_message(valid_message)
    print(f"\nValidating valid_message: {'PASS' if is_valid else 'FAIL'}")
    if errors:
        for err in errors:
            print(f"  - {err}")

    # --- Sample invalid message (missing required field 'subject') ---
    invalid_message_missing_field = {
        "message_id": "b1c2d3e4-f5g6-7890-1234-567890abcdef",
        "timestamp_created": "2024-07-29T10:05:00Z",
        "version": "1.0",
        "to_agent_id": "Agent-2",
        "from_agent_id": "System-TestHarness",
        # "subject": "This is missing",
        "body": "Another test message.",
        "body_type": "text/markdown",
        "priority": "HIGH",
    }
    is_valid, errors = validator.validate_message(invalid_message_missing_field)
    print(
        f"\nValidating invalid_message_missing_field: {'PASS' if is_valid else 'FAIL'}"
    )
    if errors:
        for err in errors:
            print(f"  - {err}")

    # --- Sample invalid message (incorrect data type for priority) ---
    invalid_message_bad_type = {
        "message_id": "c1d2e3f4-g5h6-7890-1234-567890abcdef",
        "timestamp_created": "2024-07-29T10:10:00Z",
        "version": "1.0",
        "to_agent_id": "Agent-3",
        "from_agent_id": "User-Tester",
        "subject": "Type Test",
        "body": "Checking priority type.",
        "body_type": "text/plain",
        "priority": 123,  # Should be a string from enum
    }
    is_valid, errors = validator.validate_message(invalid_message_bad_type)
    print(f"\nValidating invalid_message_bad_type: {'PASS' if is_valid else 'FAIL'}")
    if errors:
        for err in errors:
            print(f"  - {err}")

    # --- Sample invalid message (violates enum for priority) ---
    invalid_message_bad_enum = {
        "message_id": "d1e2f3g4-h5i6-7890-1234-567890abcdef",
        "timestamp_created": "2024-07-29T10:15:00Z",
        "version": "1.0",
        "to_agent_id": "Agent-4",
        "from_agent_id": "User-Tester",
        "subject": "Enum Test",
        "body": "Checking priority enum.",
        "body_type": "text/plain",
        "priority": "MEDIUM_RARE",  # Not in enum
    }
    is_valid, errors = validator.validate_message(invalid_message_bad_enum)
    print(f"\nValidating invalid_message_bad_enum: {'PASS' if is_valid else 'FAIL'}")
    if errors:
        for err in errors:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
