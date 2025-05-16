import argparse
import datetime
import json
import os

import jsonschema

# Path to the canonical schema, assuming it's in a parallel 'schemas' directory
DEFAULT_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'schemas', 'inbox_message_schema_v1.json')
VALIDATION_LOG_FILE = os.path.join(os.path.dirname(__file__), 'test_data', 'validation_test_results.log')

def log_result(message):
    """Appends a message to the validation log file with a timestamp."""
    timestamp = datetime.datetime.utcnow().isoformat()
    with open(VALIDATION_LOG_FILE, 'a') as log_f:
        log_f.write(f"{timestamp} - {message}\n")

def load_schema(schema_path=DEFAULT_SCHEMA_PATH):
    """Loads the JSON schema from the specified path."""
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    with open(schema_path, 'r') as f:
        return json.load(f)

def validate_message(message_data, schema):
    """Validates a message dictionary against the loaded schema.

    Args:
        message_data (dict): The message to validate.
        schema (dict): The JSON schema to validate against.

    Raises:
        jsonschema.exceptions.ValidationError: If the message is invalid.
        jsonschema.exceptions.SchemaError: If the schema itself is invalid.
    """
    jsonschema.validate(instance=message_data, schema=schema)
    # print("Message is valid.") # Or return True - logging will handle this

def main():
    parser = argparse.ArgumentParser(description='Validate an inbox message JSON file against the canonical schema.')
    parser.add_argument('message_file_path', type=str, help='Path to the JSON message file to validate.')
    parser.add_argument('--schema_path', type=str, default=DEFAULT_SCHEMA_PATH, help=f'Path to the JSON schema file (default: {DEFAULT_SCHEMA_PATH})')

    args = parser.parse_args()

    try:
        schema = load_schema(args.schema_path)
    except FileNotFoundError as e:
        log_result(f"Error loading schema {args.schema_path}: {e}")
        print(f"Error: {e}") # Keep console for immediate feedback if possible
        exit(2) # Exit code for schema loading error
    except json.JSONDecodeError as e:
        log_result(f"Error: Could not decode schema JSON from {args.schema_path} - {e}")
        print(f"Error: Could not decode schema JSON from {args.schema_path} - {e}")
        exit(2)

    if not os.path.exists(args.message_file_path):
        print(f"Error: Message file not found: {args.message_file_path}")
        return

    try:
        with open(args.message_file_path, 'r') as f:
            message_to_validate = json.load(f)
    except json.JSONDecodeError as e:
        log_result(f"Error: Could not decode message JSON from {args.message_file_path} - {e}")
        print(f"Error: Could not decode message JSON from {args.message_file_path} - {e}")
        exit(3) # Exit code for message loading error
    except Exception as e:
        log_result(f"Error reading message file {args.message_file_path}: {e}")
        print(f"Error reading message file {args.message_file_path}: {e}")
        exit(3)

    try:
        validate_message(message_to_validate, schema)
        log_result(f"VALIDATION_SUCCESS: For file {args.message_file_path} against schema {args.schema_path}")
        print(f"VALIDATION_SUCCESS: {args.message_file_path}")
        exit(0) # Explicit exit code for success
    except jsonschema.exceptions.ValidationError as e:
        error_details = (
            f"VALIDATION_ERROR: For file {args.message_file_path} against schema {args.schema_path}\n"
            f"  Error Details: {e.message}\n"
            f"  Path in JSON: {list(e.path)}\n"
            f"  Violated Validator: {e.validator} = {e.validator_value}"
        )
        log_result(error_details)
        print(error_details) # Also print to console for immediate feedback
        exit(1) # Explicit exit code for validation failure
    except jsonschema.exceptions.SchemaError as e:
        schema_error_details = (
            f"SCHEMA_ERROR: With schema file {args.schema_path}\n"
            f"  Error Details: {e.message}"
        )
        log_result(schema_error_details)
        print(schema_error_details)
        exit(2) # Explicit exit code for schema error
    except Exception as e:
        unexpected_error_details = f"UNEXPECTED_ERROR: {e}"
        log_result(unexpected_error_details)
        print(unexpected_error_details)
        exit(4) # Changed exit code to differentiate from message loading error

if __name__ == '__main__':
    # Optionally clear log file at start of a test suite run, or append as is
    # with open(VALIDATION_LOG_FILE, 'w') as log_f:
    #     log_f.write(f"{datetime.datetime.utcnow().isoformat()} - Validation Test Suite Started\n")
    main() 