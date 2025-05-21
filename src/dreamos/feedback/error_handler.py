import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ErrorHandler:
    def __init__(self, error_dir: str = 'runtime/errors'):
        self.error_dir = error_dir
        self.error_file = os.path.join(error_dir, 'error_log.json')
        self.alert_file = os.path.join(error_dir, 'alerts.json')
        os.makedirs(error_dir, exist_ok=True)

    def handle_error(self, agent_id: str, error: Exception, retry_func: Optional[Callable] = None, max_retries: int = 3):
        """Handle an error with optional retry logic."""
        try:
            error_entry = {
                'timestamp': datetime.now().isoformat(),
                'agent_id': agent_id,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'retries': 0
            }

            if os.path.exists(self.error_file):
                with open(self.error_file, 'r') as f:
                    error_log = json.load(f)
            else:
                error_log = []

            error_log.append(error_entry)

            with open(self.error_file, 'w') as f:
                json.dump(error_log, f, indent=2)
            logger.error(f"Error logged for {agent_id}: {error}")

            if retry_func:
                self._retry_operation(agent_id, retry_func, max_retries)
        except Exception as e:
            logger.error(f"Failed to handle error: {e}")

    def _retry_operation(self, agent_id: str, retry_func: Callable, max_retries: int):
        """Retry a failed operation."""
        retries = 0
        while retries < max_retries:
            try:
                retry_func()
                logger.info(f"Retry successful for {agent_id} after {retries + 1} attempts")
                return
            except Exception as e:
                retries += 1
                logger.warning(f"Retry {retries} failed for {agent_id}: {e}")
                time.sleep(2 ** retries)  # Exponential backoff

        self.raise_alert(agent_id, f"Operation failed after {max_retries} retries")

    def raise_alert(self, agent_id: str, message: str, severity: str = 'warning'):
        """Raise an alert for an agent."""
        try:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'agent_id': agent_id,
                'message': message,
                'severity': severity
            }

            if os.path.exists(self.alert_file):
                with open(self.alert_file, 'r') as f:
                    alerts = json.load(f)
            else:
                alerts = []

            alerts.append(alert)

            with open(self.alert_file, 'w') as f:
                json.dump(alerts, f, indent=2)
            logger.warning(f"Alert raised for {agent_id}: {message}")
        except Exception as e:
            logger.error(f"Failed to raise alert: {e}")

    def get_error_log(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get error log for an agent or all agents."""
        try:
            if not os.path.exists(self.error_file):
                return []

            with open(self.error_file, 'r') as f:
                error_log = json.load(f)

            if agent_id:
                return [entry for entry in error_log if entry['agent_id'] == agent_id]
            return error_log
        except Exception as e:
            logger.error(f"Failed to get error log: {e}")
            return []

    def get_alerts(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get alerts for an agent or all agents."""
        try:
            if not os.path.exists(self.alert_file):
                return []

            with open(self.alert_file, 'r') as f:
                alerts = json.load(f)

            if agent_id:
                return [alert for alert in alerts if alert['agent_id'] == agent_id]
            return alerts
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []

if __name__ == "__main__":
    # Example usage
    handler = ErrorHandler()

    def example_operation():
        raise ValueError("Example error")

    handler.handle_error('Agent-1', ValueError("Test error"), example_operation)
    handler.raise_alert('Agent-1', 'Test alert', 'warning')
    print(handler.get_error_log('Agent-1'))
    print(handler.get_alerts('Agent-1')) 