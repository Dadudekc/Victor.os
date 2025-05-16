import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add the src directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import our API module
from src.dreamos.api.empathy_scoring import router, scorer, update_score_cache

# Setup test app with our router
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestEmpathyScoringAPI(unittest.TestCase):
    """Tests for the Empathy Scoring API endpoints."""

    def setUp(self):
        # Reset the score cache
        global score_cache
        score_cache = {}

        # Create sample agent score
        self.sample_score = {
            "agent_id": "agent-1",
            "score": 85.5,
            "status": "proficient",
            "summary": "Agent agent-1 shows proficient empathy performance with stable recent patterns.",
            "timestamp": "2023-05-15T12:00:00Z",
            "metrics": {
                "violations": 2,
                "compliances": 10,
                "violation_severity": {"low": 2, "medium": 0, "high": 0, "critical": 0},
            },
            "value_scores": {
                "compassion": 90.0,
                "clarity": 85.0,
                "collaboration": 88.0,
                "adaptability": 82.0,
            },
            "frequency": {
                "violation_rate": 0.16,
                "compliance_rate": 0.84,
                "total_entries": 12,
            },
            "trend": {"overall": 5.0, "weekly": 2.5, "daily": 0.0},
            "recovery": {
                "recovery_attempts": 2,
                "successful_recoveries": 2,
                "recovery_rate": 1.0,
            },
            "context": {"awareness_score": 0.85, "context_metrics": {}},
            "weighted_components": {
                "core_values": 86.5,
                "frequency": 84.0,
                "trend": 77.5,
                "recovery": 100.0,
                "context": 85.0,
            },
        }

        # Mock the scorer's calculate_agent_score method
        self.scorer_patch = patch.object(
            scorer, "calculate_agent_score", return_value=self.sample_score
        )
        self.mock_calculate_score = self.scorer_patch.start()

        # Mock the scorer's calculate_all_agent_scores method
        self.all_scores_patch = patch.object(
            scorer,
            "calculate_all_agent_scores",
            return_value={"agent-1": self.sample_score},
        )
        self.mock_calculate_all_scores = self.all_scores_patch.start()

        # Mock the scorer's get_agent_comparisons method
        self.comparison_patch = patch.object(
            scorer,
            "get_agent_comparisons",
            return_value={
                "timestamp": "2023-05-15T12:00:00Z",
                "rankings": [["agent-1", 85.5]],
                "average_score": 85.5,
                "category_leaders": {
                    "core_values": {"agent_id": "agent-1", "score": 86.5},
                    "frequency": {"agent_id": "agent-1", "score": 84.0},
                    "trend": {"agent_id": "agent-1", "score": 77.5},
                    "recovery": {"agent_id": "agent-1", "score": 100.0},
                    "context": {"agent_id": "agent-1", "score": 85.0},
                },
                "empathy_status": "Healthy",
            },
        )
        self.mock_comparison = self.comparison_patch.start()

        # Mock update_score_cache
        self.update_cache_patch = patch(
            "src.dreamos.api.empathy_scoring.update_score_cache"
        )
        self.mock_update_cache = self.update_cache_patch.start()

        # Add sample score to cache
        global score_cache
        score_cache = {"agent-1": self.sample_score}

    def tearDown(self):
        # Stop patches
        self.scorer_patch.stop()
        self.all_scores_patch.stop()
        self.comparison_patch.stop()
        self.update_cache_patch.stop()

    def test_get_agent_scores(self):
        """Test the /api/empathy/scores endpoint."""
        response = client.get("/api/empathy/scores")
        self.assertEqual(response.status_code, 200)

        # Check response structure
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["agent_id"], "agent-1")

        # Check that update_score_cache was called
        self.mock_update_cache.assert_called_once()

    def test_get_agent_scores_force_update(self):
        """Test the /api/empathy/scores endpoint with force_update=true."""
        response = client.get("/api/empathy/scores?force_update=true")
        self.assertEqual(response.status_code, 200)

        # Check that update_score_cache was called with force=True
        self.mock_update_cache.assert_called_once_with(force=True)

    def test_get_agent_score(self):
        """Test the /api/empathy/scores/{agent_id} endpoint."""
        # Test with agent in cache
        response = client.get("/api/empathy/scores/agent-1")
        self.assertEqual(response.status_code, 200)

        # Check response structure
        data = response.json()
        self.assertEqual(data["agent_id"], "agent-1")
        self.assertEqual(data["score"], 85.5)
        self.assertEqual(data["status"], "proficient")
        self.assertIn("value_scores", data)
        self.assertIn("weighted_components", data)

        # Mock method should not be called since agent is in cache
        self.mock_calculate_score.assert_not_called()

        # Test with agent not in cache
        response = client.get("/api/empathy/scores/agent-2")
        self.assertEqual(response.status_code, 200)

        # Mock method should be called for agent not in cache
        self.mock_calculate_score.assert_called_once_with("agent-2", 30)

    def test_get_agent_comparison(self):
        """Test the /api/empathy/comparison endpoint."""
        response = client.get("/api/empathy/comparison")
        self.assertEqual(response.status_code, 200)

        # Check response structure
        data = response.json()
        self.assertIn("rankings", data)
        self.assertIn("average_score", data)
        self.assertIn("category_leaders", data)
        self.assertIn("empathy_status", data)

        # Check that update_score_cache was called
        self.mock_update_cache.assert_called_once()

    def test_recalculate_agent_score(self):
        """Test the /api/empathy/recalculate/{agent_id} endpoint."""
        response = client.post("/api/empathy/recalculate/agent-1")
        self.assertEqual(response.status_code, 200)

        # Check response structure
        data = response.json()
        self.assertEqual(data["agent_id"], "agent-1")

        # Mock method should be called
        self.mock_calculate_score.assert_called_once_with("agent-1")

    def test_get_empathy_threshold_status(self):
        """Test the /api/empathy/threshold-status endpoint."""
        # Mock the _determine_system_status method
        with patch.object(scorer, "_determine_system_status", return_value="Healthy"):
            response = client.get("/api/empathy/threshold-status")
            self.assertEqual(response.status_code, 200)

            # Check response structure
            data = response.json()
            self.assertIn("timestamp", data)
            self.assertIn("status", data)
            self.assertIn("average_score", data)
            self.assertIn("agents_below_threshold", data)
            self.assertIn("critical_agents", data)

            # Check that update_score_cache was called
            self.mock_update_cache.assert_called_once()

    def test_update_score_cache(self):
        """Test the update_score_cache function."""
        # Setup mock for Path.glob
        with (
            patch("pathlib.Path.glob") as mock_glob,
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", MagicMock()),
            patch.object(scorer, "calculate_all_agent_scores"),
        ):

            # Create mock log files
            mock_glob.return_value = [MagicMock()]

            # Call the function
            update_score_cache(force=True)

            # Check that the scorer method was called
            scorer.calculate_all_agent_scores.assert_called_once()


if __name__ == "__main__":
    unittest.main()
