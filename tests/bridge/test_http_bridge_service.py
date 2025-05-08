# tests/bridge/test_http_bridge_service.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the FastAPI app instance
# Need to handle potential import errors of underlying components if service isn't robust
# For testing, we might need to ensure mocks are in place *before* this import

# Option 1: Patch before import (can be tricky with module loading)
# Option 2: Import and assume service handles failed imports gracefully (as designed)
from src.dreamos.bridge.http_bridge_service import app, CursorBridgeError

# --- Test Setup ---

@pytest.fixture(scope="module")
def test_client():
    """Create a TestClient instance for the FastAPI app."""
    client = TestClient(app)
    yield client # Use yield to ensure teardown if needed

# --- Test Cases ---

# Test /health endpoint

def test_health_check_success(test_client):
    """Test health check when bridge and config are expected to be available."""
    # This assumes the default state in http_bridge_service allows successful import/config load
    # If not, mocking might be needed here too using pytest fixtures + patch
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    # Check based on the *actual* expected state during test setup
    # Asserting True might fail if imports failed in the test environment
    assert data["status"] == "ok" # Adjust if default test env state is 'error'
    assert isinstance(data["bridge_available"], bool)
    assert isinstance(data["config_loaded"], bool)

# TODO: Add tests for /health when BRIDGE_AVAILABLE=False or CONFIG_LOADED=False
# This would require patching these variables within http_bridge_service module for the test scope

# Test /interact endpoint

@patch('src.dreamos.bridge.http_bridge_service.interact_with_cursor') # Mock the core bridge function
def test_interact_success(mock_interact, test_client):
    """Test successful interaction via /interact."""
    mock_response = "This is the extracted and summarized response from Cursor."
    mock_interact.return_value = mock_response
    
    request_data = {"prompt": "Explain FastAPI testing."}
    response = test_client.post("/interact", json=request_data)
    
    assert response.status_code == 200
    assert response.json() == {"response": mock_response}
    mock_interact.assert_called_once_with(request_data["prompt"], MagicMock()) # Checks if called with prompt and some config object

@patch('src.dreamos.bridge.http_bridge_service.interact_with_cursor')
def test_interact_bridge_error(mock_interact, test_client):
    """Test handling of CursorBridgeError from the bridge function."""
    error_message = "Failed to focus Cursor window."
    mock_interact.side_effect = CursorBridgeError(error_message)
    
    request_data = {"prompt": "Do something risky."}
    response = test_client.post("/interact", json=request_data)
    
    assert response.status_code == 500
    assert response.json() == {"detail": f"Bridge Interaction Error: {error_message}"}
    mock_interact.assert_called_once()

@patch('src.dreamos.bridge.http_bridge_service.interact_with_cursor')
def test_interact_value_error(mock_interact, test_client):
    """Test handling of ValueError (simulating bad input passed down)."""
    # Although the endpoint validates prompt, interact_with_cursor might raise ValueError internally
    error_message = "Invalid internal value used."
    mock_interact.side_effect = ValueError(error_message)
    
    request_data = {"prompt": "Trigger a ValueError."}
    response = test_client.post("/interact", json=request_data)
    
    assert response.status_code == 400 # Expecting 400 based on endpoint handling
    assert response.json() == {"detail": f"Invalid Request Data: {error_message}"}
    mock_interact.assert_called_once()

@patch('src.dreamos.bridge.http_bridge_service.interact_with_cursor')
def test_interact_unexpected_error(mock_interact, test_client):
    """Test handling of unexpected errors."""
    error_message = "Something totally unexpected happened!"
    mock_interact.side_effect = RuntimeError(error_message)
    
    request_data = {"prompt": "Cause chaos."}
    response = test_client.post("/interact", json=request_data)
    
    assert response.status_code == 500
    assert response.json() == {"detail": f"Unexpected Internal Server Error: RuntimeError"} # Type is returned
    mock_interact.assert_called_once()

# Test 503 errors (requires patching module-level variables)
# These are slightly more complex to set up cleanly with pytest/patch

@patch('src.dreamos.bridge.http_bridge_service.BRIDGE_AVAILABLE', False)
def test_interact_bridge_unavailable(test_client):
    """Test /interact when bridge components are unavailable."""
    request_data = {"prompt": "This should fail early."}
    response = test_client.post("/interact", json=request_data)
    
    assert response.status_code == 503
    assert response.json() == {"detail": "Bridge service dependencies are unavailable."}

@patch('src.dreamos.bridge.http_bridge_service.CONFIG_LOADED', False)
@patch('src.dreamos.bridge.http_bridge_service.BRIDGE_AVAILABLE', True) # Ensure bridge itself is seen as available
def test_interact_config_unavailable(test_client):
    """Test /interact when config is not loaded."""
    request_data = {"prompt": "This should also fail early."}
    response = test_client.post("/interact", json=request_data)
    
    assert response.status_code == 503
    assert response.json() == {"detail": "Bridge service configuration is unavailable."}

# --- TODO: Add tests for /health failure cases --- 

@patch('src.dreamos.bridge.http_bridge_service.BRIDGE_AVAILABLE', False)
@patch('src.dreamos.bridge.http_bridge_service.CONFIG_LOADED', True) # Assume config could still load
def test_health_check_bridge_unavailable(test_client):
    """Test /health when bridge components are unavailable."""
    response = test_client.get("/health")
    assert response.status_code == 200 # Health check itself should succeed
    data = response.json()
    assert data["status"] == "error"
    assert data["bridge_available"] is False
    assert data["config_loaded"] is True

@patch('src.dreamos.bridge.http_bridge_service.BRIDGE_AVAILABLE', True)
@patch('src.dreamos.bridge.http_bridge_service.CONFIG_LOADED', False)
def test_health_check_config_unavailable(test_client):
    """Test /health when application configuration is not loaded."""
    response = test_client.get("/health")
    assert response.status_code == 200 # Health check itself should succeed
    data = response.json()
    assert data["status"] == "error"
    assert data["bridge_available"] is True
    assert data["config_loaded"] is False

@patch('src.dreamos.bridge.http_bridge_service.BRIDGE_AVAILABLE', False)
@patch('src.dreamos.bridge.http_bridge_service.CONFIG_LOADED', False)
def test_health_check_both_unavailable(test_client):
    """Test /health when both bridge and config are unavailable."""
    response = test_client.get("/health")
    assert response.status_code == 200 # Health check itself should succeed
    data = response.json()
    assert data["status"] == "error"
    assert data["bridge_available"] is False
    assert data["config_loaded"] is False 