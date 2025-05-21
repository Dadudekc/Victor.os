import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StatusMonitor:
    def __init__(self, status_dir: str = 'runtime/status'):
        self.status_dir = status_dir
        self.heartbeat_file = os.path.join(status_dir, 'heartbeat.json')
        self.devlog_file = os.path.join(status_dir, 'devlog.json')
        os.makedirs(status_dir, exist_ok=True)

    def update_heartbeat(self, agent_id: str, status: Dict[str, Any]):
        """Update the heartbeat status for an agent."""
        try:
            if os.path.exists(self.heartbeat_file):
                with open(self.heartbeat_file, 'r') as f:
                    heartbeats = json.load(f)
            else:
                heartbeats = {}

            heartbeats[agent_id] = {
                'timestamp': datetime.now().isoformat(),
                'status': status
            }

            with open(self.heartbeat_file, 'w') as f:
                json.dump(heartbeats, f, indent=2)
            logger.info(f"Updated heartbeat for {agent_id}")
        except Exception as e:
            logger.error(f"Failed to update heartbeat for {agent_id}: {e}")

    def add_devlog_entry(self, agent_id: str, entry: Dict[str, Any]):
        """Add a devlog entry for an agent."""
        try:
            if os.path.exists(self.devlog_file):
                with open(self.devlog_file, 'r') as f:
                    devlog = json.load(f)
            else:
                devlog = {}

            if agent_id not in devlog:
                devlog[agent_id] = []

            entry['timestamp'] = datetime.now().isoformat()
            devlog[agent_id].append(entry)

            with open(self.devlog_file, 'w') as f:
                json.dump(devlog, f, indent=2)
            logger.info(f"Added devlog entry for {agent_id}")
        except Exception as e:
            logger.error(f"Failed to add devlog entry for {agent_id}: {e}")

    def get_heartbeat(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get heartbeat status for an agent or all agents."""
        try:
            if not os.path.exists(self.heartbeat_file):
                return {}

            with open(self.heartbeat_file, 'r') as f:
                heartbeats = json.load(f)

            if agent_id:
                return heartbeats.get(agent_id, {})
            return heartbeats
        except Exception as e:
            logger.error(f"Failed to get heartbeat: {e}")
            return {}

    def get_devlog(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get devlog entries for an agent or all agents."""
        try:
            if not os.path.exists(self.devlog_file):
                return {}

            with open(self.devlog_file, 'r') as f:
                devlog = json.load(f)

            if agent_id:
                return devlog.get(agent_id, [])
            return devlog
        except Exception as e:
            logger.error(f"Failed to get devlog: {e}")
            return {}

if __name__ == "__main__":
    # Example usage
    monitor = StatusMonitor()
    monitor.update_heartbeat('Agent-1', {'status': 'ACTIVE', 'message': 'Hello, world!'})
    monitor.add_devlog_entry('Agent-1', {'event': 'startup', 'details': 'System initialized'})
    print(monitor.get_heartbeat('Agent-1'))
    print(monitor.get_devlog('Agent-1')) 