"""
Metrics integration and management functionality.
"""

import logging
import time
import functools
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from .agent_metrics import AgentMetrics, MetricsCollector
from .metrics_visualizer import MetricsVisualizer

class MetricsManager:
    """Manages metrics collection and visualization for agents."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.metrics = AgentMetrics(agent_id)
        self.visualizer = MetricsVisualizer()
    
    def record_action(self, action: str, start_time: float, end_time: float, success: bool = True):
        """Record metrics for an action."""
        duration_ms = (end_time - start_time) * 1000
        self.metrics.record_response_time(action, duration_ms)
        self.metrics.record_success_rate(action, success)
    
    def record_resource(self, resource_type: str, utilization: float):
        """Record resource utilization."""
        self.metrics.record_resource_utilization(resource_type, utilization)
    
    def generate_report(self, output_file: Optional[str] = None):
        """Generate a metrics report."""
        metrics_data = {
            'response_times': self.metrics.get_response_times(),
            'success_rates': self.metrics.get_success_rates(),
            'resource_utilization': self.metrics.get_resource_utilization()
        }
        return self.visualizer.generate_html_report(metrics_data, output_file)

class MetricsDecorator:
    """Decorator for automatically recording metrics for functions."""
    
    def __init__(self, agent_id: str):
        self.manager = MetricsManager(agent_id)
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise e
            finally:
                end_time = time.time()
                self.manager.record_action(func.__name__, start_time, end_time, success)
            return result
        return wrapper

class MetricsManager:
    def __init__(self, metrics_file: str = "metrics.json"):
        self.logger = logging.getLogger(__name__)
        self.metrics = AgentMetrics()
        self.collector = MetricsCollector(self.metrics)
        self.visualizer = MetricsVisualizer()
        self.metrics_file = metrics_file
        self._load_metrics()

    def _load_metrics(self) -> None:
        """Load existing metrics from file."""
        try:
            self.metrics.load_metrics(self.metrics_file)
            self.logger.info(f"Loaded metrics from {self.metrics_file}")
        except Exception as e:
            self.logger.warning(f"Could not load metrics: {str(e)}")

    def _save_metrics(self) -> None:
        """Save metrics to file."""
        try:
            self.metrics.save_metrics(self.metrics_file)
            self.logger.info(f"Saved metrics to {self.metrics_file}")
        except Exception as e:
            self.logger.error(f"Failed to save metrics: {str(e)}")

    def start_action(self, agent_id: str, action: str) -> None:
        """Start timing an action."""
        self.collector.start_action(agent_id, action)

    def end_action(self, agent_id: str, action: str, success: bool = True) -> None:
        """End timing an action and record metrics."""
        self.collector.end_action(agent_id, action, success)
        self._save_metrics()

    def record_resource(self, agent_id: str, resource_type: str, value: float) -> None:
        """Record resource utilization."""
        self.collector.record_resource(agent_id, resource_type, value)
        self._save_metrics()

    def get_metrics(self, metric_type: str, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get metrics of a specific type."""
        return self.metrics.get_metrics(metric_type, agent_id)

    def get_average_response_time(self, agent_id: Optional[str] = None) -> float:
        """Get average response time."""
        return self.metrics.get_average_response_time(agent_id)

    def get_success_rate(self, agent_id: Optional[str] = None) -> float:
        """Get success rate."""
        return self.metrics.get_success_rate(agent_id)

    def get_resource_utilization(self, agent_id: Optional[str] = None, 
                               resource_type: Optional[str] = None) -> Dict[str, float]:
        """Get resource utilization."""
        return self.metrics.get_resource_utilization(agent_id, resource_type)

    def generate_report(self, output_file: str = "metrics_report.html") -> None:
        """Generate metrics report."""
        self.visualizer.generate_report(self.metrics.metrics_store, output_file)

    def plot_response_times(self, agent_id: Optional[str] = None,
                          time_window: Optional[timedelta] = None) -> None:
        """Plot response time trends."""
        self.visualizer.plot_response_times(self.metrics.metrics_store, agent_id, time_window)

    def plot_success_rates(self, agent_id: Optional[str] = None,
                         time_window: Optional[timedelta] = None) -> None:
        """Plot success rate trends."""
        self.visualizer.plot_success_rates(self.metrics.metrics_store, agent_id, time_window)

    def plot_resource_utilization(self, agent_id: Optional[str] = None,
                                resource_type: Optional[str] = None,
                                time_window: Optional[timedelta] = None) -> None:
        """Plot resource utilization trends."""
        self.visualizer.plot_resource_utilization(
            self.metrics.metrics_store, agent_id, resource_type, time_window)

class MetricsDecorator:
    def __init__(self, metrics_manager: MetricsManager):
        self.metrics_manager = metrics_manager

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # Extract agent_id from args or kwargs
            agent_id = kwargs.get('agent_id', args[0] if args else None)
            if not agent_id:
                raise ValueError("agent_id must be provided")

            # Start timing
            self.metrics_manager.start_action(agent_id, func.__name__)
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise e
            finally:
                # Record metrics
                self.metrics_manager.end_action(agent_id, func.__name__, success)
            
            return result
        return wrapper 