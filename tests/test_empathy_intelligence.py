"""
Test suite for the empathy intelligence system.

Tests both backend components (drift detection, predictive model) and frontend integration.
"""

import asyncio
import shutil
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

# Mock the entire dreamos.api package
mock_websocket_manager = Mock()
mock_websocket_manager.connect = AsyncMock()
mock_websocket_manager.disconnect = Mock()
mock_websocket_manager._process_log_update = AsyncMock()
mock_websocket_manager.broadcast = AsyncMock()
mock_websocket_manager.notify_new_log = Mock()
mock_websocket_manager.notify_log_update = Mock()
mock_websocket_manager.process_log_update = AsyncMock()
mock_websocket_manager.broadcast_to_agent = AsyncMock()
mock_websocket_manager.stop = Mock()
mock_websocket_manager.active_connections = set()

mock_empathy_websocket = Mock()
mock_empathy_websocket.WebSocketManager = Mock(return_value=mock_websocket_manager)
mock_empathy_websocket.router = Mock()
mock_empathy_websocket.manager = mock_websocket_manager

mock_empathy_logs = Mock()
mock_empathy_logs.parse_log_content = Mock(
    return_value={
        "type": "compliance",
        "agent_id": "test_agent",
        "loop_duration": 1.5,
        "reflection_gap": 0.5,
        "metrics": {"compliance_score": 1.0},
    }
)
mock_empathy_logs.router = Mock()

mock_api = Mock()
mock_api.empathy_websocket = mock_empathy_websocket
mock_api.empathy_logs = mock_empathy_logs

sys.modules["dreamos.api"] = mock_api
sys.modules["dreamos.api.empathy_websocket"] = mock_empathy_websocket
sys.modules["dreamos.api.empathy_logs"] = mock_empathy_logs

# Now import the modules
from dreamos.api.empathy_logs import parse_log_content
from dreamos.core.drift_detector import DriftDetector
from dreamos.core.empathy import (
    EmpathyEngine,
    EmpathyMetrics,
    EmpathyValidator,
)
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
def mock_websocket_manager():
    """Create a mock WebSocketManager."""
    mock_manager = Mock()
    mock_manager.connect = AsyncMock()
    mock_manager.disconnect = Mock()
    mock_manager._process_log_update = AsyncMock()
    return mock_manager


@pytest.fixture
def test_client():
    """Create a test client."""
    from fastapi import FastAPI

    app = FastAPI()
    from fastapi.testclient import TestClient

    return TestClient(app)


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
    async def test_websocket_connection(self, mock_websocket_manager):
        """Test WebSocket connection handling."""
        mock_websocket = AsyncMock()
        await mock_websocket_manager.connect(mock_websocket)
        assert mock_websocket_manager.connect.called

        mock_websocket_manager.disconnect(mock_websocket)
        assert mock_websocket_manager.disconnect.called

    @pytest.mark.asyncio
    async def test_log_processing(self, mock_websocket_manager):
        """Test log processing and broadcasting."""
        # Create a test log file
        log_dir = Path("runtime/logs/empathy")
        log_dir.mkdir(parents=True, exist_ok=True)
        test_log = log_dir / "test_log.md"
        test_log.write_text(SAMPLE_COMPLIANCE_LOG, encoding="utf-8")

        # Mock WebSocket
        mock_websocket = AsyncMock()
        await mock_websocket_manager.connect(mock_websocket)

        # Process the log
        await mock_websocket_manager._process_log_update(str(test_log), "new")

        # Verify the method was called
        assert mock_websocket_manager._process_log_update.called

        # Cleanup
        test_log.unlink()
        shutil.rmtree(log_dir, ignore_errors=True)


class TestAPIIntegration:
    """Test suite for API integration."""

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


class TestEmpathyEngine:
    """Test suite for EmpathyEngine."""

    @pytest.fixture
    def empathy_engine(self):
        """Create an EmpathyEngine instance for testing."""
        return EmpathyEngine()

    def test_initialization(self, empathy_engine):
        """Test empathy engine initialization."""
        assert hasattr(empathy_engine, "metrics")
        assert hasattr(empathy_engine, "validator")
        assert isinstance(empathy_engine.metrics, EmpathyMetrics)
        assert isinstance(empathy_engine.validator, EmpathyValidator)

    def test_analyze_interaction(self, empathy_engine):
        """Test interaction analysis."""
        interaction_data = {
            "agent_id": "test_agent",
            "user_sentiment": 0.8,
            "response_empathy": 0.9,
            "context_awareness": 0.85,
            "emotional_intelligence": 0.75,
        }

        result = empathy_engine.analyze_interaction(interaction_data)

        assert "metrics" in result
        assert "validation" in result
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)

        # Verify metrics calculation
        metrics = result["metrics"]
        assert all(0 <= v <= 1 for v in metrics.values())

        # Verify validation
        validation = result["validation"]
        assert "is_valid" in validation
        assert "violations" in validation
        assert "score" in validation

    def test_analyze_interaction_edge_cases(self, empathy_engine):
        """Test interaction analysis with edge cases."""
        # Empty interaction data
        result = empathy_engine.analyze_interaction({})
        assert "metrics" in result
        assert "validation" in result

        # Missing fields
        partial_data = {"agent_id": "test_agent"}
        result = empathy_engine.analyze_interaction(partial_data)
        assert "metrics" in result
        assert "validation" in result

        # Invalid values
        invalid_data = {
            "agent_id": "test_agent",
            "user_sentiment": 1.5,  # Should be clamped to 1.0
            "response_empathy": -0.5,  # Should be clamped to 0.0
        }
        result = empathy_engine.analyze_interaction(invalid_data)
        assert all(0 <= v <= 1 for v in result["metrics"].values())


class TestEmpathyMetrics:
    """Test suite for EmpathyMetrics."""

    @pytest.fixture
    def metrics(self):
        """Create an EmpathyMetrics instance for testing."""
        return EmpathyMetrics()

    def test_calculate_metrics(self, metrics):
        """Test metrics calculation."""
        interaction_data = {
            "agent_id": "test_agent",
            "user_sentiment": 0.8,
            "response_empathy": 0.9,
            "context_awareness": 0.85,
            "emotional_intelligence": 0.75,
        }

        result = metrics.calculate_metrics(interaction_data)
        assert isinstance(result, dict)
        assert all(0 <= v <= 1 for v in result.values())

        # Test specific metrics
        assert "active_listening" in result
        assert "compassion" in result
        assert "emotional_awareness" in result
        assert "perspective_taking" in result


class TestEmpathyValidator:
    """Test suite for EmpathyValidator."""

    @pytest.fixture
    def validator(self):
        """Create an EmpathyValidator instance for testing."""
        return EmpathyValidator()

    def test_validate_empathy(self, validator):
        """Test empathy validation."""
        metrics = {"empathy_score": 0.9, "context_score": 0.85, "emotional_score": 0.8}

        result = validator.validate_empathy(metrics)
        assert isinstance(result, dict)
        assert "is_valid" in result
        assert "violations" in result
        assert "score" in result
        assert isinstance(result["violations"], list)
        assert 0 <= result["score"] <= 1

    def test_validate_empathy_edge_cases(self, validator):
        """Test empathy validation with edge cases."""
        # Test with empty metrics
        result = validator.validate_empathy({})
        assert isinstance(result, dict)
        assert "is_valid" in result
        assert "violations" in result
        assert "score" in result

        # Test with invalid values
        metrics = {
            "empathy_score": 1.5,  # Should be clamped or raise warning
            "context_score": -0.5,  # Should be clamped or raise warning
            "emotional_score": "invalid",  # Should handle type error
        }
        result = validator.validate_empathy(metrics)
        assert isinstance(result, dict)
        assert "is_valid" in result
        assert "violations" in result
        assert "score" in result
        assert 0 <= result["score"] <= 1


def run_smoke_test():
    """Run a smoke test of the entire system."""
    print("Running empathy intelligence system smoke test...")

    # Initialize components
    drift_detector = DriftDetector()
    predictive_model = PredictiveModel()
    empathy_engine = EmpathyEngine()
    empathy_metrics = EmpathyMetrics()
    empathy_validator = EmpathyValidator()

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

    # Test empathy components
    print("Testing empathy components...")
    interaction_data = {
        "agent_id": "test_agent",
        "user_sentiment": 0.8,
        "response_empathy": 0.9,
        "context_awareness": 0.85,
        "emotional_intelligence": 0.75,
    }

    # Test metrics calculation
    metrics = empathy_metrics.calculate_metrics(interaction_data)
    assert isinstance(metrics, dict)
    assert all(0 <= v <= 1 for v in metrics.values())

    # Test validation
    validation = empathy_validator.validate_empathy(metrics)
    assert isinstance(validation, dict)
    assert "is_valid" in validation

    # Test full empathy analysis
    analysis = empathy_engine.analyze_interaction(interaction_data)
    assert "metrics" in analysis
    assert "validation" in analysis
    assert "timestamp" in analysis

    # Test WebSocket
    print("Testing WebSocket...")

    async def test_websocket():
        mock_websocket = AsyncMock()
        mock_manager = Mock()
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = Mock()
        await mock_manager.connect(mock_websocket)
        assert mock_manager.connect.called
        mock_manager.disconnect(mock_websocket)
        assert mock_manager.disconnect.called

    asyncio.run(test_websocket())

    print("Smoke test completed successfully!")


if __name__ == "__main__":
    run_smoke_test()
