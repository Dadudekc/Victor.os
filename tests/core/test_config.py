# tests/core/test_config.py

from unittest.mock import patch

import pytest
import yaml
from pathlib import Path

# Adjust the import path based on project structure
# Assuming tests run from the project root
from dreamos.core.config import (
    get_config, load_config, AppConfig, 
    CoreConfigurationError, DEFAULT_CONFIG_PATH, _config as global_config_val # import CoreConfigurationError
)

# Test Config Files Path
TEST_CONFIGS_DIR = Path(__file__).parent / "fixtures" / "configs"
VALID_CONFIG_FILE = TEST_CONFIGS_DIR / "valid_config.yaml"
EMPTY_CONFIG_FILE = TEST_CONFIGS_DIR / "empty_config.yaml"
INVALID_CONFIG_FILE = TEST_CONFIGS_DIR / "invalid_config.yaml"
NON_EXISTENT_CONFIG_FILE = TEST_CONFIGS_DIR / "non_existent_config.yaml"

# Fixtures
@pytest.fixture(scope="function")
def clear_global_config_singleton(monkeypatch):
    """Ensures the global _config is None before and after each test."""
    # Access the global _config variable from dreamos.core.config directly
    # This assumes your test environment can import dreamos.core.config correctly.
    # If not, you might need to adjust how _config is accessed or use monkeypatch.
    monkeypatch.setattr("dreamos.core.config._config", None)
    yield
    monkeypatch.setattr("dreamos.core.config._config", None) # Ensure it's clear after

@pytest.fixture
def sample_config_data() -> Dict:
    return {
        "logging": {"level": "DEBUG"},
        "paths": {"project_root": "/test/project"}
        # Add other necessary minimal fields
    }

@pytest.fixture
def create_test_yaml_file(tmp_path, sample_config_data):
    def _create(filename: str, data: Optional[Dict] = None, malformed: bool = False):
        file_path = tmp_path / filename
        if data is not None:
            with open(file_path, "w") as f:
                if malformed:
                    f.write("logging: {level: DEBUG : # Unbalanced bracket") # Invalid YAML
                else:
                    yaml.dump(data, f)
        elif malformed: # Create empty but malformed file if no data and malformed=True
             with open(file_path, "w") as f:
                f.write("key: value: another_value") # Malformed
        else: # Create empty valid file
            with open(file_path, "w") as f:
                f.write("{}")
        return file_path
    return _create

# --- Test Cases ---

def test_get_config_loads_default_if_available(clear_global_config_singleton, monkeypatch, create_test_yaml_file, sample_config_data):
    """Test get_config loads from DEFAULT_CONFIG_PATH if it exists and _config is None."""
    # Ensure DEFAULT_CONFIG_PATH exists and is valid for this test
    test_default_path = create_test_yaml_file("default_config_for_test.yaml", sample_config_data)
    monkeypatch.setattr("dreamos.core.config.DEFAULT_CONFIG_PATH", test_default_path)
    
    config = get_config()
    assert config is not None
    assert config.logging.level == "DEBUG"
    # Ensure it's stored globally
    from dreamos.core.config import _config as current_global_config
    assert current_global_config is config

def test_load_config_specific_path(clear_global_config_singleton, create_test_yaml_file, sample_config_data):
    """Test load_config can load from a specified valid YAML file."""
    config_file = create_test_yaml_file("specific_valid.yaml", sample_config_data)
    config = load_config(config_file)
    assert config is not None
    assert config.logging.level == "DEBUG"
    # Check global state
    from dreamos.core.config import _config as current_global_config
    assert current_global_config is config

def test_load_config_path_not_exists(clear_global_config_singleton):
    """Test load_config raises ConfigurationError if specified path does not exist."""
    with pytest.raises(CoreConfigurationError, match="Config file not found"):
        load_config(NON_EXISTENT_CONFIG_FILE)

def test_load_config_empty_yaml(clear_global_config_singleton, create_test_yaml_file):
    """Test load_config handles an empty YAML file gracefully (loads defaults)."""
    empty_file = create_test_yaml_file("empty.yaml", data={})
    config = load_config(empty_file)
    assert config is not None
    # Assert some default values from AppConfig model if any
    assert isinstance(config.logging, AppConfig.__fields__['logging'].type_)

def test_load_config_invalid_yaml(clear_global_config_singleton, create_test_yaml_file):
    """Test load_config raises ConfigurationError for malformed YAML."""
    invalid_file = create_test_yaml_file("invalid.yaml", malformed=True)
    with pytest.raises(CoreConfigurationError, match="Failed to load/parse config"):
        load_config(invalid_file)

def test_get_config_returns_same_instance(clear_global_config_singleton, monkeypatch, create_test_yaml_file, sample_config_data):
    """Test get_config returns the same globally stored instance on subsequent calls."""
    test_default_path = create_test_yaml_file("default_config_for_test_singleton.yaml", sample_config_data)
    monkeypatch.setattr("dreamos.core.config.DEFAULT_CONFIG_PATH", test_default_path)

    config1 = get_config()
    config2 = get_config()
    assert config1 is config2

def test_load_config_no_file_loads_defaults(clear_global_config_singleton, monkeypatch):
    """Test load_config creates default AppConfig if no file specified and default doesn't exist."""
    # Ensure DEFAULT_CONFIG_PATH does NOT exist
    monkeypatch.setattr("dreamos.core.config.DEFAULT_CONFIG_PATH", Path("path/that/does/not/exist.yaml"))
    
    config = load_config() # Call without path
    assert config is not None
    assert isinstance(config, AppConfig)
    # Check some Pydantic default value if AppConfig has one
    # For example, if AppConfig.logging has a default level:
    # assert config.logging.level == "INFO" # (Assuming INFO is Pydantic default for LoggingConfig.level)

# Add more tests for environment variable overrides, specific model validations etc. as needed.

print("Test file skeleton created for core/config.py")
