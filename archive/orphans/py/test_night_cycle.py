"""
Night Cycle Simulation Test
Tests the integration between MIDNIGHT.MISSION.RUNNER and Bridge Expansion
by simulating a full night cycle with various events and state changes.
"""

import logging
import random
import signal
import sys
import threading
import time
from datetime import datetime, timedelta

from bridge_expansion import BridgeExpansion
from midnight_runner import MidnightRunner

# Configure logging to use stderr with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler("runtime/logs/night_cycle_test.log"),
    ],
)
logger = logging.getLogger(__name__)

# Set up specific loggers for each component
runner_logger = logging.getLogger("midnight_runner")
bridge_logger = logging.getLogger("bridge_expansion")
sim_logger = logging.getLogger("simulator")


class NightCycleSimulator:
    def __init__(self):
        self.runner = MidnightRunner()
        self.bridge = BridgeExpansion()
        self.simulation_time = datetime.now()
        self.is_running = False
        self.test_agents = ["agent_alpha", "agent_beta", "agent_gamma", "agent_delta"]
        self.last_event_hours = set()  # Track which hours we've triggered events for

    def _simulate_time_progression(self):
        """Simulate time progression through a night cycle."""
        # Start at 9 PM
        self.simulation_time = self.simulation_time.replace(hour=21, minute=0)
        sim_logger.info(f"Simulation starting at {self.simulation_time}")

        # Progress through night cycle
        while self.is_running:
            # Advance time by 30 minutes
            self.simulation_time += timedelta(minutes=30)
            current_hour = self.simulation_time.hour

            # Log time progression
            sim_logger.info(f"Time progressed to {self.simulation_time}")

            # Simulate different events based on time
            if current_hour == 22 and 22 not in self.last_event_hours:  # 10 PM
                sim_logger.info("=== NIGHT CYCLE START ===")
                self._simulate_night_cycle_start()
                self.last_event_hours.add(22)
            elif current_hour == 0 and 0 not in self.last_event_hours:  # Midnight
                sim_logger.info("=== MIDNIGHT CHECKPOINT ===")
                self._simulate_midnight_events()
                self.last_event_hours.add(0)
            elif current_hour == 3 and 3 not in self.last_event_hours:  # 3 AM
                sim_logger.info("=== EARLY MORNING PHASE ===")
                self._simulate_early_morning_events()
                self.last_event_hours.add(3)
            elif current_hour == 6 and 6 not in self.last_event_hours:  # 6 AM
                sim_logger.info("=== DAY CYCLE START ===")
                self._simulate_day_cycle_start()
                self.last_event_hours.add(6)

            # Random events
            if random.random() < 0.3:  # 30% chance of random event
                self._simulate_random_event()

            time.sleep(2)  # Simulate 30 minutes in 2 seconds

    def _simulate_night_cycle_start(self):
        """Simulate events at the start of night cycle."""
        sim_logger.info("Simulating night cycle start events")

        # Publish night cycle start event
        self.bridge.publish(
            "system_events",
            {
                "type": "NIGHT_CYCLE_START",
                "timestamp": self.simulation_time.isoformat(),
                "details": "Night cycle operations commencing",
            },
        )

        # Sync agent states
        for agent in self.test_agents:
            self.bridge.sync_state(
                agent,
                {
                    "mode": "night",
                    "status": "active",
                    "last_sync": self.simulation_time.isoformat(),
                },
            )

    def _simulate_midnight_events(self):
        """Simulate events at midnight."""
        sim_logger.info("Simulating midnight events")

        # Publish midnight event
        self.bridge.publish(
            "system_events",
            {
                "type": "MIDNIGHT",
                "timestamp": self.simulation_time.isoformat(),
                "details": "Midnight checkpoint reached",
            },
        )

        # Simulate some agents going into low-power mode
        for agent in random.sample(self.test_agents, 2):
            self.bridge.publish(
                "agent_status",
                {
                    "agent_id": agent,
                    "status": "low_power",
                    "timestamp": self.simulation_time.isoformat(),
                },
            )

    def _simulate_early_morning_events(self):
        """Simulate events in early morning."""
        sim_logger.info("Simulating early morning events")

        # Publish early morning event
        self.bridge.publish(
            "system_events",
            {
                "type": "EARLY_MORNING",
                "timestamp": self.simulation_time.isoformat(),
                "details": "Early morning operations",
            },
        )

        # Simulate some agents waking up
        for agent in self.test_agents:
            if random.random() < 0.5:
                self.bridge.publish(
                    "agent_status",
                    {
                        "agent_id": agent,
                        "status": "active",
                        "timestamp": self.simulation_time.isoformat(),
                    },
                )

    def _simulate_day_cycle_start(self):
        """Simulate events at the start of day cycle."""
        sim_logger.info("Simulating day cycle start events")

        # Publish day cycle start event
        self.bridge.publish(
            "system_events",
            {
                "type": "DAY_CYCLE_START",
                "timestamp": self.simulation_time.isoformat(),
                "details": "Day cycle operations commencing",
            },
        )

        # Sync all agents to day mode
        for agent in self.test_agents:
            self.bridge.sync_state(
                agent,
                {
                    "mode": "day",
                    "status": "active",
                    "last_sync": self.simulation_time.isoformat(),
                },
            )

    def _simulate_random_event(self):
        """Simulate random events during the night cycle."""
        event_types = [
            "TASK_COMPLETE",
            "ERROR",
            "STATE_CHANGE",
            "HEALTH_CHECK",
            "RESOURCE_UPDATE",
        ]

        event_type = random.choice(event_types)
        agent = random.choice(self.test_agents)

        if event_type == "TASK_COMPLETE":
            self.bridge.publish(
                "task_events",
                {
                    "type": event_type,
                    "agent_id": agent,
                    "task_id": f"task_{random.randint(1000, 9999)}",
                    "timestamp": self.simulation_time.isoformat(),
                },
            )
        elif event_type == "ERROR":
            self.bridge.publish(
                "error_events",
                {
                    "type": event_type,
                    "agent_id": agent,
                    "error": f"Simulated error {random.randint(1, 100)}",
                    "timestamp": self.simulation_time.isoformat(),
                },
            )
        elif event_type == "STATE_CHANGE":
            self.bridge.publish(
                "state_events",
                {
                    "type": event_type,
                    "agent_id": agent,
                    "new_state": {
                        "status": random.choice(["active", "idle", "processing"]),
                        "timestamp": self.simulation_time.isoformat(),
                    },
                },
            )
        elif event_type == "HEALTH_CHECK":
            self.bridge.publish(
                "health_events",
                {
                    "type": event_type,
                    "agent_id": agent,
                    "metrics": {
                        "cpu": random.uniform(0, 100),
                        "memory": random.uniform(0, 100),
                        "timestamp": self.simulation_time.isoformat(),
                    },
                },
            )
        elif event_type == "RESOURCE_UPDATE":
            self.bridge.publish(
                "resource_events",
                {
                    "type": event_type,
                    "agent_id": agent,
                    "resources": {
                        "allocated": random.randint(1, 100),
                        "available": random.randint(1, 100),
                        "timestamp": self.simulation_time.isoformat(),
                    },
                },
            )

    def _monitor_systems(self):
        """Monitor both systems during simulation."""
        while self.is_running:
            # Check runner health
            runner_health = self.runner.monitor_health()
            runner_logger.info(f"Health metrics: {runner_health}")

            # Check bridge health
            bridge_health = self.bridge.monitor_health()
            bridge_logger.info(f"Health metrics: {bridge_health}")

            # Log system summary
            sim_logger.info("=== System Status ===")
            sim_logger.info(f"Active agents: {len(self.test_agents)}")
            sim_logger.info(f"Current time: {self.simulation_time}")
            sim_logger.info(f"Event queue size: {self.bridge.event_queue.qsize()}")

            time.sleep(5)

    def start_simulation(self):
        """Start the night cycle simulation."""
        sim_logger.info("Starting night cycle simulation")
        self.is_running = True

        # Set up signal handlers in main thread
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        # Start the runner
        runner_thread = threading.Thread(target=self.runner.start)
        runner_thread.daemon = True
        runner_thread.start()

        # Start the bridge
        bridge_thread = threading.Thread(target=self.bridge.start)
        bridge_thread.daemon = True
        bridge_thread.start()

        # Start time progression
        time_thread = threading.Thread(target=self._simulate_time_progression)
        time_thread.daemon = True
        time_thread.start()

        # Start monitoring
        monitor_thread = threading.Thread(target=self._monitor_systems)
        monitor_thread.daemon = True
        monitor_thread.start()

        try:
            # Keep main thread alive
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            sim_logger.info("Simulation interrupted by user")
            self.stop_simulation()

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        sim_logger.info(f"Received shutdown signal {signum}")
        self.stop_simulation()

    def stop_simulation(self):
        """Stop the night cycle simulation."""
        sim_logger.info("Stopping night cycle simulation")
        self.is_running = False

        # Gracefully stop components
        try:
            self.runner.is_running = False
            self.bridge.is_running = False
        except Exception as e:
            sim_logger.error(f"Error during shutdown: {e}")

        sys.exit(0)


if __name__ == "__main__":
    simulator = NightCycleSimulator()
    simulator.start_simulation()
