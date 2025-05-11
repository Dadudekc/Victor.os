"""
Bridge Expansion System
Enhanced agent communication bridge with pub/sub patterns and real-time state sync.

Features:
- Pub/Sub event system
- Real-time state synchronization
- Event streaming
- Message queuing
- Health monitoring
- Error handling
"""

import json
import logging
import queue
import signal
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("runtime/logs/bridge_expansion.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class BridgeExpansion:
    def __init__(self):
        self.state_file = Path("runtime/state/bridge_state.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.event_queue = queue.Queue()
        self.subscribers = defaultdict(list)
        self.is_running = False
        self.state = self._load_state()
        self.message_history = []
        self.max_history = 1000

    def _load_state(self) -> Dict:
        """Load bridge state from persistent storage."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
        return {
            "last_sync": None,
            "connected_agents": [],
            "message_count": 0,
            "error_count": 0,
            "health_metrics": {},
        }

    def _save_state(self):
        """Persist current state to storage."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def subscribe(self, topic: str, callback: Callable):
        """Subscribe to a topic with a callback function."""
        self.subscribers[topic].append(callback)
        logger.info(f"New subscription to topic: {topic}")

    def unsubscribe(self, topic: str, callback: Callable):
        """Unsubscribe from a topic."""
        if topic in self.subscribers and callback in self.subscribers[topic]:
            self.subscribers[topic].remove(callback)
            logger.info(f"Unsubscribed from topic: {topic}")

    def publish(self, topic: str, message: Dict):
        """Publish a message to a topic."""
        try:
            # Add metadata
            message["timestamp"] = datetime.utcnow().isoformat()
            message["topic"] = topic

            # Store in history
            self.message_history.append(message)
            if len(self.message_history) > self.max_history:
                self.message_history.pop(0)

            # Update state
            self.state["message_count"] += 1
            self._save_state()

            # Notify subscribers
            for callback in self.subscribers[topic]:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Error in subscriber callback: {e}")

            logger.info(f"Published message to {topic}")
            return True

        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            self.state["error_count"] += 1
            self._save_state()
            return False

    def sync_state(self, agent_id: str, state: Dict):
        """Synchronize state with an agent."""
        try:
            # Update agent state
            self.state["connected_agents"].append(agent_id)
            self.state["last_sync"] = datetime.utcnow().isoformat()

            # Merge states
            self.state.update(state)
            self._save_state()

            # Notify subscribers
            self.publish("state_sync", {"agent_id": agent_id, "state": state})

            logger.info(f"State synchronized with {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Error syncing state: {e}")
            return False

    def get_message_history(
        self, topic: Optional[str] = None, limit: int = 100
    ) -> List[Dict]:
        """Get message history, optionally filtered by topic."""
        if topic:
            return [msg for msg in self.message_history if msg["topic"] == topic][
                -limit:
            ]
        return self.message_history[-limit:]

    def monitor_health(self):
        """Monitor bridge health metrics."""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "connected_agents": len(self.state["connected_agents"]),
            "message_count": self.state["message_count"],
            "error_count": self.state["error_count"],
            "subscriber_count": sum(len(subs) for subs in self.subscribers.values()),
            "queue_size": self.event_queue.qsize(),
        }
        self.state["health_metrics"] = metrics
        self._save_state()
        return metrics

    def process_events(self):
        """Process pending events in the queue."""
        while not self.event_queue.empty():
            try:
                event = self.event_queue.get_nowait()
                self._handle_event(event)
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    def _handle_event(self, event: Dict):
        """Handle a single event."""
        event_type = event.get("type")
        if event_type == "MESSAGE":
            self._handle_message_event(event)
        elif event_type == "STATE_SYNC":
            self._handle_state_sync_event(event)
        elif event_type == "ERROR":
            self._handle_error_event(event)
        else:
            logger.warning(f"Unknown event type: {event_type}")

    def _handle_message_event(self, event: Dict):
        """Handle message event."""
        topic = event.get("topic")
        message = event.get("message")
        if topic and message:
            self.publish(topic, message)

    def _handle_state_sync_event(self, event: Dict):
        """Handle state sync event."""
        agent_id = event.get("agent_id")
        state = event.get("state")
        if agent_id and state:
            self.sync_state(agent_id, state)

    def _handle_error_event(self, event: Dict):
        """Handle error event."""
        error = event.get("error")
        logger.error(f"Error event received: {error}")
        self.state["error_count"] += 1
        self._save_state()

    def start(self):
        """Start the bridge expansion system."""
        logger.info("Starting Bridge Expansion System")
        self.is_running = True

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        try:
            while self.is_running:
                # Process events
                self.process_events()

                # Monitor health
                self.monitor_health()

                # Sleep briefly
                time.sleep(1)

        except Exception as e:
            logger.error(f"Fatal error in bridge: {e}")
            self._handle_shutdown(signal.SIGTERM, None)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received shutdown signal {signum}")
        self.is_running = False
        self._save_state()
        sys.exit(0)


if __name__ == "__main__":
    bridge = BridgeExpansion()
    bridge.start()
