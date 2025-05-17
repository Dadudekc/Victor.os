"""
Monitors swarm health, operational cycles, and triggers Captain elections.

Reads from: runtime/state/agent_metrics.json
Publishes: ELECTION_START event to AgentBus
"""

from __future__ import annotations
import asyncio
import json
import logging
import time # For monotonic time, not to be confused with datetime for timestamps
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from .agent_bus import AgentBus
from .event_types import EventType

logger = logging.getLogger(__name__)

# Configuration for SystemMonitorAgent (could be externalized)
class SystemMonitorConfig:
    AGENT_ID = "SystemMonitorAgent"
    AGENT_METRICS_FILE = Path("runtime/state/agent_metrics.json")
    OPERATIONAL_CYCLE_HOURS = 24
    OPERATIONAL_CYCLE_TASKS = 300  # Swarm-wide tasks completed in a cycle
    ELECTION_TRIGGER_CYCLES = 4    # Elections occur every N operational cycles
    MONITOR_LOOP_INTERVAL_S = 60   # How often to check for cycle completion

    # Eligibility Criteria v1 (as per user spec)
    CANDIDACY_REQ_TASKS = 5
    CANDIDACY_REQ_CYCLES_HISTORY = 2 # Tasks from the last N cycles
    VOTING_REQ_UPTIME_MINS_CURRENT_CYCLE = 60

class SystemMonitorAgent:
    def __init__(self, bus: AgentBus, config: SystemMonitorConfig = SystemMonitorConfig()) -> None:
        self.agent_id = config.AGENT_ID
        self.bus = bus
        self.config = config
        self.metrics: Dict[str, Any] = {}
        self._loop_task: Optional[asyncio.Task] = None
        self._ensure_metrics_file_exists()

    def _ensure_metrics_file_exists(self) -> None:
        """Ensures the metrics file exists or initializes it."""
        if not self.config.AGENT_METRICS_FILE.exists():
            logger.warning(
                f"Metrics file {self.config.AGENT_METRICS_FILE} not found. Initializing."
            )
            self._initialize_metrics_structure()
            self._save_metrics()
        else:
            self._load_metrics() # Load existing metrics if file is present
            # Ensure essential keys are present even if file existed but was minimal
            if "swarm" not in self.metrics or not isinstance(self.metrics.get("swarm"), dict):
                 self.metrics["swarm"] = {}
            if "cycle_count" not in self.metrics["swarm"]:
                self.metrics["swarm"]["cycle_count"] = 0
            if "last_cycle_timestamp" not in self.metrics["swarm"]:
                self.metrics["swarm"]["last_cycle_timestamp"] = (datetime.now(timezone.utc) - timedelta(hours=self.config.OPERATIONAL_CYCLE_HOURS + 1)).isoformat()
            if "tasks_at_last_cycle_end" not in self.metrics["swarm"]:
                 self.metrics["swarm"]["tasks_at_last_cycle_end"] = self.metrics["swarm"].get("total_tasks_completed", 0)
            if "per_cycle_agent_metrics" not in self.metrics["swarm"]:
                self.metrics["swarm"]["per_cycle_agent_metrics"] = {} # cycle_num_str: {agent_id: {metrics}}

    def _initialize_metrics_structure(self) -> None:
        """Sets up the basic structure for a new metrics file."""
        self.metrics = {
            "swarm": {
                "total_tasks_completed": 0, # Cumulative across all time
                "cycle_count": 0,
                "last_cycle_timestamp": (datetime.now(timezone.utc) - timedelta(hours=self.config.OPERATIONAL_CYCLE_HOURS + 1)).isoformat(),
                "tasks_at_last_cycle_end": 0, # total_tasks_completed at the end of the previous cycle
                "per_cycle_agent_metrics": {} # Stores {cycle_num_str: {agent_id: {tasks_completed_in_cycle, uptime_minutes_in_cycle}}}
            }
            # Agent-specific cumulative data (Agent-ID: {tasks_completed, uptime_minutes, last_active})
            # will be added by agents themselves or a dedicated metrics collector.
        }

    def _load_metrics(self) -> None:
        try:
            if self.config.AGENT_METRICS_FILE.exists():
                with self.config.AGENT_METRICS_FILE.open("r", encoding="utf-8") as f:
                    self.metrics = json.load(f)
                logger.debug(f"Metrics loaded from {self.config.AGENT_METRICS_FILE}")
            else:
                self._initialize_metrics_structure()
        except json.JSONDecodeError:
            logger.exception(f"Invalid JSON in {self.config.AGENT_METRICS_FILE}. Re-initializing.")
            self._initialize_metrics_structure()
        except IOError:
            logger.exception(f"Could not read {self.config.AGENT_METRICS_FILE}. Re-initializing.")
            self._initialize_metrics_structure()

    def _save_metrics(self) -> None:
        try:
            self.config.AGENT_METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with self.config.AGENT_METRICS_FILE.open("w", encoding="utf-8") as f:
                json.dump(self.metrics, f, indent=2)
            logger.debug(f"Metrics saved to {self.config.AGENT_METRICS_FILE}")
        except IOError:
            logger.exception(f"Could not save metrics to {self.config.AGENT_METRICS_FILE}")

    async def start_monitoring(self) -> None:
        if self._loop_task and not self._loop_task.done():
            logger.warning(f"{self.agent_id} monitoring loop already running.")
            return
        self._ensure_metrics_file_exists() # Ensure metrics are loaded/initialized before loop
        self._loop_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"{self.agent_id} monitoring services started.")

    async def stop_monitoring(self) -> None:
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                logger.info(f"{self.agent_id} monitoring loop cancelled.")
        self._loop_task = None
        logger.info(f"{self.agent_id} monitoring services stopped.")

    def _check_operational_cycle_completion(self) -> bool:
        self._load_metrics() # Refresh metrics from file
        swarm_metrics = self.metrics.get("swarm", {})

        last_cycle_ts_str = swarm_metrics.get("last_cycle_timestamp", (datetime.now(timezone.utc) - timedelta(hours=self.config.OPERATIONAL_CYCLE_HOURS + 1)).isoformat())
        last_cycle_dt = datetime.fromisoformat(last_cycle_ts_str)
        time_since_last_cycle_hr = (datetime.now(timezone.utc) - last_cycle_dt).total_seconds() / 3600

        current_total_swarm_tasks = swarm_metrics.get("total_tasks_completed", 0)
        tasks_at_last_cycle_end = swarm_metrics.get("tasks_at_last_cycle_end", 0)
        tasks_this_cycle = current_total_swarm_tasks - tasks_at_last_cycle_end

        time_triggered = time_since_last_cycle_hr >= self.config.OPERATIONAL_CYCLE_HOURS
        task_triggered = tasks_this_cycle >= self.config.OPERATIONAL_CYCLE_TASKS

        if time_triggered or task_triggered:
            reason = "time" if time_triggered else "tasks"
            logger.info(
                f"Operational cycle {swarm_metrics.get('cycle_count', 0) + 1} ended. "
                f"Trigger: {reason} ({time_since_last_cycle_hr=:.2f}hrs, {tasks_this_cycle=})."
            )
            return True
        return False

    def _finalize_current_cycle_metrics(self, current_cycle_num: int) -> None:
        """Calculates and stores agent metrics for the just-ended cycle."""
        # This requires agents to report their *cumulative* metrics to agent_metrics.json
        # This method then calculates the delta for the completed cycle.
        # Example: { "Agent-1": {"tasks_completed": 100, "uptime_minutes": 1200}}
        # If previous cycle stored "tasks_completed_cumulative": 80, then this cycle had 20.
        # This method needs more robust historical data access or snapshots.

        cycle_metrics_key = str(current_cycle_num)
        self.metrics["swarm"].setdefault("per_cycle_agent_metrics", {})[cycle_metrics_key] = {}
        
        previous_cycle_key = str(current_cycle_num - 1)
        prev_cycle_data = self.metrics["swarm"].get("per_cycle_agent_metrics", {}).get(previous_cycle_key, {})

        for agent_id, data in self.metrics.items():
            if agent_id == "swarm":
                continue
            
            cumulative_tasks = data.get("tasks_completed", 0)
            cumulative_uptime = data.get("uptime_minutes", 0)
            
            # Get cumulative metrics *at the end of the previous cycle* for this agent
            prev_agent_metrics_snapshot = prev_cycle_data.get(agent_id, {})
            prev_cumulative_tasks = prev_agent_metrics_snapshot.get("cumulative_tasks_at_cycle_end", 0)
            prev_cumulative_uptime = prev_agent_metrics_snapshot.get("cumulative_uptime_at_cycle_end", 0)

            tasks_in_this_cycle = cumulative_tasks - prev_cumulative_tasks
            uptime_in_this_cycle = cumulative_uptime - prev_cumulative_uptime
            
            agent_cycle_summary = {
                "tasks_completed_in_cycle": tasks_in_this_cycle,
                "uptime_minutes_in_cycle": uptime_in_this_cycle,
                "cumulative_tasks_at_cycle_end": cumulative_tasks, # Snapshot for next cycle
                "cumulative_uptime_at_cycle_end": cumulative_uptime # Snapshot for next cycle
            }
            self.metrics["swarm"]["per_cycle_agent_metrics"][cycle_metrics_key][agent_id] = agent_cycle_summary
        logger.info(f"Finalized and stored agent metrics for cycle {current_cycle_num}.")

    def _start_new_operational_cycle(self) -> None:
        self._load_metrics()
        current_cycle = self.metrics["swarm"].get("cycle_count", 0)
        self._finalize_current_cycle_metrics(current_cycle) # Finalize metrics for the cycle that just ended

        self.metrics["swarm"]["cycle_count"] = current_cycle + 1
        self.metrics["swarm"]["last_cycle_timestamp"] = datetime.now(timezone.utc).isoformat()
        self.metrics["swarm"]["tasks_at_last_cycle_end"] = self.metrics["swarm"].get("total_tasks_completed", 0)
        self._save_metrics()
        logger.info(f"New operational cycle {self.metrics['swarm']['cycle_count']} started.")

    def _get_eligible_agents(self) -> Dict[str, List[str]]:
        self._load_metrics()
        eligible_for_candidacy: List[str] = []
        eligible_to_vote: List[str] = []
        current_cycle_num = self.metrics["swarm"].get("cycle_count", 0)
        per_cycle_metrics = self.metrics["swarm"].get("per_cycle_agent_metrics", {})

        all_agent_ids = [aid for aid in self.metrics if aid != "swarm"]

        for agent_id in all_agent_ids:
            # Candidacy: ≥ X tasks in past Y cycles
            tasks_in_relevant_cycles = 0
            for i in range(self.config.CANDIDACY_REQ_CYCLES_HISTORY):
                cycle_to_check_num = current_cycle_num - i
                agent_metrics_for_cycle = per_cycle_metrics.get(str(cycle_to_check_num), {}).get(agent_id, {})
                tasks_in_relevant_cycles += agent_metrics_for_cycle.get("tasks_completed_in_cycle", 0)
            
            if tasks_in_relevant_cycles >= self.config.CANDIDACY_REQ_TASKS:
                eligible_for_candidacy.append(agent_id)

            # Voting: ≥ X uptime in current (just ended) cycle
            # The "current cycle" for voting eligibility is the one that just completed.
            current_cycle_agent_metrics = per_cycle_metrics.get(str(current_cycle_num), {}).get(agent_id, {})
            uptime_this_cycle = current_cycle_agent_metrics.get("uptime_minutes_in_cycle", 0)
            if uptime_this_cycle >= self.config.VOTING_REQ_UPTIME_MINS_CURRENT_CYCLE:
                eligible_to_vote.append(agent_id)

        logger.info(f"Eligibility: Candidates ({len(eligible_for_candidacy)}): {eligible_for_candidacy}")
        logger.info(f"Eligibility: Voters ({len(eligible_to_vote)}): {eligible_to_vote}")
        return {"candidates": eligible_for_candidacy, "voters": eligible_to_vote}

    async def _trigger_election(self) -> None:
        logger.info("Election trigger cycle reached. Determining eligibility...")
        eligibility = self._get_eligible_agents()
        await self.bus.publish(EventType.ELECTION_START, {
            "cycle_count": self.metrics["swarm"].get("cycle_count", 0),
            "eligible_candidates": eligibility["candidates"],
            "eligible_voters": eligibility["voters"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        logger.info("ELECTION_START event published.")

    async def _monitor_loop(self) -> None:
        logger.info(f"{self.agent_id} main loop running. Interval: {self.config.MONITOR_LOOP_INTERVAL_S}s")
        while True:
            try:
                if self._check_operational_cycle_completion():
                    self._start_new_operational_cycle()
                    if self.metrics["swarm"].get("cycle_count", 0) % self.config.ELECTION_TRIGGER_CYCLES == 0:
                        await self._trigger_election()
                await asyncio.sleep(self.config.MONITOR_LOOP_INTERVAL_S)
            except asyncio.CancelledError:
                logger.info(f"{self.agent_id} monitor loop cancelled.")
                break
            except Exception:
                logger.exception("Error in monitor loop. Retrying after delay.")
                await asyncio.sleep(self.config.MONITOR_LOOP_INTERVAL_S * 2)

# Example usage for standalone testing
async def main_sma_test():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(name)s: %(message)s")
    
    # Ensure runtime directories exist for test
    Path("runtime/state").mkdir(parents=True, exist_ok=True)
    Path("runtime/bus/events").mkdir(parents=True, exist_ok=True)

    # Create a dummy metrics file for testing SystemMonitorAgent initialization
    # and per-cycle logic
    dummy_metrics = {
        "swarm": {
            "total_tasks_completed": 50,
            "cycle_count": 2, # Start at cycle 2 to test eligibility over past cycles
            "last_cycle_timestamp": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "tasks_at_last_cycle_end": 30,
            "per_cycle_agent_metrics": {
                "1": { # Metrics for cycle 1
                    "Agent-Alpha": {"tasks_completed_in_cycle": 10, "uptime_minutes_in_cycle": 100, "cumulative_tasks_at_cycle_end": 10, "cumulative_uptime_at_cycle_end": 100},
                    "Agent-Beta": {"tasks_completed_in_cycle": 8, "uptime_minutes_in_cycle": 120, "cumulative_tasks_at_cycle_end": 8, "cumulative_uptime_at_cycle_end": 120}
                },
                "2": { # Metrics for cycle 2
                    "Agent-Alpha": {"tasks_completed_in_cycle": 12, "uptime_minutes_in_cycle": 90, "cumulative_tasks_at_cycle_end": 22, "cumulative_uptime_at_cycle_end": 190},
                    "Agent-Beta": {"tasks_completed_in_cycle": 7, "uptime_minutes_in_cycle": 30, "cumulative_tasks_at_cycle_end": 15, "cumulative_uptime_at_cycle_end": 150}
                }
            }
        },
        "Agent-Alpha": {"tasks_completed": 22, "uptime_minutes": 190, "last_active": datetime.now(timezone.utc).isoformat()},
        "Agent-Beta": {"tasks_completed": 15, "uptime_minutes": 150, "last_active": datetime.now(timezone.utc).isoformat()},
        "Agent-Charlie": {"tasks_completed": 2, "uptime_minutes": 200, "last_active": datetime.now(timezone.utc).isoformat()}
    }
    with open(SystemMonitorConfig.AGENT_METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(dummy_metrics, f, indent=2)

    bus = AgentBus()
    config = SystemMonitorConfig()
    # Test with shorter cycles for faster demo if needed
    # config.OPERATIONAL_CYCLE_HOURS = 0.01 # e.g., ~36 seconds
    # config.OPERATIONAL_CYCLE_TASKS = 5
    # config.MONITOR_LOOP_INTERVAL_S = 5
    # config.ELECTION_TRIGGER_CYCLES = 1 # Trigger election on next cycle for testing

    sma = SystemMonitorAgent(bus=bus, config=config)
    
    print(f"SMA Test: Starting SystemMonitorAgent. Current cycle from file: {sma.metrics.get('swarm',{}).get('cycle_count')}")
    print(f"SMA Test: Election will trigger if current cycle + 1 is a multiple of {config.ELECTION_TRIGGER_CYCLES}.") 
    print(f"SMA Test: CANDIDACY_REQ_TASKS={config.CANDIDACY_REQ_TASKS}, CANDIDACY_REQ_CYCLES_HISTORY={config.CANDIDACY_REQ_CYCLES_HISTORY}")
    print(f"SMA Test: VOTING_REQ_UPTIME_MINS_CURRENT_CYCLE={config.VOTING_REQ_UPTIME_MINS_CURRENT_CYCLE}")

    try:
        await sma.start_monitoring()
        # Let it run for a bit to see a cycle or two (adjust based on test cycle length)
        await asyncio.sleep(120) # Adjust as needed for testing
    except KeyboardInterrupt:
        print("SMA Test: Keyboard interrupt received.")
    finally:
        print("SMA Test: Stopping SystemMonitorAgent...")
        await sma.stop_monitoring()
        print("SMA Test: SystemMonitorAgent stopped.")

if __name__ == "__main__":
    asyncio.run(main_sma_test()) 