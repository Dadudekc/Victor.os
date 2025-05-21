import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MetricsTracker:
    def __init__(self, metrics_dir: str = 'runtime/metrics'):
        self.metrics_dir = metrics_dir
        self.current_file = os.path.join(metrics_dir, 'current_metrics.json')
        self.history_file = os.path.join(metrics_dir, 'metrics_history.json')
        os.makedirs(metrics_dir, exist_ok=True)

    def record_metrics(self, agent_id: str, metrics: Dict[str, Any]):
        """Record metrics for an agent."""
        try:
            if os.path.exists(self.current_file):
                with open(self.current_file, 'r') as f:
                    current_metrics = json.load(f)
            else:
                current_metrics = {}

            current_metrics[agent_id] = {
                'timestamp': datetime.now().isoformat(),
                'metrics': metrics
            }

            with open(self.current_file, 'w') as f:
                json.dump(current_metrics, f, indent=2)
            logger.info(f"Recorded metrics for {agent_id}")
        except Exception as e:
            logger.error(f"Failed to record metrics for {agent_id}: {e}")

    def archive_metrics(self):
        """Archive current metrics to history."""
        try:
            if not os.path.exists(self.current_file):
                return

            with open(self.current_file, 'r') as f:
                current_metrics = json.load(f)

            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []

            history.append({
                'timestamp': datetime.now().isoformat(),
                'metrics': current_metrics
            })

            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)

            os.remove(self.current_file)
            logger.info("Metrics archived to history")
        except Exception as e:
            logger.error(f"Failed to archive metrics: {e}")

    def get_current_metrics(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current metrics for an agent or all agents."""
        try:
            if not os.path.exists(self.current_file):
                return {}

            with open(self.current_file, 'r') as f:
                current_metrics = json.load(f)

            if agent_id:
                return current_metrics.get(agent_id, {})
            return current_metrics
        except Exception as e:
            logger.error(f"Failed to get current metrics: {e}")
            return {}

    def get_metrics_history(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get metrics history for an agent or all agents."""
        try:
            if not os.path.exists(self.history_file):
                return []

            with open(self.history_file, 'r') as f:
                history = json.load(f)

            if agent_id:
                return [entry for entry in history if agent_id in entry['metrics']]
            return history
        except Exception as e:
            logger.error(f"Failed to get metrics history: {e}")
            return []

if __name__ == "__main__":
    # Example usage
    tracker = MetricsTracker()
    tracker.record_metrics('Agent-1', {'tasks_completed': 10, 'errors': 0})
    tracker.archive_metrics()
    print(tracker.get_current_metrics('Agent-1'))
    print(tracker.get_metrics_history('Agent-1')) 