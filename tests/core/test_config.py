# tests/core/test_config.py

import os
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

# Adjust the import path based on project structure
# Assuming tests run from the project root
from src.dreamos.core.config import (
    AppConfig,
    load_config,
    get_config,
    find_project_root_marker,
    DEFAULT_CONFIG_PATH,
    ConfigurationError,
    setup_logging, # Import if testing this function directly
    # Import nested models if needed for specific tests
    LoggingConfig,
    PathsConfig,
)

# Helper to create dummy config files
@pytest.fixture
def dummy_config_file(tmp_path):
    config_dir = tmp_path / "runtime" / "config"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.yaml"
    config_data = {
        "logging": {"level": "DEBUG", "log_to_console": False},
        "paths": { 
            # Add specific paths if needed for testing resolution 
        },
        # Add other minimal sections if validation requires them
    }
    with open(config_path, 'w') as f:
        yaml.dump(config_data, f)
    return config_path

@pytest.fixture
def mock_project_root(tmp_path):
    # Create a fake project root structure
    project_root = tmp_path / "fake_project"
    project_root.mkdir()
    (project_root / ".git").mkdir() # Marker file
    # Create structure expected by find_project_root_marker relative to a fake test file location
    fake_src_dir = project_root / "src" / "dreamos" / "core"
    fake_src_dir.mkdir(parents=True)
    fake_config_py = fake_src_dir / "config.py"
    fake_config_py.touch()
    return project_root, fake_config_py

# --- Test Cases ---

def test_find_project_root_marker_success(mock_project_root):
    project_root, fake_config_py = mock_project_root
    # Patch __file__ within the config module context
    with patch('src.dreamos.core.config.__file__', str(fake_config_py)):
        found_root = find_project_root_marker()
        assert found_root == project_root

def test_find_project_root_marker_fail(tmp_path):
    # Test failure when marker is not found
    non_project_dir = tmp_path / "no_marker"
    non_project_dir.mkdir()
    fake_file = non_project_dir / "some_file.py"
    fake_file.touch()
    with patch('src.dreamos.core.config.__file__', str(fake_file)):
        with pytest.raises(FileNotFoundError):
            find_project_root_marker()

# TODO: Add tests for load_config
def test_load_config_success(dummy_config_file):
    """Test loading a valid configuration file."""
    # Reset global config state for isolation
    # Patch multiple items using a single with statement
    with (patch('src.dreamos.core.config._config', None),
          patch('src.dreamos.core.config.setup_logging') as mock_setup_logging,
          patch('src.dreamos.core.config.DEFAULT_CONFIG_PATH', dummy_config_file)): # Ensure default path points to dummy
        
        # Load config using the dummy file path
        # Note: The load_config implementation currently might have issues if passed None
        # but here we pass the explicit path from the fixture.
        config = load_config(config_path=dummy_config_file) 
        
        assert isinstance(config, AppConfig)
        assert config.logging.level == "DEBUG" # Check value from dummy file
        assert config.logging.log_to_console is False
        mock_setup_logging.assert_called_once_with(config)

def test_load_config_file_not_found(tmp_path):
    """Test load_config raises error if file doesn't exist."""
    non_existent_path = tmp_path / "not_real.yaml"
    with patch('src.dreamos.core.config._config', None):
        # Need to mock DEFAULT_CONFIG_PATH as well if load_config relies on it when path=None
        # However, the current implementation seems to require a path argument.
        # Test by providing a non-existent path explicitly.
        with pytest.raises(ConfigurationError, match="Config file not found"):
             load_config(config_path=non_existent_path)

def test_load_config_invalid_yaml(tmp_path):
    """Test load_config raises error for invalid YAML format."""
    invalid_yaml_path = tmp_path / "invalid.yaml"
    with open(invalid_yaml_path, 'w') as f:
        f.write("logging: { level: DEBUG") # Malformed YAML
    
    with patch('src.dreamos.core.config._config', None):
        with pytest.raises(ConfigurationError, match="Failed to load config"):
            load_config(config_path=invalid_yaml_path)

def test_load_config_not_dict(tmp_path):
    """Test load_config raises error if YAML is not a dictionary."""
    not_dict_path = tmp_path / "not_dict.yaml"
    with open(not_dict_path, 'w') as f:
        yaml.dump(["list", "not", "dict"], f)
        
    with patch('src.dreamos.core.config._config', None):
        with pytest.raises(ConfigurationError, match="Config file is not a valid dictionary"):
            load_config(config_path=not_dict_path)

# TODO: Add tests for get_config (singleton behavior)
def test_get_config_loads_once(dummy_config_file):
    """Test that get_config loads config only once and returns the same instance."""
    with (patch('src.dreamos.core.config._config', None) as mock_config_global,
          patch('src.dreamos.core.config.load_config') as mock_load_config):
        
        # Set a return value for the mock load_config
        mock_instance = AppConfig() # Create a dummy instance
        mock_load_config.return_value = mock_instance
        
        # First call to get_config should trigger load_config
        config1 = get_config()
        mock_load_config.assert_called_once()
        assert config1 is mock_instance

        # Reset call count for next assertion
        mock_load_config.reset_mock()

        # Second call to get_config should return the same instance without calling load_config again
        config2 = get_config()
        mock_load_config.assert_not_called()
        assert config2 is config1
        assert config2 is mock_instance

def test_get_config_uses_loaded_config(dummy_config_file):
    """Test get_config returns already loaded config."""
    # First, load the config directly
    with (patch('src.dreamos.core.config._config', None),
          patch('src.dreamos.core.config.setup_logging') as mock_setup_logging,
          patch('src.dreamos.core.config.DEFAULT_CONFIG_PATH', dummy_config_file)):
        loaded_config = load_config(config_path=dummy_config_file)
    
    # Now, patch load_config to ensure it's NOT called by get_config
    with patch('src.dreamos.core.config.load_config') as mock_load_config:
        retrieved_config = get_config()
        mock_load_config.assert_not_called()
        assert retrieved_config is loaded_config

# TODO: Add tests for AppConfig model validation (e.g., path resolution)
def test_appconfig_path_resolution(mock_project_root):
    """Test that paths in PathsConfig are resolved correctly relative to project root."""
    project_root, fake_config_py = mock_project_root
    
    # Use patch to simulate AppConfig being initialized with the mock project root
    # We need to patch find_project_root_marker used during initialization
    with (patch('src.dreamos.core.config.find_project_root_marker', return_value=project_root),
          patch('src.dreamos.core.config.setup_logging')): # Mock logging setup
         # Initialize AppConfig directly for testing its validation
         # We assume default values are used if no config file is loaded explicitly
         config = AppConfig()

    # Check default paths resolution (assuming defaults use PROJECT_ROOT)
    assert config.paths.project_root == project_root
    assert config.paths.runtime == project_root / "runtime"
    assert config.paths.logs == project_root / "runtime" / "logs"
    assert config.paths.agent_comms == project_root / "runtime" / "agent_comms"
    assert config.paths.central_task_boards == project_root / "runtime" / "agent_comms" / "central_task_boards"
    assert config.paths.task_schema == project_root / "src" / "dreamos" / "coordination" / "tasks" / "task-schema.json"

def test_appconfig_ensure_dirs_exist(mock_project_root):
    """Test that the _ensure_dirs_exist method (called by validator) creates dirs."""
    project_root, fake_config_py = mock_project_root
    runtime_path = project_root / "runtime"
    logs_path = runtime_path / "logs"
    tasks_path = runtime_path / "tasks" # Assuming this is created by _ensure_dirs_exist

    assert not runtime_path.exists()
    assert not logs_path.exists()
    assert not tasks_path.exists()

    # Patch find_project_root_marker and Path.mkdir to check calls
    # Correct multi-context manager syntax using parentheses
    with (
        patch('src.dreamos.core.config.find_project_root_marker', return_value=project_root),
        patch('pathlib.Path.mkdir') as mock_mkdir,
        patch('src.dreamos.core.config.setup_logging')
    ):
        # Initialize AppConfig - validation should call _ensure_dirs_exist
        config = AppConfig()

    # Check if mkdir was called for expected directories
    mkdir_calls = {call.args[0] for call in mock_mkdir.call_args_list} 
    
    # Verify the essential directories were attempted
    assert any(str(logs_path) in str(path_arg) for path_arg in mkdir_calls), f"Logs path {logs_path} not created"
    assert any(str(runtime_path) in str(path_arg) for path_arg in mkdir_calls), f"Runtime path {runtime_path} not created"
    # assert any(tasks_path in mkdir_calls), "Tasks path not created" # Uncomment/adjust if tasks dir is added

# TODO: Add tests for setup_logging (if desired)

print("Test file skeleton created for core/config.py") 