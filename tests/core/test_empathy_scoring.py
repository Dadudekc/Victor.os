import json
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import mock_open, patch

# Add the src directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.dreamos.core.empathy_scoring import CONFIG, WEIGHTS, EmpathyScorer


class TestEmpathyScorer(unittest.TestCase):
    """Tests for the EmpathyScorer class."""

    def setUp(self):
        # Mock ethos data
        self.mock_ethos = {
            "version": "1.1.0",
            "last_updated": "2023-05-15",
            "core_mission": {
                "statement": "To augment human potential through ethical, contextual assistance",
                "aspiration": "Creating an evolutional partnership with users",
            },
            "core_values": {
                "compassion": {
                    "definition": "Prioritize user wellbeing and autonomy",
                    "manifestations": ["empathy", "respect", "patience"],
                },
                "clarity": {
                    "definition": "Promote understanding and transparency",
                    "manifestations": ["honesty", "explainability", "simplicity"],
                },
                "collaboration": {
                    "definition": "Work with humans as partners",
                    "manifestations": ["teamwork", "synergy", "amplification"],
                },
                "adaptability": {
                    "definition": "Evolve to better serve human needs",
                    "manifestations": ["learning", "flexibility", "resilience"],
                },
            },
        }

        # Create a patcher for the ethos loading
        self.ethos_patcher = patch(
            "src.dreamos.core.empathy_scoring.open",
            mock_open(read_data=json.dumps(self.mock_ethos)),
        )
        self.mock_ethos_open = self.ethos_patcher.start()

        # Mock Path.exists
        self.path_exists_patcher = patch("pathlib.Path.exists", return_value=True)
        self.mock_path_exists = self.path_exists_patcher.start()

        # Create a scorer instance with mocked ethos
        self.scorer = EmpathyScorer()

        # Mock agent logs
        self.mock_logs = [
            {
                "timestamp": datetime.now().isoformat(),
                "agent_id": "agent-1",
                "type": "compliance",
                "severity": "info",
                "metrics": {"loop_duration": 0.5, "reflection_gap": 0.2},
                "content": "Compliance check passed.",
            },
            {
                "timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
                "agent_id": "agent-1",
                "type": "violation",
                "severity": "low",
                "violated_value": "clarity",
                "metrics": {"loop_duration": 0.8, "reflection_gap": 0.3},
                "content": "Minor violation detected. Violated Value: clarity",
            },
            {
                "timestamp": (datetime.now() - timedelta(days=2)).isoformat(),
                "agent_id": "agent-1",
                "type": "violation",
                "severity": "medium",
                "violated_value": "compassion",
                "resolution": "The issue was addressed successfully.",
                "metrics": {"loop_duration": 1.2, "reflection_gap": 0.5},
                "content": "Medium violation. Violated Value: compassion Resolution: The issue was addressed successfully.",
            },
        ]

    def tearDown(self):
        # Stop patchers
        self.ethos_patcher.stop()
        self.path_exists_patcher.stop()

    def test_initialize(self):
        """Test initialization of the EmpathyScorer."""
        self.assertEqual(self.scorer.ethos, self.mock_ethos)

    def test_initialize_with_config(self):
        """Test initialization with custom config."""
        custom_config = {"score_decay_enabled": False, "decay_half_life_days": 14}
        scorer = EmpathyScorer(config=custom_config)

        # Verify that config was properly merged
        self.assertEqual(scorer.config["score_decay_enabled"], False)
        self.assertEqual(scorer.config["decay_half_life_days"], 14)
        # Other config values should be preserved
        self.assertEqual(scorer.config["min_decay_factor"], CONFIG["min_decay_factor"])

    @patch("src.dreamos.core.empathy_scoring.EmpathyScorer._get_agent_logs")
    def test_calculate_agent_score(self, mock_get_logs):
        """Test calculation of agent score."""
        # Setup the mock to return our test logs
        mock_get_logs.return_value = self.mock_logs

        # Calculate the score
        score = self.scorer.calculate_agent_score("agent-1")

        # Basic validation
        self.assertIsInstance(score, dict)
        self.assertEqual(score["agent_id"], "agent-1")
        self.assertIn("score", score)
        self.assertIn("metrics", score)
        self.assertIn("value_scores", score)
        self.assertIn("frequency", score)
        self.assertIn("trend", score)
        self.assertIn("recovery", score)
        self.assertIn("weighted_components", score)

        # Check metrics
        self.assertEqual(score["metrics"]["violations"], 2)
        self.assertEqual(score["metrics"]["compliances"], 1)

        # Check value scores (should be reduced due to violations)
        self.assertLess(score["value_scores"]["clarity"], 100)
        self.assertLess(score["value_scores"]["compassion"], 100)

        # Check frequency
        self.assertAlmostEqual(score["frequency"]["violation_rate"], 2 / 3, places=2)
        self.assertAlmostEqual(score["frequency"]["compliance_rate"], 1 / 3, places=2)

        # Check recovery
        self.assertEqual(score["recovery"]["recovery_attempts"], 1)
        self.assertEqual(score["recovery"]["successful_recoveries"], 1)
        self.assertEqual(score["recovery"]["recovery_rate"], 1.0)

    @patch("src.dreamos.core.empathy_scoring.EmpathyScorer._get_agent_logs")
    def test_exponential_decay_trend_calculation(self, mock_get_logs):
        """Test the exponential decay trend calculation."""
        # Create logs with timestamps at various ages
        now = datetime.now()
        logs = [
            # Recent logs (high weight with decay)
            {
                "timestamp": now.isoformat(),
                "agent_id": "agent-1",
                "type": "compliance",
                "severity": "info",
                "content": "Compliance check passed.",
            },
            {
                "timestamp": (now - timedelta(days=1)).isoformat(),
                "agent_id": "agent-1",
                "type": "violation",
                "severity": "low",
                "content": "Minor violation detected.",
            },
            # Older logs (lower weight with decay)
            {
                "timestamp": (now - timedelta(days=14)).isoformat(),
                "agent_id": "agent-1",
                "type": "violation",
                "severity": "high",
                "content": "High violation detected.",
            },
        ]

        mock_get_logs.return_value = logs

        # Test with decay enabled
        self.scorer.config["score_decay_enabled"] = True
        score_with_decay = self.scorer.calculate_agent_score("agent-1")

        # Test with decay disabled
        self.scorer.config["score_decay_enabled"] = False
        score_without_decay = self.scorer.calculate_agent_score("agent-1")

        # The trend scores should be different
        self.assertNotEqual(
            score_with_decay["trend"]["overall"],
            score_without_decay["trend"]["overall"],
        )

        # With decay, older violations should have less impact,
        # making the trend more positive than without decay
        self.assertGreater(
            score_with_decay["trend"]["overall"],
            score_without_decay["trend"]["overall"],
        )

    @patch("src.dreamos.core.empathy_scoring.EmpathyScorer._get_agent_logs")
    def test_decay_half_life_effect(self, mock_get_logs):
        """Test the effect of different half-life values on trend calculation."""
        # Create logs with a mix of recent and old logs
        now = datetime.now()
        logs = [
            # Recent compliance (positive impact)
            {"timestamp": now.isoformat(), "agent_id": "agent-1", "type": "compliance"},
            # Old violation (negative impact, but will decay)
            {
                "timestamp": (now - timedelta(days=10)).isoformat(),
                "agent_id": "agent-1",
                "type": "violation",
                "severity": "high",
            },
        ]

        mock_get_logs.return_value = logs

        # Test with short half-life (faster decay)
        self.scorer.config["score_decay_enabled"] = True
        self.scorer.config["decay_half_life_days"] = 3  # Short half-life
        score_fast_decay = self.scorer.calculate_agent_score("agent-1")

        # Test with long half-life (slower decay)
        self.scorer.config["decay_half_life_days"] = 20  # Long half-life
        score_slow_decay = self.scorer.calculate_agent_score("agent-1")

        # With faster decay, old violations have less impact,
        # making the trend more positive than with slower decay
        self.assertGreater(
            score_fast_decay["trend"]["overall"], score_slow_decay["trend"]["overall"]
        )

    @patch("src.dreamos.core.empathy_scoring.EmpathyScorer._get_agent_logs")
    def test_calculate_all_agent_scores(self, mock_get_logs):
        """Test calculation of scores for multiple agents."""

        # Setup the mock to return different logs for different agents
        def get_logs_side_effect(agent_id, days):
            if agent_id == "agent-1":
                return self.mock_logs
            else:
                return [
                    {
                        "timestamp": datetime.now().isoformat(),
                        "agent_id": agent_id,
                        "type": "compliance",
                        "severity": "info",
                        "content": "Compliance check passed.",
                    }
                ]

        mock_get_logs.side_effect = get_logs_side_effect

        # Calculate scores for two agents
        scores = self.scorer.calculate_all_agent_scores(["agent-1", "agent-2"])

        # Validate
        self.assertEqual(len(scores), 2)
        self.assertIn("agent-1", scores)
        self.assertIn("agent-2", scores)

        # Agent-1 should have lower score due to violations
        self.assertLess(scores["agent-1"]["score"], scores["agent-2"]["score"])

    @patch("src.dreamos.core.empathy_scoring.EmpathyScorer.calculate_agent_score")
    def test_get_agent_comparisons(self, mock_calculate_score):
        """Test agent comparison functionality."""
        # Setup mock scores
        mock_calculate_score.side_effect = lambda agent_id: {
            "agent-1": {
                "agent_id": "agent-1",
                "score": 75.0,
                "status": "developing",
                "summary": "Test summary",
                "weighted_components": {
                    "core_values": 70.0,
                    "frequency": 65.0,
                    "trend": 85.0,
                    "recovery": 80.0,
                    "context": 75.0,
                },
            },
            "agent-2": {
                "agent_id": "agent-2",
                "score": 85.0,
                "status": "proficient",
                "summary": "Test summary",
                "weighted_components": {
                    "core_values": 80.0,
                    "frequency": 85.0,
                    "trend": 90.0,
                    "recovery": 85.0,
                    "context": 85.0,
                },
            },
        }.get(agent_id)

        # Store mock scores in agent_scores attribute
        self.scorer.agent_scores = {
            "agent-1": mock_calculate_score("agent-1"),
            "agent-2": mock_calculate_score("agent-2"),
        }

        # Get comparison data
        comparison = self.scorer.get_agent_comparisons(["agent-1", "agent-2"])

        # Validate
        self.assertIn("rankings", comparison)
        self.assertIn("average_score", comparison)
        self.assertIn("category_leaders", comparison)

        # Check rankings (should be sorted by score, highest first)
        self.assertEqual(comparison["rankings"][0][0], "agent-2")
        self.assertEqual(comparison["rankings"][1][0], "agent-1")

        # Check average score
        self.assertAlmostEqual(comparison["average_score"], 80.0, places=1)

        # Check category leaders
        self.assertEqual(
            comparison["category_leaders"]["core_values"]["agent_id"], "agent-2"
        )
        self.assertEqual(comparison["category_leaders"]["trend"]["agent_id"], "agent-2")

    def test_determine_agent_status(self):
        """Test status determination based on score."""
        statuses = [
            (95, "exemplary"),
            (85, "proficient"),
            (75, "developing"),
            (65, "needs_improvement"),
            (55, "critical"),
        ]

        for score, expected_status in statuses:
            self.assertEqual(
                self.scorer._determine_agent_status(score), expected_status
            )

    def test_weights(self):
        """Test that weights are properly defined."""
        # Basic validation of WEIGHTS constant
        self.assertIn("violation_severity", WEIGHTS)
        self.assertIn("frequency", WEIGHTS)
        self.assertIn("recency", WEIGHTS)
        self.assertIn("trend", WEIGHTS)
        self.assertIn("recovery", WEIGHTS)
        self.assertIn("context", WEIGHTS)
        self.assertIn("core_values", WEIGHTS)

        # Check severity weights specifically
        self.assertIn("low", WEIGHTS["violation_severity"])
        self.assertIn("medium", WEIGHTS["violation_severity"])
        self.assertIn("high", WEIGHTS["violation_severity"])
        self.assertIn("critical", WEIGHTS["violation_severity"])

        # Validate that weights make sense (higher severity = lower weight multiplier)
        self.assertGreater(
            WEIGHTS["violation_severity"]["low"], WEIGHTS["violation_severity"]["high"]
        )

    def test_config(self):
        """Test that configuration parameters are properly defined."""
        # Basic validation of CONFIG
        self.assertIn("score_decay_enabled", CONFIG)
        self.assertIn("decay_half_life_days", CONFIG)
        self.assertIn("min_decay_factor", CONFIG)
        self.assertIn("trend_window_days", CONFIG)

        # Verify default values
        self.assertTrue(CONFIG["score_decay_enabled"])
        self.assertGreater(CONFIG["decay_half_life_days"], 0)
        self.assertGreater(CONFIG["min_decay_factor"], 0)
        self.assertGreater(CONFIG["trend_window_days"], 0)


if __name__ == "__main__":
    unittest.main()
