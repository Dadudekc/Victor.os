"""
Tests for the validation module
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dreamos.tools.agent2_bootstrap_runner.validation import (
    validate_all_files,
    validate_coords,
    validate_json_file,
)


class TestValidateCoords:
    def test_valid_dict_coords(self, mock_logger, tmp_path):
        """Test validation with valid dict coordinates"""
        # Create a valid coords file
        coords_file = tmp_path / "coords.json"
        coords_data = {"Agent-2": {"x": 100, "y": 200}}
        coords_file.write_text(json.dumps(coords_data))
        
        # Validate
        result = validate_coords(mock_logger, coords_file, "Agent-2", expect_dict=True)
        assert result is True
        mock_logger.error.assert_not_called()
    
    def test_valid_list_coords(self, mock_logger, tmp_path):
        """Test validation with valid list coordinates"""
        # Create a valid coords file
        coords_file = tmp_path / "copy_coords.json"
        coords_data = {"agent_02": [300, 400]}
        coords_file.write_text(json.dumps(coords_data))
        
        # Validate
        result = validate_coords(mock_logger, coords_file, "agent_02", expect_dict=False)
        assert result is True
        mock_logger.error.assert_not_called()
    
    def test_missing_key(self, mock_logger, tmp_path):
        """Test validation with missing key"""
        # Create a coords file with missing key
        coords_file = tmp_path / "coords.json"
        coords_data = {"Agent-1": {"x": 100, "y": 200}}
        coords_file.write_text(json.dumps(coords_data))
        
        # Validate and expect system exit
        with pytest.raises(SystemExit):
            validate_coords(mock_logger, coords_file, "Agent-2", expect_dict=True)
        
        mock_logger.error.assert_called_once()
    
    def test_wrong_dict_format(self, mock_logger, tmp_path):
        """Test validation with wrong dict format"""
        # Create a coords file with wrong format
        coords_file = tmp_path / "coords.json"
        coords_data = {"Agent-2": [100, 200]}  # List instead of dict
        coords_file.write_text(json.dumps(coords_data))
        
        # Validate and expect system exit
        with pytest.raises(SystemExit):
            validate_coords(mock_logger, coords_file, "Agent-2", expect_dict=True)
        
        mock_logger.error.assert_called_once()
    
    def test_wrong_list_format(self, mock_logger, tmp_path):
        """Test validation with wrong list format"""
        # Create a coords file with wrong format
        coords_file = tmp_path / "copy_coords.json"
        coords_data = {"agent_02": {"x": 300, "y": 400}}  # Dict instead of list
        coords_file.write_text(json.dumps(coords_data))
        
        # Validate and expect system exit
        with pytest.raises(SystemExit):
            validate_coords(mock_logger, coords_file, "agent_02", expect_dict=False)
        
        mock_logger.error.assert_called_once()
    
    def test_invalid_list_length(self, mock_logger, tmp_path):
        """Test validation with invalid list length"""
        # Create a coords file with wrong list length
        coords_file = tmp_path / "copy_coords.json"
        coords_data = {"agent_02": [300, 400, 500]}  # 3 elements instead of 2
        coords_file.write_text(json.dumps(coords_data))
        
        # Validate and expect system exit
        with pytest.raises(SystemExit):
            validate_coords(mock_logger, coords_file, "agent_02", expect_dict=False)
        
        mock_logger.error.assert_called_once()
    
    def test_file_not_found(self, mock_logger, tmp_path):
        """Test validation with non-existent file"""
        # Non-existent file
        coords_file = tmp_path / "nonexistent.json"
        
        # Validate and expect system exit
        with pytest.raises(SystemExit):
            validate_coords(mock_logger, coords_file, "Agent-2", expect_dict=True)
        
        mock_logger.error.assert_called_once()
    
    def test_invalid_json(self, mock_logger, tmp_path):
        """Test validation with invalid JSON"""
        # Create an invalid JSON file
        coords_file = tmp_path / "invalid.json"
        coords_file.write_text("{invalid json")
        
        # Validate and expect system exit
        with pytest.raises(SystemExit):
            validate_coords(mock_logger, coords_file, "Agent-2", expect_dict=True)
        
        mock_logger.error.assert_called_once()

class TestValidateJsonFile:
    def test_valid_json_dict(self, mock_logger, tmp_path):
        """Test validation with valid JSON dict"""
        # Create a valid JSON file
        json_file = tmp_path / "valid.json"
        json_data = {"key": "value"}
        json_file.write_text(json.dumps(json_data))
        
        # Validate
        result = validate_json_file(mock_logger, json_file)
        assert result is True
        mock_logger.error.assert_not_called()
    
    def test_valid_json_list(self, mock_logger, tmp_path):
        """Test validation with valid JSON list"""
        # Create a valid JSON file
        json_file = tmp_path / "valid.json"
        json_data = [{"key": "value"}]
        json_file.write_text(json.dumps(json_data))
        
        # Validate
        result = validate_json_file(mock_logger, json_file)
        assert result is True
        mock_logger.error.assert_not_called()
    
    def test_expect_list_with_list(self, mock_logger, tmp_path):
        """Test validation expecting list with list"""
        # Create a valid JSON file
        json_file = tmp_path / "valid.json"
        json_data = [{"key": "value"}]
        json_file.write_text(json.dumps(json_data))
        
        # Validate
        result = validate_json_file(mock_logger, json_file, expect_list=True)
        assert result is True
        mock_logger.error.assert_not_called()
    
    def test_expect_list_with_dict(self, mock_logger, tmp_path):
        """Test validation expecting list with dict"""
        # Create a JSON file with dict
        json_file = tmp_path / "invalid.json"
        json_data = {"key": "value"}
        json_file.write_text(json.dumps(json_data))
        
        # Validate and expect system exit
        with pytest.raises(SystemExit):
            validate_json_file(mock_logger, json_file, expect_list=True)
        
        mock_logger.error.assert_called_once()
    
    def test_inbox_json_not_exists(self, mock_logger, tmp_path):
        """Test validation with non-existent inbox.json"""
        # Non-existent inbox.json file
        json_file = tmp_path / "inbox.json"
        
        # Validate should pass for inbox.json
        result = validate_json_file(mock_logger, json_file)
        assert result is True
        mock_logger.error.assert_not_called()
    
    def test_other_file_not_exists(self, mock_logger, tmp_path):
        """Test validation with non-existent file (not inbox.json)"""
        # Non-existent file
        json_file = tmp_path / "other.json"
        
        # Validate and expect system exit
        with pytest.raises(SystemExit):
            validate_json_file(mock_logger, json_file)
        
        mock_logger.error.assert_called_once()
    
    def test_invalid_json(self, mock_logger, tmp_path):
        """Test validation with invalid JSON"""
        # Create an invalid JSON file
        json_file = tmp_path / "invalid.json"
        json_file.write_text("{invalid json")
        
        # Validate and expect system exit
        with pytest.raises(SystemExit):
            validate_json_file(mock_logger, json_file)
        
        mock_logger.error.assert_called_once()

class TestValidateAllFiles:
    def test_valid_files(self, mock_logger, mock_agent_config):
        """Test validation with all valid files"""
        # Mock validation functions
        with patch('dreamos.tools.agent2_bootstrap_runner.validation.validate_coords', return_value=True) as mock_validate_coords, \
             patch('dreamos.tools.agent2_bootstrap_runner.validation.validate_json_file', return_value=True) as mock_validate_json:
            
            # Mock file existence
            with patch.object(mock_agent_config.coords_file, 'exists', return_value=True), \
                 patch.object(mock_agent_config.copy_coords_file, 'exists', return_value=True), \
                 patch.object(mock_agent_config.inbox_file, 'exists', return_value=True):
                
                # Validate
                validate_all_files(mock_logger, mock_agent_config)
                
                # Check validation functions were called
                mock_validate_coords.assert_called()
                mock_validate_json.assert_called_once()
                mock_logger.error.assert_not_called()
    
    def test_missing_coords_files(self, mock_logger, mock_agent_config):
        """Test validation with missing coordinate files"""
        # Mock file existence
        with patch.object(mock_agent_config.coords_file, 'exists', return_value=False), \
             patch.object(mock_agent_config.copy_coords_file, 'exists', return_value=True):
            
            # Validate and expect system exit
            with pytest.raises(SystemExit):
                validate_all_files(mock_logger, mock_agent_config)
            
            mock_logger.error.assert_called_once()
    
    def test_inbox_not_exists(self, mock_logger, mock_agent_config):
        """Test validation with non-existent inbox file"""
        # Mock validation functions
        with patch('dreamos.tools.agent2_bootstrap_runner.validation.validate_coords', return_value=True) as mock_validate_coords, \
             patch('dreamos.tools.agent2_bootstrap_runner.validation.validate_json_file', return_value=True) as mock_validate_json:
            
            # Mock file existence
            with patch.object(mock_agent_config.coords_file, 'exists', return_value=True), \
                 patch.object(mock_agent_config.copy_coords_file, 'exists', return_value=True), \
                 patch.object(mock_agent_config.inbox_file, 'exists', return_value=False):
                
                # Validate
                validate_all_files(mock_logger, mock_agent_config)
                
                # Check validation functions were called
                mock_validate_coords.assert_called()
                mock_validate_json.assert_not_called()  # Should not be called if inbox doesn't exist
                mock_logger.error.assert_not_called() 