import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Import the adapter
from dreamos.core.db.sqlite_adapter import (  # Assuming Task type is defined
    SQLiteAdapter,
    Task,
)

logger = logging.getLogger(__name__)


class AgentRegistryHandler:
    """Handles agent heartbeat recording and stale task reclamation using SQLiteAdapter."""

    # --- Init with Adapter --- #
    def __init__(self, adapter: SQLiteAdapter, heartbeat_ttl: int):
        self.adapter = adapter
        self.heartbeat_ttl = heartbeat_ttl
        self.agents: Dict[str, float] = {}  # In-memory cache for heartbeats

        logger.info(f"AgentRegistryHandler initialized (TTL: {self.heartbeat_ttl}s)")
        # Load initial cache
        asyncio.run(self._load_agents_from_db())  # Run async loader in sync context

    # --- Load from DB --- #
    async def _load_agents_from_db(self) -> None:
        """Loads agent heartbeats from the database into the in-memory cache."""
        logger.debug("Loading agent heartbeats from database...")
        try:
            # Use adapter method (assuming it's synchronous for simplicity here,
            # otherwise need to handle async properly)
            # If adapter methods become async, this needs adjustment.
            self.agents = self.adapter.get_all_agents()
            logger.info(f"Loaded {len(self.agents)} agent heartbeats into cache.")
        except Exception as e:
            logger.error(f"Failed to load agents from DB: {e}", exc_info=True)
            # Keep potentially stale cache

    # --- Heartbeat Methods --- #
    async def record_heartbeat(
        self, agent_name: str, timestamp: Optional[float] = None
    ) -> bool:
        """Record or update the heartbeat timestamp for the given agent via adapter."""
        if timestamp is None:
            timestamp = time.time()
        try:
            # 1. Update Database via Adapter
            # Assuming adapter method is sync for now
            self.adapter.update_agent_heartbeat(agent_name, timestamp)

            # 2. Update In-Memory Cache
            self.agents[agent_name] = timestamp
            logger.debug(f"Recorded heartbeat for {agent_name} (DB & Cache)")
            return True
        except Exception as e:
            logger.error(
                f"Failed to record heartbeat for {agent_name}: {e}", exc_info=True
            )
            return False

    async def get_all_registered_agents(
        self, force_reload: bool = False
    ) -> Dict[str, float]:
        """Return a dict of agent names to last heartbeat timestamps (purges stale from cache)."""
        if force_reload or not self.agents:
            await self._load_agents_from_db()

        # Filter cached agents based on TTL
        current_time = time.time()
        active_agents = {
            agent: ts
            for agent, ts in self.agents.items()
            if current_time - ts <= self.heartbeat_ttl
        }
        if len(active_agents) < len(self.agents):
            stale_count = len(self.agents) - len(active_agents)
            logger.debug(
                f"Returning {len(active_agents)} active agents (filtered {stale_count} stale from cache by TTL)."
            )
        return active_agents

    # --- Task Reclamation --- #
    async def reclaim_stale_tasks(self) -> List[Task]:  # Return reclaimed Task objects
        """Finds tasks assigned to stale agents and resets them to 'pending'."""
        reclaimed_tasks_info = []
        try:
            # 1. Get stale agent IDs from the adapter
            stale_agent_ids = self.adapter.get_stale_agents(self.heartbeat_ttl)
            if not stale_agent_ids:
                logger.debug("No stale agents found, no tasks to reclaim.")
                return []

            logger.info(
                f"Found stale agents: {stale_agent_ids}. Checking for assigned tasks..."
            )

            # 2. Find tasks assigned to these agents with 'claimed' or 'in_progress' status
            # Requires a new adapter method or combination of existing ones.
            # Let's assume a new method `get_tasks_by_agents_and_status` exists.
            stale_tasks: List[Task] = self.adapter.get_tasks_by_agents_and_status(
                stale_agent_ids, ["claimed", "in_progress"]
            )

            if not stale_tasks:
                logger.info("No active tasks found assigned to stale agents.")
                return []

            logger.warning(
                f"Found {len(stale_tasks)} tasks assigned to stale agents. Attempting reclamation..."
            )

            now_iso = datetime.now(timezone.utc).isoformat()
            reclaimed_count = 0
            failed_count = 0

            # 3. Update each stale task via the adapter (ideally in a transaction if possible)
            for task in stale_tasks:
                task_id = task.get("task_id")
                if not task_id:
                    continue

                updates = {
                    "status": "pending",
                    "agent_id": None,  # Unassign
                    "updated_at": now_iso,
                    # Optionally add a note to payload or summary?
                    # "result_summary": f"Reclaimed due to agent {task.get('agent_id')} staleness."
                }
                try:
                    # Assuming update_task handles the transaction and status logging
                    self.adapter.update_task(task_id, updates)
                    reclaimed_tasks_info.append(
                        {"task_id": task_id, "previous_agent": task.get("agent_id")}
                    )  # Store info about reclaimed tasks
                    reclaimed_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to reclaim task {task_id}: {e}", exc_info=True
                    )
                    failed_count += 1

            if reclaimed_count > 0:
                logger.info(f"Successfully reclaimed {reclaimed_count} tasks.")
            if failed_count > 0:
                logger.error(f"Failed to reclaim {failed_count} tasks.")

        except Exception as e:
            logger.error(
                f"Error during stale task reclamation process: {e}", exc_info=True
            )

        # Return info about tasks that were reclaimed
        return reclaimed_tasks_info  # Or return full Task objects if needed
