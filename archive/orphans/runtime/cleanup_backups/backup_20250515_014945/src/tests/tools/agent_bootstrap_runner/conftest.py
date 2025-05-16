"""
Pytest fixtures for agent bootstrap runner tests
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_logger():
    """Mock logger fixture for testing"""
    logger = MagicMock()
    return logger

@pytest.fixture
def mock_agent_config(tmp_path):
    """Mock agent config fixture for testing"""
    config = MagicMock()
    config.agent_id = "test-agent"  # String instead of MagicMock
    config.base_runtime = tmp_path
    config.coords_file = tmp_path / "coords.json"
    config.copy_coords_file = tmp_path / "copy_coords.json"
    config.inbox_file = tmp_path / "inbox.json"
    config.archive_dir = tmp_path / "archive"
    return config 