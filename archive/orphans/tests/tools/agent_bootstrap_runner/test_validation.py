"""
Tests for validation functionality
"""

import json

import pytest

from dreamos.tools.agent_bootstrap_runner.validation import (
    validate_all_files,
    validate_coords,
    validate_json_file,
)


@pytest.mark.parametrize("agent_id", [f"Agent-{i}" for i in range(9)])
class TestValidateCoords:
    def test_valid_dict_coords(self, agent_id, mock_logger, tmp_path):
        """Test validation of valid dict coordinates"""
        coords_file = tmp_path / "coords.json"
        coords_file.write_text(json.dumps({agent_id: {"x": 100, "y": 200}}))

        # Should not raise any exceptions
        validate_coords(mock_logger, coords_file, agent_id, expect_dict=True)

    def test_valid_list_coords(self, agent_id, mock_logger, tmp_path):
        """Test validation of valid list coordinates"""
        coords_file = tmp_path / "coords.json"
        coords_file.write_text(json.dumps({agent_id: [100, 200]}))

        # Should not raise any exceptions
        validate_coords(mock_logger, coords_file, agent_id, expect_dict=False)

    def test_missing_key(self, agent_id, mock_logger, tmp_path):
        """Test validation when agent key is missing"""
        coords_file = tmp_path / "coords.json"
        coords_file.write_text(json.dumps({"other_agent": {"x": 100, "y": 200}}))

        with pytest.raises(SystemExit):
            validate_coords(mock_logger, coords_file, agent_id)

    def test_wrong_dict_format(self, agent_id, mock_logger, tmp_path):
        """Test validation when dict format is wrong"""
        coords_file = tmp_path / "coords.json"
        coords_file.write_text(
            json.dumps({agent_id: [100, 200]})
        )  # List instead of dict

        with pytest.raises(SystemExit):
            validate_coords(mock_logger, coords_file, agent_id, expect_dict=True)

    def test_wrong_list_format(self, agent_id, mock_logger, tmp_path):
        """Test validation when list format is wrong"""
        coords_file = tmp_path / "coords.json"
        coords_file.write_text(
            json.dumps({agent_id: {"x": 100, "y": 200}})
        )  # Dict instead of list

        with pytest.raises(SystemExit):
            validate_coords(mock_logger, coords_file, agent_id, expect_dict=False)

    def test_invalid_list_length(self, agent_id, mock_logger, tmp_path):
        """Test validation when list length is wrong"""
        coords_file = tmp_path / "coords.json"
        coords_file.write_text(
            json.dumps({agent_id: [100, 200, 300]})
        )  # 3 values instead of 2

        with pytest.raises(SystemExit):
            validate_coords(mock_logger, coords_file, agent_id, expect_dict=False)

    def test_file_not_found(self, agent_id, mock_logger, tmp_path):
        """Test validation when file doesn't exist"""
        coords_file = tmp_path / "nonexistent.json"

        with pytest.raises(SystemExit):
            validate_coords(mock_logger, coords_file, agent_id)

    def test_invalid_json(self, agent_id, mock_logger, tmp_path):
        """Test validation with invalid JSON"""
        coords_file = tmp_path / "coords.json"
        coords_file.write_text("invalid json")

        with pytest.raises(SystemExit):
            validate_coords(mock_logger, coords_file, agent_id)


class TestValidateJsonFile:
    def test_valid_json_dict(self, mock_logger, tmp_path):
        """Test validation of valid JSON dict"""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')

        # Should not raise any exceptions
        validate_json_file(mock_logger, json_file)

    def test_valid_json_list(self, mock_logger, tmp_path):
        """Test validation of valid JSON list"""
        json_file = tmp_path / "test.json"
        json_file.write_text("[1, 2, 3]")

        # Should not raise any exceptions
        validate_json_file(mock_logger, json_file)

    def test_expect_list_with_list(self, mock_logger, tmp_path):
        """Test validation when expecting list and got list"""
        json_file = tmp_path / "test.json"
        json_file.write_text("[1, 2, 3]")

        # Should not raise any exceptions
        validate_json_file(mock_logger, json_file, expect_list=True)

    def test_expect_list_with_dict(self, mock_logger, tmp_path):
        """Test validation when expecting list but got dict"""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')

        with pytest.raises(SystemExit):
            validate_json_file(mock_logger, json_file, expect_list=True)

    def test_inbox_json_not_exists(self, mock_logger, tmp_path):
        """Test validation when inbox.json doesn't exist"""
        json_file = tmp_path / "inbox.json"

        # Should not raise any exceptions for inbox.json
        validate_json_file(mock_logger, json_file)

    def test_other_file_not_exists(self, mock_logger, tmp_path):
        """Test validation when other file doesn't exist"""
        json_file = tmp_path / "other.json"

        with pytest.raises(SystemExit):
            validate_json_file(mock_logger, json_file)

    def test_invalid_json(self, mock_logger, tmp_path):
        """Test validation with invalid JSON"""
        json_file = tmp_path / "test.json"
        json_file.write_text("invalid json")

        with pytest.raises(SystemExit):
            validate_json_file(mock_logger, json_file)


@pytest.mark.parametrize("agent_id", [f"Agent-{i}" for i in range(9)])
class TestValidateAllFiles:
    def test_valid_files(self, agent_id, mock_logger, mock_agent_config, tmp_path):
        """Test validation with all valid files"""
        # Create and configure test files
        coords_file = tmp_path / "coords.json"
        copy_coords_file = tmp_path / "copy_coords.json"
        inbox_file = tmp_path / "inbox.json"

        # Set up agent config
        mock_agent_config.agent_id = agent_id
        mock_agent_config.agent_id_for_retriever = f"agent_{agent_id[-1].zfill(2)}"
        mock_agent_config.coords_file = coords_file
        mock_agent_config.copy_coords_file = copy_coords_file
        mock_agent_config.inbox_file = inbox_file

        # Create test files
        coords_file.write_text(json.dumps({agent_id: {"x": 100, "y": 200}}))
        copy_coords_file.write_text(
            json.dumps({mock_agent_config.agent_id_for_retriever: [100, 200]})
        )
        inbox_file.write_text('[{"prompt": "test"}]')

        # Should not raise any exceptions
        validate_all_files(mock_logger, mock_agent_config)

    def test_missing_coords_files(
        self, agent_id, mock_logger, mock_agent_config, tmp_path
    ):
        """Test validation with missing coordinate files"""
        # Only create inbox file
        inbox_file = tmp_path / "inbox.json"
        inbox_file.write_text('[{"prompt": "test"}]')

        # Set up agent config
        mock_agent_config.agent_id = agent_id
        mock_agent_config.agent_id_for_retriever = f"agent_{agent_id[-1].zfill(2)}"
        mock_agent_config.coords_file = tmp_path / "nonexistent_coords.json"
        mock_agent_config.copy_coords_file = tmp_path / "nonexistent_copy_coords.json"
        mock_agent_config.inbox_file = inbox_file

        with pytest.raises(SystemExit):
            validate_all_files(mock_logger, mock_agent_config)

    def test_inbox_not_exists(self, agent_id, mock_logger, mock_agent_config, tmp_path):
        """Test validation when inbox.json doesn't exist"""
        # Create only coordinate files
        coords_file = tmp_path / "coords.json"
        copy_coords_file = tmp_path / "copy_coords.json"

        # Set up agent config
        mock_agent_config.agent_id = agent_id
        mock_agent_config.agent_id_for_retriever = f"agent_{agent_id[-1].zfill(2)}"
        mock_agent_config.coords_file = coords_file
        mock_agent_config.copy_coords_file = copy_coords_file
        mock_agent_config.inbox_file = tmp_path / "nonexistent_inbox.json"

        # Create test files
        coords_file.write_text(json.dumps({agent_id: {"x": 100, "y": 200}}))
        copy_coords_file.write_text(
            json.dumps({mock_agent_config.agent_id_for_retriever: [100, 200]})
        )

        # Should not raise any exceptions (inbox.json is optional)
        validate_all_files(mock_logger, mock_agent_config)
