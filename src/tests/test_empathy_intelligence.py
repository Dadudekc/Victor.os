"""
Test suite for the empathy intelligence system.

Tests both backend components (drift detection, predictive model) and frontend integration.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from dreamos.api.empathy_logs import parse_log_content
from dreamos.api.empathy_websocket import WebSocketManager
from dreamos.core.drift_detector import DriftDetector
from dreamos.core.predictive_model import PredictiveModel

# Test data
SAMPLE_COMPLIANCE_LOG = """
# Compliance Check
- **Agent**: test_agent
- **Timestamp**: 2024-03-20T10:00:00
- **Loop Duration**: 1.5
- **Reflection Gap**: 0.5
- **Task Complexity**: 0.8
- **Violation Frequency**: 0.1
- **Thea Approval Rate**: 0.95
- **Response Time**: 0.3
- **Self Reflection Depth**: 0.9

✅ All compliance checks passed
"""

SAMPLE_VIOLATION_LOG = """
# Violation Detected
- **Agent**: test_agent
- **Timestamp**: 2024-03-20T10:01:00
- **Type**: ethical_boundary
- **Severity**: high

❌ Agent attempted to access restricted information
"""


@pytest.fixture
def drift_detector():
    return DriftDetector()


@pytest.fixture
def predictive_model():
    return PredictiveModel()


@pytest.fixture
def websocket_manager():
    return WebSocketManager()


@pytest.fixture
def test_client():
    from dreamos.main import app

    return TestClient(app=app)


class TestDriftDetector:
    def test_initialization(self, drift_detector):
        """Test drift detector initialization."""
        assert drift_detector.window_size == 100
        assert drift_detector.threshold == 0.1

    def test_add_action(self, drift_detector):
        """Test adding actions and drift detection."""
        # Add some compliant actions
        for _ in range(5):
            warning = drift_detector.add_action("test_agent", "compliance_check", 1.0)
            assert warning is None

        # Add some non-compliant actions
        warning = drift_detector.add_action("test_agent", "compliance_check", 0.0)
        assert warning is not None
        assert warning["type"] == "drift_warning"
        assert warning["severity"] == "medium"

    def test_add_violation(self, drift_detector):
        """Test violation pattern detection."""
        # Add multiple violations of the same type
        for _ in range(3):
            warning = drift_detector.add_violation("test_agent", "ethical_boundary")

        assert warning is not None
        assert warning["type"] == "pattern_warning"
        assert warning["violation_type"] == "ethical_boundary"
        assert warning["count"] == 3

    def test_predict_compliance(self, drift_detector):
        """Test compliance prediction."""
        # Add some actions to build history
        for _ in range(10):
            drift_detector.add_action("test_agent", "compliance_check", 0.8)

        prediction = drift_detector.predict_compliance("test_agent")
        assert prediction["predicted_compliance"] > 0
        assert prediction["confidence"] > 0


class TestPredictiveModel:
    def test_initialization(self, predictive_model):
        """Test predictive model initialization."""
        assert predictive_model.model_dir.exists()
        assert hasattr(predictive_model, "drift_detector")
        assert hasattr(predictive_model, "compliance_predictor")

    def test_extract_features(self, predictive_model):
        """Test feature extraction from action data."""
        action_data = {
            "loop_duration": 1.5,
            "reflection_gap": 0.5,
            "task_complexity": 0.8,
            "violation_frequency": 0.1,
            "thea_approval_rate": 0.95,
            "response_time": 0.3,
            "self_reflection_depth": 0.9,
        }

        features = predictive_model.extract_features("test_agent", action_data)
        assert len(features) >= 7  # Base features
        assert all(0 <= v <= 1 for v in features.values())

    def test_update_model(self, predictive_model):
        """Test model updates with new data."""
        action_data = {
            "loop_duration": 1.5,
            "reflection_gap": 0.5,
            "task_complexity": 0.8,
            "violation_frequency": 0.1,
            "thea_approval_rate": 0.95,
            "response_time": 0.3,
            "self_reflection_depth": 0.9,
        }

        predictive_model.update_model("test_agent", action_data, 1.0)
        assert "test_agent" in predictive_model.feature_history

    def test_predict_drift(self, predictive_model):
        """Test drift prediction."""
        action_data = {
            "loop_duration": 1.5,
            "reflection_gap": 0.5,
            "task_complexity": 0.8,
            "violation_frequency": 0.1,
            "thea_approval_rate": 0.95,
            "response_time": 0.3,
            "self_reflection_depth": 0.9,
        }

        # Update model first
        predictive_model.update_model("test_agent", action_data, 1.0)

        # Test prediction
        prediction = predictive_model.predict_drift("test_agent", action_data)
        assert "drift_detected" in prediction
        assert "drift_score" in prediction
        assert "compliance_probability" in prediction
        assert "confidence" in prediction

    def test_get_agent_insights(self, predictive_model):
        """Test agent insights generation."""
        # Add some data first
        action_data = {
            "loop_duration": 1.5,
            "reflection_gap": 0.5,
            "task_complexity": 0.8,
            "violation_frequency": 0.1,
            "thea_approval_rate": 0.95,
            "response_time": 0.3,
            "self_reflection_depth": 0.9,
        }

        for _ in range(5):
            predictive_model.update_model("test_agent", action_data, 1.0)

        insights = predictive_model.get_agent_insights("test_agent")
        assert "error" not in insights
        assert "drift_trend" in insights
        assert "compliance_trend" in insights
        assert "drift_pattern" in insights
        assert "compliance_pattern" in insights


class TestWebSocketIntegration:
    @pytest.mark.asyncio
    async def test_websocket_connection(self, websocket_manager):
        """Test WebSocket connection handling."""
        mock_websocket = AsyncMock()
        await websocket_manager.connect(mock_websocket)
        assert mock_websocket in websocket_manager.active_connections

        websocket_manager.disconnect(mock_websocket)
        assert mock_websocket not in websocket_manager.active_connections

    @pytest.mark.asyncio
    async def test_log_processing(self, websocket_manager):
        """Test log processing and broadcasting."""
        # Create a test log file
        log_dir = Path("runtime/logs/empathy")
        log_dir.mkdir(parents=True, exist_ok=True)
        test_log = log_dir / "test_log.md"
        test_log.write_text(SAMPLE_COMPLIANCE_LOG, encoding="utf-8")

        # Mock WebSocket
        mock_websocket = AsyncMock()
        await websocket_manager.connect(mock_websocket)

        # Process the log
        await websocket_manager._process_log_update(str(test_log), "new")

        # Verify broadcast
        assert mock_websocket.send_json.called

        sent_messages = [call[0][0] for call in mock_websocket.send_json.call_args_list]

        log_update_message = next(
            (msg for msg in sent_messages if msg.get("type") == "log_update"), None
        )
        assert log_update_message is not None, "log_update message was not sent"
        assert log_update_message["log_type"] == "compliance"

        # Optionally, verify other messages like agent_insights if specifically needed for this test's scope
        agent_insights_message = next(
            (msg for msg in sent_messages if msg.get("type") == "agent_insights"), None
        )
        assert agent_insights_message is not None, "agent_insights message was not sent"

        # Cleanup
        test_log.unlink()
        log_dir.rmdir()


class TestAPIIntegration:
    def test_log_parsing(self):
        """Test log content parsing."""
        metadata = parse_log_content(SAMPLE_COMPLIANCE_LOG)
        assert metadata["type"] == "compliance"
        assert metadata["agent_id"] == "test_agent"
        assert metadata["loop_duration"] == 1.5
        assert metadata["reflection_gap"] == 0.5

    def test_log_endpoints(self, test_client):
        """Test log API endpoints."""
        # Test getting logs
        response = test_client.get("/api/empathy/logs")
        assert response.status_code == 200
        logs = response.json()
        assert isinstance(logs, list)

        # Test getting agents
        response = test_client.get("/api/empathy/agents")
        assert response.status_code == 200
        agents = response.json()
        assert isinstance(agents, list)


def run_smoke_test():
    """Run a smoke test of the entire system."""
    print("Running empathy intelligence system smoke test...")

    # Initialize components
    drift_detector = DriftDetector()
    predictive_model = PredictiveModel()
    websocket_manager = WebSocketManager()

    # Test drift detection
    print("Testing drift detection...")
    warning = drift_detector.add_action("test_agent", "compliance_check", 0.0)
    assert warning is not None

    # Test predictive model
    print("Testing predictive model...")
    action_data = {
        "loop_duration": 1.5,
        "reflection_gap": 0.5,
        "task_complexity": 0.8,
        "violation_frequency": 0.1,
        "thea_approval_rate": 0.95,
        "response_time": 0.3,
        "self_reflection_depth": 0.9,
    }
    predictive_model.update_model("test_agent", action_data, 1.0)
    prediction = predictive_model.predict_drift("test_agent", action_data)
    assert prediction is not None

    # Test WebSocket
    print("Testing WebSocket...")

    async def test_websocket():
        mock_websocket = Mock()
        await websocket_manager.connect(mock_websocket)
        assert mock_websocket in websocket_manager.active_connections
        websocket_manager.disconnect(mock_websocket)

    asyncio.run(test_websocket())

    print("Smoke test completed successfully!")


if __name__ == "__main__":
    run_smoke_test()
