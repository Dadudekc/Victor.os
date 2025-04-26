# Event Bus & Acknowledgment Protocol Stub
import threading
import uuid
import time
from collections import defaultdict

class EventBus:
    """Lightweight in-memory pub/sub broker with ack support."""
    def __init__(self):
        self.topics = defaultdict(list)  # topic -> list of subscribers
        self.lock = threading.Lock()

    def subscribe(self, topic: str, callback):
        """Subscribe a callback to a topic."""
        with self.lock:
            self.topics[topic].append(callback)

    def publish(self, topic: str, payload: dict, ack_required: bool = False, timeout: float = 5.0):
        """Publish a message to a topic, optionally waiting for ACKs."""
        message = {
            "id": str(uuid.uuid4()),
            "type": topic,
            "payload": payload,
            "timestamp": time.time(),
            "ack_required": ack_required,
        }
        # Dispatch
        with self.lock:
            subscribers = list(self.topics.get(topic, []))
        acks = []
        for cb in subscribers:
            try:
                result = cb(message)
                if ack_required and result is True:
                    acks.append(message["id"])
            except Exception:
                continue
        # Simple ack logic
        if ack_required:
            start = time.time()
            while time.time() - start < timeout:
                if len(acks) >= len(subscribers):
                    return True
                time.sleep(0.1)
            return False
        return True 
