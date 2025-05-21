import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from collections import defaultdict
import json
import os

logger = logging.getLogger(__name__)

class QueryMetrics:
    """Metrics collection for query processing."""
    
    def __init__(self, metrics_dir: str = "runtime/metrics/agent_004"):
        """Initialize metrics collection.
        
        Args:
            metrics_dir: Directory to store metrics files
        """
        self.metrics_dir = metrics_dir
        self._ensure_metrics_dir()
        
        # Initialize metrics storage
        self.query_counts = defaultdict(int)
        self.query_types = defaultdict(int)
        self.response_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.context_usage = defaultdict(int)
        
        # Load existing metrics if available
        self._load_metrics()
    
    def _ensure_metrics_dir(self):
        """Ensure metrics directory exists."""
        os.makedirs(self.metrics_dir, exist_ok=True)
    
    def _load_metrics(self):
        """Load existing metrics from disk."""
        try:
            metrics_file = os.path.join(self.metrics_dir, "query_metrics.json")
            if os.path.exists(metrics_file):
                with open(metrics_file, "r") as f:
                    data = json.load(f)
                    self.query_counts = defaultdict(int, data.get("query_counts", {}))
                    self.query_types = defaultdict(int, data.get("query_types", {}))
                    self.error_counts = defaultdict(int, data.get("error_counts", {}))
                    self.context_usage = defaultdict(int, data.get("context_usage", {}))
        except Exception as e:
            logger.error(f"Error loading metrics: {str(e)}")
    
    def _save_metrics(self):
        """Save current metrics to disk."""
        try:
            metrics_file = os.path.join(self.metrics_dir, "query_metrics.json")
            data = {
                "query_counts": dict(self.query_counts),
                "query_types": dict(self.query_types),
                "error_counts": dict(self.error_counts),
                "context_usage": dict(self.context_usage),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            with open(metrics_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metrics: {str(e)}")
    
    def record_query(self, query: str, query_type: str, response_time: float, 
                    context_used: bool = False, error: Optional[str] = None):
        """Record a query processing event.
        
        Args:
            query: The processed query
            query_type: Type of query (information, action, status, general)
            response_time: Time taken to process query in seconds
            context_used: Whether context was used in processing
            error: Error message if any
        """
        # Record query count
        self.query_counts[query_type] += 1
        
        # Record query type distribution
        self.query_types[query_type] += 1
        
        # Record response time
        self.response_times[query_type].append(response_time)
        
        # Record context usage
        if context_used:
            self.context_usage[query_type] += 1
        
        # Record error if any
        if error:
            self.error_counts[query_type] += 1
        
        # Save metrics periodically
        if sum(self.query_counts.values()) % 10 == 0:  # Save every 10 queries
            self._save_metrics()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics.
        
        Returns:
            Dictionary containing metrics summary
        """
        total_queries = sum(self.query_counts.values())
        total_errors = sum(self.error_counts.values())
        
        # Calculate average response times
        avg_response_times = {}
        for query_type, times in self.response_times.items():
            if times:
                avg_response_times[query_type] = sum(times) / len(times)
        
        return {
            "total_queries": total_queries,
            "query_type_distribution": dict(self.query_types),
            "average_response_times": avg_response_times,
            "error_rate": total_errors / total_queries if total_queries > 0 else 0,
            "context_usage_rate": {
                qtype: count / self.query_counts[qtype] if self.query_counts[qtype] > 0 else 0
                for qtype, count in self.context_usage.items()
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    def reset_metrics(self):
        """Reset all metrics to zero."""
        self.query_counts.clear()
        self.query_types.clear()
        self.response_times.clear()
        self.error_counts.clear()
        self.context_usage.clear()
        self._save_metrics() 