"""
Core metrics collection and management for agent responses.
"""

import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

class AgentMetrics:
    """Manages metrics collection for individual agents."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.metrics_dir = Path("runtime/metrics")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.metrics_dir / f"{agent_id}_metrics.json"
        self._load_metrics()
    
    def _load_metrics(self):
        """Load existing metrics from file."""
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                self.metrics = json.load(f)
        else:
            self.metrics = {
                'response_times': [],
                'success_rates': [],
                'resource_utilization': []
            }
    
    def _save_metrics(self):
        """Save metrics to file."""
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
    
    def record_response_time(self, action: str, duration_ms: float):
        """Record response time for an action."""
        self.metrics['response_times'].append({
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'duration_ms': duration_ms
        })
        self._save_metrics()
    
    def record_success_rate(self, action: str, success: bool):
        """Record success/failure for an action."""
        self.metrics['success_rates'].append({
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'success': success
        })
        self._save_metrics()
    
    def record_resource_utilization(self, resource_type: str, utilization: float):
        """Record resource utilization."""
        self.metrics['resource_utilization'].append({
            'timestamp': datetime.now().isoformat(),
            'resource_type': resource_type,
            'utilization': utilization
        })
        self._save_metrics()
    
    def get_response_times(self, action: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get response times, optionally filtered by action."""
        if action:
            return [rt for rt in self.metrics['response_times'] if rt['action'] == action]
        return self.metrics['response_times']
    
    def get_success_rates(self, action: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get success rates, optionally filtered by action."""
        if action:
            return [sr for sr in self.metrics['success_rates'] if sr['action'] == action]
        return self.metrics['success_rates']
    
    def get_resource_utilization(self, resource_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get resource utilization, optionally filtered by resource type."""
        if resource_type:
            return [ru for ru in self.metrics['resource_utilization'] if ru['resource_type'] == resource_type]
        return self.metrics['resource_utilization']

class MetricsCollector:
    """Collects metrics across multiple agents."""
    
    def __init__(self):
        self.metrics_dir = Path("runtime/metrics")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
    
    def get_all_agent_metrics(self) -> Dict[str, AgentMetrics]:
        """Get metrics for all agents."""
        metrics = {}
        for metrics_file in self.metrics_dir.glob("*_metrics.json"):
            agent_id = metrics_file.stem.replace("_metrics", "")
            metrics[agent_id] = AgentMetrics(agent_id)
        return metrics
    
    def get_aggregate_response_times(self, action: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get aggregate response times across all agents."""
        all_times = []
        for agent_metrics in self.get_all_agent_metrics().values():
            all_times.extend(agent_metrics.get_response_times(action))
        return sorted(all_times, key=lambda x: x['timestamp'])
    
    def get_aggregate_success_rates(self, action: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get aggregate success rates across all agents."""
        all_rates = []
        for agent_metrics in self.get_all_agent_metrics().values():
            all_rates.extend(agent_metrics.get_success_rates(action))
        return sorted(all_rates, key=lambda x: x['timestamp'])
    
    def get_aggregate_resource_utilization(self, resource_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get aggregate resource utilization across all agents."""
        all_util = []
        for agent_metrics in self.get_all_agent_metrics().values():
            all_util.extend(agent_metrics.get_resource_utilization(resource_type))
        return sorted(all_util, key=lambda x: x['timestamp']) 