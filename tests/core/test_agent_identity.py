import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.dreamos.core.agent_identity import AgentIdentity


class TestAgentIdentity(unittest.TestCase):
    """Tests for the enhanced AgentIdentity class with score delta tracking."""
    
    def setUp(self):
        # Mock ethos data
        self.mock_ethos = {
            "version": "1.1.0",
            "core_values": {
                "compassion": {
                    "definition": "Prioritize user wellbeing and autonomy"
                },
                "clarity": {
                    "definition": "Promote understanding and transparency"
                }
            },
            "operational_principles": {
                "transparency": {
                    "definition": "Be clear about capabilities and limitations"
                },
                "responsibility": {
                    "definition": "Take ownership of actions and outcomes"
                }
            }
        }
        
        # Create a patcher for the ethos loading
        self.ethos_patcher = patch('src.dreamos.core.agent_identity.open', 
                                  new=mock_open(read_data=json.dumps(self.mock_ethos)))
        self.mock_ethos_open = self.ethos_patcher.start()
        
        # Mock Path.exists
        self.path_exists_patcher = patch('pathlib.Path.exists', return_value=True)
        self.mock_path_exists = self.path_exists_patcher.start()
        
        # Mock Path.mkdir
        self.path_mkdir_patcher = patch('pathlib.Path.mkdir', return_value=None)
        self.mock_path_mkdir = self.path_mkdir_patcher.start()
        
        # Mock EthosValidator
        self.validator_patcher = patch('src.dreamos.core.agent_identity.EthosValidator')
        self.mock_validator = self.validator_patcher.start()
        self.mock_validator_instance = MagicMock()
        self.mock_validator.return_value = self.mock_validator_instance
        self.mock_validator_instance.validate_identity.return_value = (True, [])
        
        # Mock EmpathyScorer
        self.scorer_patcher = patch('src.dreamos.core.agent_identity.EmpathyScorer')
        self.mock_scorer = self.scorer_patcher.start()
        self.mock_scorer_instance = MagicMock()
        self.mock_scorer.return_value = self.mock_scorer_instance
        
        # Mock DevlogFormatter
        self.devlog_patcher = patch('src.dreamos.core.agent_identity.DevlogFormatter')
        self.mock_devlog = self.devlog_patcher.start()
        self.mock_devlog_instance = MagicMock()
        self.mock_devlog.return_value = self.mock_devlog_instance
        
        # Set up default score data
        self.default_score_data = {
            "agent_id": "test-agent",
            "score": 75.0,
            "status": "developing",
            "summary": "Agent shows developing empathy performance",
            "weighted_components": {
                "core_values": 75.0,
                "frequency": 75.0,
                "trend": 75.0,
                "recovery": 75.0,
                "context": 75.0
            }
        }
        self.mock_scorer_instance.calculate_agent_score.return_value = self.default_score_data
    
    def tearDown(self):
        # Stop patchers
        self.ethos_patcher.stop()
        self.path_exists_patcher.stop()
        self.path_mkdir_patcher.stop()
        self.validator_patcher.stop()
        self.scorer_patcher.stop()
        self.devlog_patcher.stop()
    
    def test_initialize_agent_identity(self):
        """Test initialization of agent identity."""
        identity = AgentIdentity("test-agent")
        
        # Verify basic properties
        self.assertEqual(identity.agent_id, "test-agent")
        self.assertEqual(identity.identity_data["empathy_score"], 75.0)
        self.assertEqual(identity.identity_data["empathy_status"], "developing")
        self.assertEqual(identity.previous_score, 75.0)
        self.assertEqual(identity.score_history, [])
        
        # Verify validator and scorer were initialized
        self.mock_validator.assert_called_once()
        self.mock_scorer.assert_called_once()
        
    def test_update_empathy_score_first_time(self):
        """Test updating empathy score for the first time."""
        # Set up score data
        self.mock_scorer_instance.calculate_agent_score.return_value = {
            "agent_id": "test-agent",
            "score": 80.0,
            "status": "proficient",
            "summary": "Agent shows proficient empathy performance",
            "weighted_components": {
                "core_values": 80.0,
                "frequency": 80.0,
                "trend": 80.0,
                "recovery": 80.0,
                "context": 80.0
            }
        }
        
        # Create identity and update score
        identity = AgentIdentity("test-agent")
        score_data = identity.update_empathy_score()
        
        # Verify score was updated
        self.assertEqual(identity.identity_data["empathy_score"], 80.0)
        self.assertEqual(identity.identity_data["empathy_status"], "proficient")
        
        # Verify score history was updated
        self.assertEqual(len(identity.score_history), 1)
        self.assertEqual(identity.score_history[0]["score"], 80.0)
        self.assertEqual(identity.score_history[0]["previous_score"], 75.0)
        self.assertEqual(identity.score_history[0]["delta"], 5.0)
        self.assertEqual(identity.score_history[0]["status"], "proficient")
        
        # Verify log was created
        self.mock_devlog_instance.format_and_write_identity_update.assert_called()
        # Get the last call arguments
        args, kwargs = self.mock_devlog_instance.format_and_write_identity_update.call_args
        # Check for delta in the message and additional data
        self.assertIn("Δ +5.0", kwargs.get("message", ""))
        self.assertEqual(kwargs.get("score_delta"), 5.0)
        self.assertIn("score_history", kwargs)
        
    def test_update_empathy_score_multiple_times(self):
        """Test updating empathy score multiple times to build history."""
        identity = AgentIdentity("test-agent")
        
        # First update: Increase score
        self.mock_scorer_instance.calculate_agent_score.return_value = {
            "agent_id": "test-agent",
            "score": 80.0,
            "status": "proficient",
            "summary": "Agent shows proficient empathy performance"
        }
        identity.update_empathy_score()
        
        # Second update: Decrease score
        self.mock_scorer_instance.calculate_agent_score.return_value = {
            "agent_id": "test-agent",
            "score": 70.0,
            "status": "developing",
            "summary": "Agent shows developing empathy performance"
        }
        identity.update_empathy_score()
        
        # Third update: Increase score again
        self.mock_scorer_instance.calculate_agent_score.return_value = {
            "agent_id": "test-agent",
            "score": 72.0,
            "status": "developing",
            "summary": "Agent shows developing empathy performance"
        }
        identity.update_empathy_score()
        
        # Verify score history
        self.assertEqual(len(identity.score_history), 3)
        
        # Check first entry
        self.assertEqual(identity.score_history[0]["score"], 80.0)
        self.assertEqual(identity.score_history[0]["delta"], 5.0)
        
        # Check second entry
        self.assertEqual(identity.score_history[1]["score"], 70.0)
        self.assertEqual(identity.score_history[1]["delta"], -10.0)
        
        # Check third entry
        self.assertEqual(identity.score_history[2]["score"], 72.0)
        self.assertEqual(identity.score_history[2]["delta"], 2.0)
        
    def test_log_file_creation(self):
        """Test creation of score evolution log file."""
        # Mock the file open
        mock_file = MagicMock()
        mock_open_func = mock_open(mock=mock_file)
        
        with patch('builtins.open', mock_open_func):
            identity = AgentIdentity("test-agent")
            
            # Update score
            self.mock_scorer_instance.calculate_agent_score.return_value = {
                "agent_id": "test-agent",
                "score": 80.0,
                "status": "proficient",
                "summary": "Agent shows proficient empathy performance"
            }
            identity.update_empathy_score()
            
            # Verify log file was opened
            mock_open_func.assert_called()
            # The file path should contain the agent ID
            file_path = mock_open_func.call_args[0][0]
            self.assertIn("test-agent", str(file_path))
            self.assertIn("score_evolution.log", str(file_path))
            
            # Verify log contents
            handle = mock_open_func()
            handle.write.assert_called()
            
            # Get all write calls
            write_calls = [args[0] for args, kwargs in handle.write.call_args_list]
            
            # Check for key information in the log
            log_content = "".join(write_calls)
            self.assertIn("Previous: 75.0, Current: 80.0, Delta: 5.0", log_content)
            self.assertIn("Status: proficient", log_content)
        
    def test_get_identity_summary_includes_history(self):
        """Test that identity summary includes score history."""
        identity = AgentIdentity("test-agent")
        
        # Update score
        self.mock_scorer_instance.calculate_agent_score.return_value = {
            "agent_id": "test-agent",
            "score": 80.0,
            "status": "proficient",
            "summary": "Agent shows proficient empathy performance"
        }
        identity.update_empathy_score()
        
        # Get summary
        summary = identity.get_identity_summary()
        
        # Verify summary includes score history
        self.assertIn("score_history", summary)
        self.assertEqual(len(summary["score_history"]), 1)
        self.assertEqual(summary["score_history"][0]["score"], 80.0)
        self.assertEqual(summary["score_history"][0]["delta"], 5.0)
        
    def test_large_history_truncation(self):
        """Test that score history is truncated properly."""
        identity = AgentIdentity("test-agent")
        
        # Generate a large history
        for i in range(110):  # More than the 100 limit
            identity.score_history.append({
                "timestamp": datetime.now().isoformat(),
                "score": 75.0 + i,
                "previous_score": 75.0 + (i - 1) if i > 0 else 75.0,
                "delta": 1.0,
                "status": "developing"
            })
        
        # Update score again
        identity.update_empathy_score()
        
        # Verify history was truncated to 100 entries
        self.assertEqual(len(identity.score_history), 100)
        
    def test_get_score_history(self):
        """Test the get_score_history method."""
        identity = AgentIdentity("test-agent")
        
        # Add entries to history
        for i in range(20):
            identity.score_history.append({
                "timestamp": datetime.now().isoformat(),
                "score": 75.0 + i,
                "previous_score": 75.0 + (i - 1) if i > 0 else 75.0,
                "delta": 1.0,
                "status": "developing"
            })
        
        # Get limited history
        history_10 = identity.get_score_history(10)
        # Get full history 
        history_full = identity.get_score_history(30)
        
        # Verify results
        self.assertEqual(len(history_10), 10)
        self.assertEqual(len(history_full), 20)
        
        # Verify the entries are the most recent ones
        self.assertEqual(history_10[0]["score"], 85.0)  # 75 + 10
        self.assertEqual(history_10[-1]["score"], 94.0)  # 75 + 19


if __name__ == '__main__':
    unittest.main() 