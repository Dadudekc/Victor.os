#!/usr/bin/env python3
"""
SupervisorOriaAgent monitors agent heartbeats and triggers recovery tasks if agents stall.
"""
import time
import threading
import logging
from coordination.agent_bus import AgentBus, Message

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AGENT_NAME = "SupervisorOria"

class SupervisorOriaAgent:
    """Agent to supervise other agents and trigger recovery when they become idle."""

    def __init__(self, agent_bus: AgentBus, heartbeat_threshold: float = 30.0, monitor_interval: float = 5.0):
        self.agent_name = AGENT_NAME
        self.bus = agent_bus
        self.heartbeat_threshold = heartbeat_threshold
        self.monitor_interval = monitor_interval
        self.last_heartbeats = {}
        self._stop_event = threading.Event()

        # Register agent and heartbeat handler
        self.bus.register_agent(self.agent_name, capabilities=["supervision"])
        self.bus.register_handler("HEARTBEAT", self.handle_heartbeat)
        # Register handler for task failures to retry
        self.bus.register_handler("TASK_FAILURE", self.handle_task_failure)
        logger.info(f"{self.agent_name} initialized with heartbeat threshold {self.heartbeat_threshold}s")

        # Start monitoring thread
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

        # Initial injection of Thea tasks into TaskNexus
        try:
            logger.info("Injecting Thea tasks into TaskNexus (stub)")
            # Send injection directive to TaskNexus via bus
            self.bus.send_message(
                sender=self.agent_name,
                recipient="TaskNexus",  # Assuming TaskNexus is listening
                message_type="INJECT_TASK",
                payload={"source": "SupervisorOria", "action": "inject_thea_tasks"}
            )
        except Exception as e:
            logger.error(f"Error during initial task injection: {e}")

    def handle_heartbeat(self, message: Message):
        payload = message.payload
        agent_id = payload.get("agent_id")
        timestamp = payload.get("timestamp")
        if agent_id and timestamp:
            self.last_heartbeats[agent_id] = timestamp
            logger.debug(f"Heartbeat received from {agent_id}: {timestamp}")

    def handle_task_failure(self, message: Message):
        """Handle failed tasks by retrying them."""
        payload = message.payload
        task_id = payload.get("task_id")
        agent_id = payload.get("agent_id")
        logger.warning(f"Task {task_id} failed on {agent_id}; retrying.")
        # Send retry directive back to the same agent or orchestrator
        self.bus.send_message(self.agent_name, agent_id, "RETRY_TASK", {"task_id": task_id})

    def _monitor_loop(self):
        while not self._stop_event.is_set():
            now = time.time()
            for agent_id, last in list(self.last_heartbeats.items()):
                if now - last > self.heartbeat_threshold:
                    logger.warning(f"Agent {agent_id} idle for {now - last:.1f}s; triggering recovery")
                    self.bus.send_message(self.agent_name, agent_id, "TRIGGER_RECOVERY", {"agent_id": agent_id})
            time.sleep(self.monitor_interval)

    def shutdown(self):
        """Stop the monitoring thread gracefully."""
        self._stop_event.set()
        self._thread.join()
        logger.info(f"{self.agent_name} shutdown complete") 