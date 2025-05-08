import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Import the adapter
from dreamos.core.db.sqlite_adapter import (
    SQLiteAdapter,
    Task, # This Task type might need reconciliation with other Task definitions
)

logger = logging.getLogger(__name__)


class AgentRegistryHandler:
    """Handles agent heartbeat recording and stale task reclamation using SQLiteAdapter."""

    def __init__(self, adapter: SQLiteAdapter, heartbeat_ttl: int):
        self.adapter = adapter
        self.heartbeat_ttl = heartbeat_ttl
        self.agents: Dict[str, float] = {}  # In-memory cache for heartbeats
        self._initialized = False
        # Initialization is now deferred to the async initialize() method

    async def initialize(self):
        """Asynchronously initializes the handler by loading agent heartbeats from DB."""
        if self._initialized:
            return
        # This lock is to prevent concurrent initializations if `initialize` is called multiple times.
        # A more robust singleton pattern for the class itself might be considered if needed.
        async with getattr(self, '_init_lock', asyncio.Lock()): # Lazily create lock if needed
            if not hasattr(self, '_init_lock'): self._init_lock = asyncio.Lock()
            if self._initialized:
                return
            await self._load_agents_from_db()
            logger.info(f"AgentRegistryHandler initialized (TTL: {self.heartbeat_ttl}s)")
            self._initialized = True

    async def _load_agents_from_db(self) -> None:
        """Loads agent heartbeats from the database into the in-memory cache."""
        logger.debug("Loading agent heartbeats from database...")
        try:
            self.agents = self.adapter.get_all_agents() # Assumes adapter method is sync
            logger.info(f"Loaded {len(self.agents)} agent heartbeats into cache.")
        except Exception as e:
            logger.error(f"Failed to load agents from DB: {e}", exc_info=True)

    async def record_heartbeat(
        self, agent_name: str, timestamp: Optional[float] = None
    ) -> bool:
        """Record or update the heartbeat timestamp for the given agent via adapter."""
        if not self._initialized:
            logger.error("AgentRegistryHandler not initialized. Call await initialize() first.")
            return False
        if timestamp is None:
            timestamp = time.time()
        try:
            self.adapter.update_agent_heartbeat(agent_name, timestamp) # Assumes adapter method is sync
            self.agents[agent_name] = timestamp
            logger.debug(f"Recorded heartbeat for {agent_name} (DB & Cache)")
            return True
        except Exception as e:
            logger.error(f"Failed to record heartbeat for {agent_name}: {e}", exc_info=True)
            return False

    async def get_all_registered_agents(
        self, force_reload: bool = False
    ) -> Dict[str, float]:
        """Return a dict of agent names to last heartbeat timestamps (purges stale from cache)."""
        if not self._initialized:
            logger.error("AgentRegistryHandler not initialized. Call await initialize() first.")
            return {}
        if force_reload or not self.agents:
            await self._load_agents_from_db()
        current_time = time.time()
        active_agents = {
            agent: ts
            for agent, ts in self.agents.items()
            if current_time - ts <= self.heartbeat_ttl
        }
        if len(active_agents) < len(self.agents):
            stale_count = len(self.agents) - len(active_agents)
            logger.debug(f"Returning {len(active_agents)} active agents (filtered {stale_count} stale from cache by TTL)." )
        return active_agents

    async def reclaim_stale_tasks(self) -> List[Dict[str, Optional[str]]]: # Updated return type hint
        """Finds tasks assigned to stale agents and resets them to 'pending'.
        Returns a list of dicts with info about reclaimed tasks (task_id, previous_agent).
        """
        if not self._initialized:
            logger.error("AgentRegistryHandler not initialized. Call await initialize() first.")
            return []
        reclaimed_tasks_info: List[Dict[str, Optional[str]]] = []
        try:
            stale_agent_ids = self.adapter.get_stale_agents(self.heartbeat_ttl)
            if not stale_agent_ids:
                logger.debug("No stale agents found, no tasks to reclaim.")
                return []
            logger.info(f"Found stale agents: {stale_agent_ids}. Checking for assigned tasks...")
            stale_tasks: List[Task] = self.adapter.get_tasks_by_agents_and_status(
                stale_agent_ids, ["claimed", "in_progress"]
            )
            if not stale_tasks:
                logger.info("No active tasks found assigned to stale agents.")
                return []
            logger.warning(f"Found {len(stale_tasks)} tasks assigned to stale agents. Attempting reclamation...")
            now_iso = datetime.now(timezone.utc).isoformat()
            reclaimed_count = 0
            failed_count = 0
            for task in stale_tasks:
                task_id = task.get("task_id") # type: ignore
                if not task_id:
                    continue
                updates = {
                    "status": "pending",
                    "agent_id": None,
                    "updated_at": now_iso,
                }
                try:
                    self.adapter.update_task(task_id, updates)
                    reclaimed_tasks_info.append(
                        {"task_id": task_id, "previous_agent": task.get("agent_id")} # type: ignore
                    )
                    reclaimed_count += 1
                except Exception as e:
                    logger.error(f"Failed to reclaim task {task_id}: {e}", exc_info=True)
                    failed_count += 1
            if reclaimed_count > 0:
                logger.info(f"Successfully reclaimed {reclaimed_count} tasks.")
            if failed_count > 0:
                logger.error(f"Failed to reclaim {failed_count} tasks.")
        except Exception as e:
            logger.error(f"Error during stale task reclamation process: {e}", exc_info=True)
        return reclaimed_tasks_info
