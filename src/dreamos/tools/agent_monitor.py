import time
import json
import logging
from pathlib import Path
from threading import Thread, Event
from typing import Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger("agent_monitor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class AgentMonitor:
    def __init__(self, outbox_dir="runtime/bridge_outbox", check_interval=30, timeout=120):
        self.outbox = Path(outbox_dir)
        self.interval = check_interval
        self.timeout = timeout
        self.stop_event = Event()
        self.last_seen: Dict[str, float] = {}  # agent_id -> timestamp of last response
        self.metrics_dir = Path("runtime/monitor/metrics")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.alert_dir = Path("runtime/monitor/unresponsive")
        self.alert_dir.mkdir(parents=True, exist_ok=True)
        self.status_dir = Path("runtime/agent_comms/agent_mailboxes")
        self.status_dir.mkdir(parents=True, exist_ok=True)
        self.wake_confirmations: Dict[str, bool] = {}  # agent_id -> wake confirmation status
        
    def start(self):
        """Start the monitoring loop in a background thread."""
        Thread(target=self._watch_loop, daemon=True).start()
        logger.info("AgentMonitor started.")
        
    def stop(self):
        """Stop the monitoring loop."""
        self.stop_event.set()
        logger.info("AgentMonitor stopped.")
        
    def _watch_loop(self):
        """Main monitoring loop that checks agent responsiveness."""
        while not self.stop_event.is_set():
            try:
                for agent_dir in self.outbox.iterdir():
                    if agent_dir.is_dir():
                        agent_id = agent_dir.name
                        resp_file = agent_dir / "last_cellphone_response.json"
                        status_file = self.status_dir / agent_id / "status.json"
                        
                        # Update last seen timestamp
                        if resp_file.exists():
                            ts = resp_file.stat().st_mtime
                            self.last_seen[agent_id] = ts
                            
                            # Record metrics
                            self._record_metrics(agent_id, ts)
                            
                            # Update status.json with wake confirmation
                            self._update_status_file(agent_id, status_file, ts)
                            
                            # Check for wake confirmation
                            if self._check_wake_confirmation(agent_id, resp_file):
                                self.wake_confirmations[agent_id] = True
                                logger.info(f"{agent_id} confirmed wake command")
                            
                        # Check timeout
                        last = self.last_seen.get(agent_id, 0)
                        if time.time() - last > self.timeout:
                            self._alert_unresponsive(agent_id, time.time() - last)
                            
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"Error in watch loop: {e}")
                time.sleep(self.interval)  # Continue monitoring despite errors
                
    def _check_wake_confirmation(self, agent_id: str, resp_file: Path) -> bool:
        """Check if agent has confirmed wake command."""
        try:
            if resp_file.exists():
                with open(resp_file, 'r') as f:
                    response = json.load(f)
                message = response.get('message', '').lower()
                return any(phrase in message for phrase in [
                    'wake command received',
                    'wake confirmed',
                    'status confirmed',
                    'ready to proceed',
                    'capabilities confirmed'
                ])
        except Exception as e:
            logger.error(f"Failed to check wake confirmation for {agent_id}: {e}")
        return False
                
    def _update_status_file(self, agent_id: str, status_file: Path, timestamp: float):
        """Update agent's status.json file."""
        try:
            status_data = {
                "agent_id": agent_id,
                "last_seen": datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
                "status": "active",
                "last_update": datetime.now(timezone.utc).isoformat(),
                "wake_confirmed": self.wake_confirmations.get(agent_id, False),
                "metrics": {
                    "response_time": timestamp,
                    "is_responsive": True
                }
            }
            
            # Create directory if it doesn't exist
            status_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write status file
            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
                
            logger.debug(f"Updated status file for {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to update status file for {agent_id}: {e}")
                
    def _record_metrics(self, agent_id: str, timestamp: float):
        """Record metrics for an agent's response."""
        metrics_file = self.metrics_dir / f"{agent_id}_metrics.json"
        
        try:
            # Load existing metrics
            if metrics_file.exists():
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
            else:
                metrics = {
                    "response_times": [],
                    "last_updated": None,
                    "total_responses": 0,
                    "wake_confirmations": 0
                }
                
            # Update metrics
            metrics["response_times"].append(timestamp)
            metrics["last_updated"] = datetime.now(timezone.utc).isoformat()
            metrics["total_responses"] += 1
            if self.wake_confirmations.get(agent_id, False):
                metrics["wake_confirmations"] += 1
            
            # Keep only last 1000 response times
            metrics["response_times"] = metrics["response_times"][-1000:]
            
            # Save updated metrics
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to record metrics for {agent_id}: {e}")
            
    def _alert_unresponsive(self, agent_id: str, delay: float):
        """Generate an alert for an unresponsive agent."""
        alert_path = self.alert_dir / f"{agent_id}.json"
        
        try:
            payload = {
                "agent": agent_id,
                "delay_seconds": int(delay),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "last_seen": datetime.fromtimestamp(self.last_seen.get(agent_id, 0), timezone.utc).isoformat(),
                "wake_confirmed": self.wake_confirmations.get(agent_id, False)
            }
            
            with open(alert_path, 'w') as f:
                json.dump(payload, f, indent=2)
                
            logger.warning(f"{agent_id} unresponsive for {int(delay)}s; alert written.")
            
            # Update status file to reflect unresponsive state
            status_file = self.status_dir / agent_id / "status.json"
            if status_file.exists():
                with open(status_file, 'r') as f:
                    status_data = json.load(f)
                status_data["status"] = "unresponsive"
                status_data["last_update"] = datetime.now(timezone.utc).isoformat()
                status_data["metrics"]["is_responsive"] = False
                with open(status_file, 'w') as f:
                    json.dump(status_data, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to write alert for {agent_id}: {e}")
            
    def get_agent_status(self, agent_id: str) -> Optional[Dict]:
        """Get current status for an agent."""
        try:
            last = self.last_seen.get(agent_id, 0)
            delay = time.time() - last
            
            return {
                "agent": agent_id,
                "last_seen": datetime.fromtimestamp(last, timezone.utc).isoformat(),
                "delay_seconds": int(delay),
                "is_responsive": delay <= self.timeout,
                "wake_confirmed": self.wake_confirmations.get(agent_id, False)
            }
            
        except Exception as e:
            logger.error(f"Failed to get status for {agent_id}: {e}")
            return None

if __name__ == "__main__":
    mon = AgentMonitor(check_interval=30, timeout=150)
    mon.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        mon.stop()
        logger.info("AgentMonitor stopped.") 