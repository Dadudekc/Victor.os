"""
Pytest configuration file for Dream.OS tests.
"""

import sys
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

# Mock watchdog before importing anything
mock_observer = Mock()
mock_observer.start = Mock()
mock_observer.stop = Mock()
mock_observer.join = Mock()
mock_observer.schedule = Mock()

mock_watchdog = Mock()
mock_watchdog.observers = Mock()
mock_watchdog.observers.Observer = Mock(return_value=mock_observer)
mock_watchdog.events = Mock()
mock_watchdog.events.FileSystemEventHandler = Mock

sys.modules['watchdog'] = mock_watchdog
sys.modules['watchdog.observers'] = mock_watchdog.observers
sys.modules['watchdog.events'] = mock_watchdog.events

class MockLogFileHandler:
    """Mock LogFileHandler for testing."""
    def __init__(self, websocket_manager):
        """Initialize the mock handler."""
        self.manager = websocket_manager
        self.on_created = Mock()
        self.on_modified = Mock()
        self.on_deleted = Mock()

class MockWebSocketManager:
    """Mock WebSocketManager for testing."""
    
    def __init__(self):
        """Initialize the mock manager."""
        self.active_connections = set()
        self.log_dir = Path("runtime/logs/empathy")
        self.file_handler = MockLogFileHandler(self)
        self.observer = mock_observer
        self.observer.schedule(self.file_handler, str(self.log_dir), recursive=False)
        self.observer.start()
        self.drift_detector = Mock()
        self.predictive_model = Mock()
        
        # Mock async methods
        self.connect = AsyncMock()
        self.disconnect = Mock()
        self._process_log_update = AsyncMock()
        self.broadcast = AsyncMock()
        self.notify_new_log = Mock()
        self.notify_log_update = Mock()
        self.process_log_update = AsyncMock()
        self.broadcast_to_agent = AsyncMock()
        self.stop = Mock()

class MockEmpathyWebSocket:
    """Mock empathy_websocket module."""
    WebSocketManager = Mock(return_value=MockWebSocketManager())
    router = Mock()
    manager = MockWebSocketManager()
    LogFileHandler = MockLogFileHandler

class MockEmpathyLogs:
    """Mock empathy_logs module."""
    def parse_log_content(content):
        """Mock log parsing."""
        return {
            "type": "compliance",
            "agent_id": "test_agent",
            "loop_duration": 1.5,
            "reflection_gap": 0.5,
            "metrics": {
                "compliance_score": 1.0
            }
        }
    router = Mock()

class MockAPI:
    """Mock dreamos.api package."""
    empathy_websocket = MockEmpathyWebSocket
    empathy_logs = MockEmpathyLogs

@pytest.fixture(autouse=True)
def mock_api(monkeypatch):
    """Mock the entire dreamos.api package."""
    mock_api = MockAPI()
    sys.modules['dreamos.api'] = mock_api
    sys.modules['dreamos.api.empathy_websocket'] = mock_api.empathy_websocket
    sys.modules['dreamos.api.empathy_logs'] = mock_api.empathy_logs
    return mock_api

@pytest.fixture
def test_client():
    """Create a test client."""
    from fastapi import FastAPI
    app = FastAPI()
    from fastapi.testclient import TestClient
    return TestClient(app) 