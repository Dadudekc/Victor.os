"""
Test suite for the metrics package.
"""

import unittest
import time
import json
from pathlib import Path
from datetime import datetime
from ..agent_metrics import AgentMetrics, MetricsCollector
from ..metrics_visualizer import MetricsVisualizer
from ..metrics_integration import MetricsManager, MetricsDecorator

class TestAgentMetrics(unittest.TestCase):
    def setUp(self):
        self.agent_id = "test_agent"
        self.metrics = AgentMetrics(self.agent_id)
        self.metrics_file = Path("runtime/metrics") / f"{self.agent_id}_metrics.json"
    
    def tearDown(self):
        if self.metrics_file.exists():
            self.metrics_file.unlink()
    
    def test_record_response_time(self):
        self.metrics.record_response_time("test_action", 100.0)
        response_times = self.metrics.get_response_times()
        self.assertEqual(len(response_times), 1)
        self.assertEqual(response_times[0]["action"], "test_action")
        self.assertEqual(response_times[0]["duration_ms"], 100.0)
    
    def test_record_success_rate(self):
        self.metrics.record_success_rate("test_action", True)
        success_rates = self.metrics.get_success_rates()
        self.assertEqual(len(success_rates), 1)
        self.assertEqual(success_rates[0]["action"], "test_action")
        self.assertTrue(success_rates[0]["success"])
    
    def test_record_resource_utilization(self):
        self.metrics.record_resource_utilization("cpu", 0.5)
        resource_util = self.metrics.get_resource_utilization()
        self.assertEqual(len(resource_util), 1)
        self.assertEqual(resource_util[0]["resource_type"], "cpu")
        self.assertEqual(resource_util[0]["utilization"], 0.5)

class TestMetricsCollector(unittest.TestCase):
    def setUp(self):
        self.collector = MetricsCollector()
        self.agent1 = AgentMetrics("agent1")
        self.agent2 = AgentMetrics("agent2")
    
    def tearDown(self):
        for agent_id in ["agent1", "agent2"]:
            metrics_file = Path("runtime/metrics") / f"{agent_id}_metrics.json"
            if metrics_file.exists():
                metrics_file.unlink()
    
    def test_get_all_agent_metrics(self):
        metrics = self.collector.get_all_agent_metrics()
        self.assertEqual(len(metrics), 2)
        self.assertIn("agent1", metrics)
        self.assertIn("agent2", metrics)
    
    def test_get_aggregate_response_times(self):
        self.agent1.record_response_time("action1", 100.0)
        self.agent2.record_response_time("action2", 200.0)
        response_times = self.collector.get_aggregate_response_times()
        self.assertEqual(len(response_times), 2)

class TestMetricsVisualizer(unittest.TestCase):
    def setUp(self):
        self.visualizer = MetricsVisualizer()
        self.output_dir = Path("runtime/metrics/reports")
    
    def tearDown(self):
        if self.output_dir.exists():
            for file in self.output_dir.glob("*"):
                file.unlink()
    
    def test_plot_response_times(self):
        response_times = [
            {"timestamp": datetime.now().isoformat(), "action": "test", "duration_ms": 100.0}
        ]
        fig = self.visualizer.plot_response_times(response_times)
        self.assertIsNotNone(fig)
    
    def test_plot_success_rates(self):
        success_rates = [
            {"timestamp": datetime.now().isoformat(), "action": "test", "success": True}
        ]
        fig = self.visualizer.plot_success_rates(success_rates)
        self.assertIsNotNone(fig)
    
    def test_plot_resource_utilization(self):
        resource_utilization = [
            {"timestamp": datetime.now().isoformat(), "resource_type": "cpu", "utilization": 0.5}
        ]
        fig = self.visualizer.plot_resource_utilization(resource_utilization)
        self.assertIsNotNone(fig)
    
    def test_generate_html_report(self):
        metrics_data = {
            "response_times": [
                {"timestamp": datetime.now().isoformat(), "action": "test", "duration_ms": 100.0}
            ],
            "success_rates": [
                {"timestamp": datetime.now().isoformat(), "action": "test", "success": True}
            ],
            "resource_utilization": [
                {"timestamp": datetime.now().isoformat(), "resource_type": "cpu", "utilization": 0.5}
            ]
        }
        report_file = self.visualizer.generate_html_report(metrics_data)
        self.assertTrue(Path(report_file).exists())

class TestMetricsIntegration(unittest.TestCase):
    def setUp(self):
        self.agent_id = "test_agent"
        self.manager = MetricsManager(self.agent_id)
        self.decorator = MetricsDecorator(self.agent_id)
    
    def tearDown(self):
        metrics_file = Path("runtime/metrics") / f"{self.agent_id}_metrics.json"
        if metrics_file.exists():
            metrics_file.unlink()
    
    def test_record_action(self):
        start_time = time.time()
        end_time = start_time + 0.1
        self.manager.record_action("test_action", start_time, end_time, True)
        response_times = self.manager.metrics.get_response_times()
        self.assertEqual(len(response_times), 1)
        self.assertEqual(response_times[0]["action"], "test_action")
    
    def test_record_resource(self):
        self.manager.record_resource("cpu", 0.5)
        resource_util = self.manager.metrics.get_resource_utilization()
        self.assertEqual(len(resource_util), 1)
        self.assertEqual(resource_util[0]["resource_type"], "cpu")
        self.assertEqual(resource_util[0]["utilization"], 0.5)
    
    def test_metrics_decorator(self):
        @self.decorator
        def test_function():
            time.sleep(0.1)
            return True
        
        result = test_function()
        self.assertTrue(result)
        response_times = self.manager.metrics.get_response_times()
        self.assertEqual(len(response_times), 1)
        self.assertEqual(response_times[0]["action"], "test_function")

if __name__ == "__main__":
    unittest.main() 