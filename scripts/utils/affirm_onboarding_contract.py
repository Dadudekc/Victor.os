import argparse
import datetime
import hashlib
import os
import sys

import yaml  # Requires PyYAML: pip install PyYAML

# Define paths relative to the script's location assuming it's in scripts/utils/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
PROTOCOL_DOC_PATH = os.path.join(
    PROJECT_ROOT, "docs", "swarm", "onboarding_protocols.md"
)
CONTRACT_YAML_PATH = os.path.join(
    PROJECT_ROOT, "runtime", "agent_registry", "agent_onboarding_contracts.yaml"
)


def calculate_sha256(file_path):
    """Calculates the SHA256 hash of a file."""
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as file:
            while True:
                chunk = file.read(4096)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest().upper()  # Match Get-FileHash output format
    except FileNotFoundError:
        print(f"Error: Protocol document not found at {file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading protocol document: {e}", file=sys.stderr)
        sys.exit(1)


def get_current_utc_iso():
    """Gets the current UTC timestamp in ISO 8601 format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def update_contract_yaml(agent_id, protocol_hash, timestamp):
    """Updates the agent's entry in the onboarding contracts YAML file.

    Note: This currently lacks file locking. Concurrent writes could corrupt the file.
    Consider adding a file locking mechanism if concurrent execution is expected.
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(CONTRACT_YAML_PATH), exist_ok=True)

        # Read existing data or initialize if file doesn't exist/is empty
        data = {}
        if os.path.exists(CONTRACT_YAML_PATH):
            try:
                with open(CONTRACT_YAML_PATH, "r") as file:
                    loaded_data = yaml.safe_load(file)
                    if loaded_data:  # Check if file is not empty
                        data = loaded_data
            except yaml.YAMLError as e:
                print(
                    f"Warning: Could not parse existing YAML file at {CONTRACT_YAML_PATH}. It might be corrupted. Starting fresh. Error: {e}",
                    file=sys.stderr,
                )
            except Exception as e:
                print(
                    f"Warning: Could not read existing YAML file at {CONTRACT_YAML_PATH}. Error: {e}",
                    file=sys.stderr,
                )

        # Update the agent's entry
        data[agent_id] = {
            "protocol_version_hash": f"sha256:{protocol_hash}",
            "affirmation_timestamp_utc": timestamp,
            "notes": f"Contract affirmed/re-affirmed by {agent_id} via script.",
        }

        # Write the updated data back to the file
        with open(CONTRACT_YAML_PATH, "w") as file:
            yaml.dump(data, file, default_flow_style=False, sort_keys=False)

        print(f"Successfully updated contract for {agent_id} in {CONTRACT_YAML_PATH}")

    except FileNotFoundError:
        # This case should be handled by os.makedirs, but included for robustness
        print(
            f"Error: Could not create or access the directory for {CONTRACT_YAML_PATH}",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error updating YAML file: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Affirm onboarding contract by updating the registry YAML."
    )
    parser.add_argument(
        "agent_id", help="The ID of the agent affirming the contract (e.g., Agent4)"
    )
    args = parser.parse_args()

    agent_id = args.agent_id
    print(f"Affirming contract for Agent ID: {agent_id}")

    print(f"Calculating SHA256 hash for: {PROTOCOL_DOC_PATH}")
    protocol_hash = calculate_sha256(PROTOCOL_DOC_PATH)
    print(f"Protocol Hash: {protocol_hash}")

    print("Getting current UTC timestamp...")
    timestamp = get_current_utc_iso()
    print(f"Timestamp: {timestamp}")

    print(f"Updating contract file: {CONTRACT_YAML_PATH}")
    update_contract_yaml(agent_id, protocol_hash, timestamp)


if __name__ == "__main__":
    main()
