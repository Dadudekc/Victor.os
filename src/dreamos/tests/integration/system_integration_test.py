"""
System Integration Test Suite for Dream.OS
Tests all core components and their interactions.
"""

import unittest
import json
import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from dreamos.core.config import AppConfig
from dreamos.core.project_board import ProjectBoardManager
from dreamos.agents.agent_manager import AgentManager
from dreamos.agents.agent import Agent
from dreamos.agents.mailbox import Mailbox
from dreamos.agents.state import AgentState
from dreamos.agents.metrics import AgentMetrics
from dreamos.agents.validation import AgentValidation
from dreamos.agents.improvement import AgentImprovement
from dreamos.agents.documentation import AgentDocumentation
from dreamos.agents.leaderboard import AgentLeaderboard
from dreamos.agents.jarvis import JarvisIntegration
from dreamos.agents.health import AgentHealth
from dreamos.agents.load import AgentLoad
from dreamos.agents.chaos import AgentChaos
from dreamos.orchestration.swarm_controller import SwarmController
from dreamos.orchestration.swarm_cycle_test import SwarmCycleTest

class TestSystemIntegration(unittest.TestCase):
    """Integration tests for the entire Dream.OS system."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
        cls.runtime_dir = os.path.join(cls.workspace_root, 'runtime')
        cls.test_results_dir = os.path.join(cls.runtime_dir, 'test_results')
        
        # Create necessary directories
        os.makedirs(cls.test_results_dir, exist_ok=True)
        
        # Load configuration
        cls.config = AppConfig()
        cls.project_board = ProjectBoardManager(cls.config)
        
        # Initialize components
        cls.agent_manager = AgentManager(cls.config)
        cls.swarm_controller = SwarmController()
        cls.swarm_cycle_test = SwarmCycleTest()
        
    def test_agent_system_integration(self):
        """Test integration between agent system components."""
        # Create test agent
        agent = Agent(
            agent_id="TEST-AGENT-1",
            config=self.config,
            project_board=self.project_board
        )
        
        # Test agent initialization
        self.assertTrue(agent.initialize())
        self.assertEqual(agent.state.status, "ONBOARDING")
        
        # Test mailbox integration
        test_message = {
            "type": "test",
            "content": "Test message",
            "timestamp": datetime.now().isoformat()
        }
        agent.mailbox.send_message(test_message)
        received_message = agent.mailbox.receive_message()
        self.assertEqual(received_message, test_message)
        
        # Test metrics collection
        metrics = agent.metrics.collect_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertIn("performance", metrics)
        
        # Test validation
        validation_result = agent.validation.validate_state()
        self.assertTrue(validation_result["is_valid"])
        
    def test_swarm_controller_integration(self):
        """Test swarm controller integration with agent system."""
        # Test agent launch
        agent_config = {
            "agent_id": "TEST-AGENT-2",
            "script_path": "src/dreamos/agents/test_agent.py"
        }
        launch_result = self.swarm_controller.launch_agent(
            agent_config["agent_id"],
            agent_config
        )
        self.assertIsNotNone(launch_result)
        
        # Test agent status
        status = self.swarm_controller.get_agent_status(agent_config["agent_id"])
        self.assertEqual(status["status"], "running")
        
        # Test agent termination
        terminate_result = self.swarm_controller.terminate_agent(agent_config["agent_id"])
        self.assertEqual(terminate_result["status"], "terminated")
        
    def test_swarm_cycle_test_integration(self):
        """Test swarm cycle test integration."""
        # Run cycle test
        test_results = self.swarm_cycle_test.run_test(num_cycles=5)
        
        # Verify test results
        self.assertIsInstance(test_results, dict)
        self.assertIn("system_metrics", test_results)
        self.assertIn("cycles", test_results)
        
        # Check metrics
        metrics = test_results["system_metrics"]
        self.assertGreaterEqual(metrics["total_cycles"], 5)
        self.assertGreaterEqual(metrics["successful_cycles"], 0)
        
    def test_system_flow_optimization(self):
        """Test system flow optimization."""
        # Generate recommendations
        recommendations = self.agent_manager.generate_integration_recommendations()
        
        # Verify recommendations
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
        
        # Check for specific recommendation types
        recommendation_types = [r["type"] for r in recommendations]
        self.assertIn("Integration", recommendation_types)
        self.assertIn("Performance", recommendation_types)
        self.assertIn("Workflow", recommendation_types)
        
    def test_error_handling_integration(self):
        """Test error handling integration across components."""
        # Simulate error condition
        error_message = {
            "type": "error",
            "content": "Test error",
            "severity": "critical",
            "timestamp": datetime.now().isoformat()
        }
        
        # Test error propagation
        self.agent_manager.handle_error(error_message)
        
        # Verify error handling
        error_log = os.path.join(self.runtime_dir, "logs", "error.log")
        self.assertTrue(os.path.exists(error_log))
        
        # Check error recovery
        recovery_status = self.agent_manager.check_error_recovery()
        self.assertTrue(recovery_status["recovered"])
        
    def test_state_management_integration(self):
        """Test state management integration."""
        # Create test state
        test_state = AgentState(
            agent_id="TEST-AGENT-3",
            status="TESTING",
            metrics={},
            timestamp=datetime.now().isoformat()
        )
        
        # Save state
        self.agent_manager.save_agent_state(test_state)
        
        # Load state
        loaded_state = self.agent_manager.load_agent_state("TEST-AGENT-3")
        self.assertEqual(loaded_state.status, test_state.status)
        
        # Test state restoration
        restore_result = self.agent_manager.restore_agent_state("TEST-AGENT-3")
        self.assertTrue(restore_result["success"])
        
    def test_monitoring_integration(self):
        """Test monitoring system integration."""
        # Collect system metrics
        system_metrics = self.agent_manager.collect_system_metrics()
        
        # Verify metrics
        self.assertIsInstance(system_metrics, dict)
        self.assertIn("performance", system_metrics)
        self.assertIn("health", system_metrics)
        
        # Test health check
        health_status = self.agent_manager.check_system_health()
        self.assertTrue(health_status["healthy"])
        
        # Test performance monitoring
        performance_metrics = self.agent_manager.monitor_performance()
        self.assertIsInstance(performance_metrics, dict)
        self.assertIn("response_time", performance_metrics)
        
    def test_documentation_integration(self):
        """Test documentation system integration."""
        # Generate documentation
        doc_result = self.agent_manager.generate_documentation()
        
        # Verify documentation
        self.assertTrue(doc_result["success"])
        self.assertIsInstance(doc_result["documentation"], dict)
        
        # Check documentation content
        doc_content = doc_result["documentation"]
        self.assertIn("system_architecture", doc_content)
        self.assertIn("component_interactions", doc_content)
        self.assertIn("error_handling", doc_content)
        
    def test_improvement_integration(self):
        """Test improvement system integration."""
        # Generate improvements
        improvements = self.agent_manager.generate_improvements()
        
        # Verify improvements
        self.assertIsInstance(improvements, list)
        self.assertGreater(len(improvements), 0)
        
        # Check improvement types
        improvement_types = [i["type"] for i in improvements]
        self.assertIn("Performance", improvement_types)
        self.assertIn("Reliability", improvement_types)
        self.assertIn("Efficiency", improvement_types)
        
    def test_leaderboard_integration(self):
        """Test leaderboard system integration."""
        # Update leaderboard
        leaderboard_result = self.agent_manager.update_leaderboard()
        
        # Verify leaderboard
        self.assertTrue(leaderboard_result["success"])
        self.assertIsInstance(leaderboard_result["leaderboard"], dict)
        
        # Check leaderboard content
        leaderboard = leaderboard_result["leaderboard"]
        self.assertIn("agents", leaderboard)
        self.assertIn("metrics", leaderboard)
        self.assertIn("rankings", leaderboard)

if __name__ == "__main__":
    unittest.main() 