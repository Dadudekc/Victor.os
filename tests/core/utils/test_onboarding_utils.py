#!/usr/bin/env python3
import hashlib  # Needed for mocking sha256
import os

# Adjust the path to import the function from the correct location
# This might need tweaking based on how tests are run (e.g., from project root)
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path  # Use Path object
from unittest.mock import MagicMock, mock_open, patch

import yaml

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
)

from dreamos.agents.utils.onboarding_utils import (
    calculate_file_sha256,
    update_onboarding_contract,
)

# Define mock paths for testing
MOCK_PROTOCOL_FILE = "mock_docs/swarm/onboarding_protocols.md"
MOCK_CONTRACT_FILE = "mock_runtime/agent_registry/agent_onboarding_contracts.yaml"
MOCK_PROJECT_ROOT = "."


class TestUpdateOnboardingContract(unittest.TestCase):

    # Remove setUp/tearDown related to old lock file logic
    # def setUp(self):
    #     ...
    # def tearDown(self):
    #     ...

    # --- Test Cases Implementation (will be adapted next) ---

    @patch("dreamos.agents.utils.onboarding_utils.calculate_file_sha256")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.parent.mkdir")
    @patch("yaml.safe_load")
    @patch("yaml.dump")
    def test_successful_affirmation_new_agent(
        self,
        mock_yaml_dump,
        mock_yaml_load,
        mock_mkdir,
        mock_exists,
        mock_open_file,
        mock_calculate_hash,
    ):
        """Test affirming a contract for a new agent when the contract file doesn't exist."""
        # Arrange
        agent_id = "AgentNew001"
        mock_hash = "FAKEHASH123ABC"
        mock_calculate_hash.return_value = mock_hash
        mock_exists.return_value = False  # Simulate contract file does not exist
        mock_yaml_load.return_value = (
            {}
        )  # safe_load returns {} if file is empty or created

        # Act
        result = update_onboarding_contract(
            agent_id=agent_id,
            protocol_file_path=MOCK_PROTOCOL_FILE,
            contract_file_path=MOCK_CONTRACT_FILE,
            project_root=MOCK_PROJECT_ROOT,
        )

        # Assert
        self.assertTrue(result)
        mock_calculate_hash.assert_called_once_with(
            Path(MOCK_PROJECT_ROOT, MOCK_PROTOCOL_FILE).resolve()
        )
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_exists.assert_called_once()  # Called once to check if contract file exists
        mock_open_file.assert_called_once_with(
            Path(MOCK_PROJECT_ROOT, MOCK_CONTRACT_FILE).resolve(), "w", encoding="utf-8"
        )
        mock_yaml_load.assert_not_called()  # Not called if file doesn't exist
        mock_yaml_dump.assert_called_once()

        # Check dumped data structure
        args, kwargs = mock_yaml_dump.call_args
        dumped_data = args[0]
        self.assertIn(agent_id, dumped_data)
        self.assertEqual(dumped_data[agent_id]["protocol_hash"], mock_hash.upper())
        self.assertIn("timestamp_utc", dumped_data[agent_id])

    @patch("dreamos.agents.utils.onboarding_utils.calculate_file_sha256")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.parent.mkdir")  # mkdir might still be called
    @patch("yaml.safe_load")
    @patch("yaml.dump")
    def test_successful_affirmation_existing_agent(
        self,
        mock_yaml_dump,
        mock_yaml_load,
        mock_mkdir,
        mock_exists,
        mock_open_file,
        mock_calculate_hash,
    ):
        """Test updating the contract for an existing agent successfully."""
        # Arrange
        agent_id_existing = "AgentOld007"
        agent_id_other = "AgentOther002"
        mock_hash_new = "NEWFAKEHASH456DEF"
        initial_timestamp = "2024-01-01T00:00:00Z"
        other_agent_hash = "otherhash789"

        initial_contracts_data = {
            agent_id_existing: {
                "protocol_hash": "OLDFakeHash123",
                "timestamp_utc": initial_timestamp,
            },
            agent_id_other: {
                "protocol_hash": other_agent_hash,
                "timestamp_utc": "2024-01-02T00:00:00Z",
            },
        }

        mock_calculate_hash.return_value = mock_hash_new
        mock_exists.return_value = True  # Simulate contract file exists
        mock_yaml_load.return_value = initial_contracts_data  # Return existing data

        # Mock file handles for read and write
        mock_read_handle = mock_open(
            read_data=yaml.dump(initial_contracts_data)
        ).return_value
        mock_write_handle = mock_open().return_value

        def open_side_effect(path, mode="r", *args, **kwargs):
            resolved_path = Path(path).resolve()
            resolved_contract_path = Path(
                MOCK_PROJECT_ROOT, MOCK_CONTRACT_FILE
            ).resolve()
            if resolved_path == resolved_contract_path:
                if mode == "r":
                    return mock_read_handle
                elif mode == "w":
                    return mock_write_handle
            raise FileNotFoundError(
                f"Unexpected mock open call: {path} with mode {mode}"
            )

        mock_open_file.side_effect = open_side_effect

        # Act
        result = update_onboarding_contract(
            agent_id=agent_id_existing,
            protocol_file_path=MOCK_PROTOCOL_FILE,
            contract_file_path=MOCK_CONTRACT_FILE,
            project_root=MOCK_PROJECT_ROOT,
        )

        # Assert
        self.assertTrue(result)
        mock_calculate_hash.assert_called_once()
        mock_exists.assert_called_once()
        mock_open_file.assert_any_call(
            Path(MOCK_PROJECT_ROOT, MOCK_CONTRACT_FILE).resolve(), "r", encoding="utf-8"
        )
        mock_open_file.assert_any_call(
            Path(MOCK_PROJECT_ROOT, MOCK_CONTRACT_FILE).resolve(), "w", encoding="utf-8"
        )
        mock_yaml_load.assert_called_once_with(mock_read_handle)
        mock_yaml_dump.assert_called_once()

        # Check dumped data structure
        args, kwargs = mock_yaml_dump.call_args
        dumped_data = args[0]
        self.assertIn(agent_id_existing, dumped_data)
        self.assertIn(agent_id_other, dumped_data)
        self.assertEqual(len(dumped_data), 2)

        # Verify existing agent updated
        self.assertEqual(
            dumped_data[agent_id_existing]["protocol_hash"], mock_hash_new.upper()
        )
        self.assertNotEqual(
            dumped_data[agent_id_existing]["timestamp_utc"], initial_timestamp
        )

        # Verify other agent unchanged
        self.assertEqual(dumped_data[agent_id_other]["protocol_hash"], other_agent_hash)

    @patch(
        "dreamos.agents.utils.onboarding_utils.calculate_file_sha256", return_value=None
    )  # Mock hash calculation failure
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    @patch("yaml.dump")
    @patch("logging.error")
    def test_fail_protocol_hash_error(
        self,
        mock_log_error,
        mock_yaml_dump,
        mock_exists,
        mock_open_file,
        mock_calculate_hash,
    ):
        """Test that affirmation fails if protocol hash calculation returns None."""
        # Arrange
        agent_id = "AgentFail003"

        # Act
        result = update_onboarding_contract(
            agent_id=agent_id,
            protocol_file_path=MOCK_PROTOCOL_FILE,  # Path doesn't matter as calculate is mocked
            contract_file_path=MOCK_CONTRACT_FILE,
            project_root=MOCK_PROJECT_ROOT,
        )

        # Assert
        self.assertFalse(result)
        mock_calculate_hash.assert_called_once()
        mock_log_error.assert_called_once()  # Check error was logged
        mock_exists.assert_not_called()  # Should fail before checking contract file
        mock_open_file.assert_not_called()  # Should not attempt to open/write contract file
        mock_yaml_dump.assert_not_called()

    @patch(
        "dreamos.agents.utils.onboarding_utils.calculate_file_sha256",
        return_value="FAKECALCHASH",
    )
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    @patch("yaml.safe_load", side_effect=yaml.YAMLError("Mock YAML parse error"))
    @patch("yaml.dump")
    @patch("logging.error")
    def test_fail_invalid_yaml_load(
        self,
        mock_log_error,
        mock_yaml_dump,
        mock_yaml_load,
        mock_exists,
        mock_open_file,
        mock_calculate_hash,
    ):
        """Test failure when reading the existing contracts YAML file fails."""
        # Arrange
        agent_id = "AgentFail004"
        mock_read_handle = mock_open(read_data="invalid: yaml: content").return_value
        mock_open_file.return_value = (
            mock_read_handle  # Mock open to return handle for reading
        )

        # Act
        result = update_onboarding_contract(
            agent_id=agent_id,
            protocol_file_path=MOCK_PROTOCOL_FILE,
            contract_file_path=MOCK_CONTRACT_FILE,
            project_root=MOCK_PROJECT_ROOT,
        )

        # Assert
        self.assertFalse(result)
        mock_calculate_hash.assert_called_once()
        mock_exists.assert_called_once()
        # Check that it attempted to open for reading
        mock_open_file.assert_called_once_with(
            Path(MOCK_PROJECT_ROOT, MOCK_CONTRACT_FILE).resolve(), "r", encoding="utf-8"
        )
        mock_yaml_load.assert_called_once_with(mock_read_handle)
        mock_yaml_dump.assert_not_called()  # Should not attempt to dump
        mock_log_error.assert_called_once()  # Check error was logged

    @patch(
        "dreamos.agents.utils.onboarding_utils.calculate_file_sha256",
        return_value="FAKECALCHASH",
    )
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists", return_value=True)  # Contract file exists
    @patch(
        "yaml.safe_load",
        return_value={
            "AgentExisting": {"protocol_hash": "OLD", "timestamp_utc": "OLDTIME"}
        },
    )  # Load succeeds
    @patch("yaml.dump", side_effect=yaml.YAMLError("Mock YAML dump error"))
    @patch("logging.error")
    def test_fail_yaml_dump_error(
        self,
        mock_log_error,
        mock_yaml_dump,
        mock_yaml_load,
        mock_exists,
        mock_open_file,
        mock_calculate_hash,
    ):
        """Test failure when writing the updated YAML data fails."""
        # Arrange
        agent_id = "AgentFail005"
        # Mock open to succeed for read, fail for write
        mock_read_handle = mock_open(read_data="dummy: yaml").return_value
        mock_write_handle = mock_open().return_value
        mock_write_handle.__enter__.side_effect = yaml.YAMLError(
            "Mock dump error context"
        )  # Raise error during write context

        def open_side_effect(path, mode="r", *args, **kwargs):
            resolved_path = Path(path).resolve()
            resolved_contract_path = Path(
                MOCK_PROJECT_ROOT, MOCK_CONTRACT_FILE
            ).resolve()
            if resolved_path == resolved_contract_path:
                if mode == "r":
                    return mock_read_handle
                elif mode == "w":
                    # Simulate failure during write by having dump raise or by raising here
                    # Here we mock dump raising the error directly via side_effect patch
                    return (
                        mock_write_handle  # Return handle, dump mock will raise error
                    )
            raise FileNotFoundError(
                f"Unexpected mock open call: {path} with mode {mode}"
            )

        mock_open_file.side_effect = open_side_effect

        # Act
        result = update_onboarding_contract(
            agent_id=agent_id,
            protocol_file_path=MOCK_PROTOCOL_FILE,
            contract_file_path=MOCK_CONTRACT_FILE,
            project_root=MOCK_PROJECT_ROOT,
        )

        # Assert
        self.assertFalse(result)
        mock_calculate_hash.assert_called_once()
        mock_exists.assert_called_once()
        mock_open_file.assert_any_call(
            Path(MOCK_PROJECT_ROOT, MOCK_CONTRACT_FILE).resolve(), "r", encoding="utf-8"
        )
        mock_open_file.assert_any_call(
            Path(MOCK_PROJECT_ROOT, MOCK_CONTRACT_FILE).resolve(), "w", encoding="utf-8"
        )
        mock_yaml_load.assert_called_once()
        mock_yaml_dump.assert_called_once()  # Dump is called, but it raises the error
        mock_log_error.assert_called()  # Check error was logged (could be multiple logs)

    @patch(
        "dreamos.agents.utils.onboarding_utils.calculate_file_sha256",
        return_value="FAKECALCHASH",
    )
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists", return_value=True)  # Contract file exists
    @patch("yaml.safe_load", return_value={})  # Load succeeds
    @patch("yaml.dump")
    @patch("logging.error")
    def test_fail_write_permission_error(
        self,
        mock_log_error,
        mock_yaml_dump,
        mock_yaml_load,
        mock_exists,
        mock_open_file,
        mock_calculate_hash,
    ):
        """Test failure due to a permission error when writing the contracts file."""
        # Arrange
        agent_id = "AgentFail006"

        # Configure mock_open to fail with PermissionError during write
        mock_read_handle = mock_open(read_data="{}").return_value

        def open_side_effect(path, mode="r", *args, **kwargs):
            resolved_path = Path(path).resolve()
            resolved_contract_path = Path(
                MOCK_PROJECT_ROOT, MOCK_CONTRACT_FILE
            ).resolve()
            if resolved_path == resolved_contract_path:
                if mode == "r":
                    return mock_read_handle
                elif mode == "w":
                    raise PermissionError(
                        "[Mock Error] Permission denied to write file"
                    )
            raise FileNotFoundError(
                f"Unexpected mock open call: {path} with mode {mode}"
            )

        mock_open_file.side_effect = open_side_effect

        # Act
        result = update_onboarding_contract(
            agent_id=agent_id,
            protocol_file_path=MOCK_PROTOCOL_FILE,
            contract_file_path=MOCK_CONTRACT_FILE,
            project_root=MOCK_PROJECT_ROOT,
        )

        # Assert
        self.assertFalse(result)  # Expect failure
        mock_calculate_hash.assert_called_once()
        mock_exists.assert_called_once()
        mock_open_file.assert_any_call(
            Path(MOCK_PROJECT_ROOT, MOCK_CONTRACT_FILE).resolve(), "r", encoding="utf-8"
        )
        mock_open_file.assert_any_call(
            Path(MOCK_PROJECT_ROOT, MOCK_CONTRACT_FILE).resolve(), "w", encoding="utf-8"
        )
        mock_yaml_load.assert_called_once()
        mock_yaml_dump.assert_not_called()  # Error occurs during open('w'), before dump
        mock_log_error.assert_called()  # Check error was logged

    @patch(
        "src.dreamos.agents.utils.onboarding_utils.FILELOCK_AVAILABLE", True
    )  # Assume filelock IS available
    @patch("filelock.FileLock")  # Mock the FileLock class
    @patch(
        "src.dreamos.agents.utils.onboarding_utils.calculate_file_sha256"
    )  # Mock hashing
    @patch("yaml.safe_load")
    @patch("yaml.dump")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    def test_update_contract_successful_lock(
        self,
        mock_mkdir,
        mock_exists,
        mock_open_file,
        mock_yaml_dump,
        mock_yaml_load,
        mock_calculate_hash,
        mock_filelock_class,
    ):
        """Test update_onboarding_contract successfully acquires and releases lock."""
        # Arrange
        agent_id = "AgentLock001"
        protocol_path = "docs/swarm/onboarding_protocols.md"
        contract_path = "runtime/agent_registry/agent_onboarding_contracts.yaml"
        lock_path = contract_path + ".lock"

        mock_calculate_hash.return_value = "mockhash123"
        mock_exists.return_value = True  # Simulate contract file exists
        mock_yaml_load.return_value = {}  # Simulate empty existing data

        # Configure the mock FileLock instance
        mock_lock_instance = MagicMock()
        mock_filelock_class.return_value = mock_lock_instance
        mock_lock_instance.acquire.return_value = None  # Simulate successful acquire
        mock_lock_instance.release.return_value = None  # Simulate successful release
        mock_lock_instance.is_locked = True  # Assume locked after acquire

        # Act
        result = update_onboarding_contract(agent_id, protocol_path, contract_path)

        # Assert
        self.assertTrue(result)
        mock_calculate_hash.assert_called_once()
        mock_filelock_class.assert_called_once_with(
            Path(lock_path), timeout=LOCK_TIMEOUT_SECONDS
        )
        mock_lock_instance.acquire.assert_called_once()
        mock_exists.assert_called()  # Should check if contract file exists
        mock_open_file.assert_any_call(
            Path(contract_path), "r", encoding="utf-8"
        )  # Read attempt
        mock_yaml_load.assert_called_once()
        # Verify data passed to dump includes agent_id and mockhash123
        mock_yaml_dump.assert_called_once()
        args, kwargs = mock_yaml_dump.call_args
        dumped_data = args[0]
        self.assertIn(agent_id, dumped_data)
        self.assertEqual(
            dumped_data[agent_id]["protocol_hash"], "MOCKHASH123"
        )  # Check hash (uppercased)
        self.assertIn("timestamp_utc", dumped_data[agent_id])
        mock_open_file.assert_any_call(
            Path(contract_path), "w", encoding="utf-8"
        )  # Write attempt
        mock_lock_instance.release.assert_called_once()  # Ensure lock released

    @patch(
        "src.dreamos.agents.utils.onboarding_utils.FILELOCK_AVAILABLE", False
    )  # Simulate filelock NOT available
    # No need to patch filelock.FileLock if FILELOCK_AVAILABLE is False
    @patch("src.dreamos.agents.utils.onboarding_utils.calculate_file_sha256")
    @patch("yaml.safe_load")
    @patch("yaml.dump")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("logging.warning")  # Check for warning log
    def test_update_contract_no_filelock_library(
        self,
        mock_log_warning,
        mock_mkdir,
        mock_exists,
        mock_open_file,
        mock_yaml_dump,
        mock_yaml_load,
        mock_calculate_hash,
    ):
        """Test update_onboarding_contract proceeds without locking if filelock is unavailable."""
        # Arrange
        agent_id = "AgentLock003"
        protocol_path = "docs/swarm/onboarding_protocols.md"
        contract_path = "runtime/agent_registry/agent_onboarding_contracts.yaml"

        mock_calculate_hash.return_value = "mockhash789"
        mock_exists.return_value = False  # Simulate contract file needs creation
        mock_yaml_load.return_value = (
            {}
        )  # Not strictly needed if exists is False, but safe

        # Act
        result = update_onboarding_contract(agent_id, protocol_path, contract_path)

        # Assert
        self.assertTrue(result)  # Expect success, just without locking
        mock_calculate_hash.assert_called_once()
        # Verify lock was NOT attempted
        # Verify read/write operations happened
        mock_exists.assert_called()
        mock_mkdir.assert_called_once()  # Directory should be created
        # safe_load won't be called if exists is False
        mock_yaml_load.assert_not_called()
        mock_yaml_dump.assert_called_once()
        mock_open_file.assert_any_call(
            Path(contract_path), "w", encoding="utf-8"
        )  # Write attempt
        # Check that the appropriate warning was logged
        mock_log_warning.assert_any_call(unittest.mock.ANY)
        self.assertTrue(
            any(
                "Proceeding without file lock" in call[0][0]
                for call in mock_log_warning.call_args_list
            )
        )


# Remove old lock file test
# def test_fail_cannot_acquire_lock(...):
#    ...

if __name__ == "__main__":
    unittest.main()
