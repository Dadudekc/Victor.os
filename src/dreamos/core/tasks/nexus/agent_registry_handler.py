import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import filelock
from filelock import Timeout as LockAcquisitionError

logger = logging.getLogger(__name__)


class AgentRegistryHandler:
    """Handles agent heartbeat recording, registry loading/saving, and stale task reclamation."""  # noqa: E501

    def __init__(
        self,
        registry_path: Path,
        lock_timeout: int,
        heartbeat_ttl: int,
        working_tasks_path: Path,
        future_tasks_path: Path,
        working_tasks_lock_path: Path,
        future_tasks_lock_path: Path,
    ):
        self.agent_registry_path = registry_path
        self.agent_registry_lock_path = registry_path.with_suffix(
            registry_path.suffix + ".lock"
        )
        self.lock_timeout = lock_timeout
        self.heartbeat_ttl = heartbeat_ttl
        self.working_tasks_path = working_tasks_path
        self.future_tasks_path = future_tasks_path
        self.working_tasks_lock_path = working_tasks_lock_path
        self.future_tasks_lock_path = future_tasks_lock_path

        self.agents: Dict[str, float] = {}  # In-memory cache

        logger.info(
            f"AgentRegistryHandler initialized for {self.agent_registry_path} "
            f"(TTL: {self.heartbeat_ttl}s, Lock Timeout: {self.lock_timeout}s)"
        )

    async def _load_json_registry(self) -> Dict[str, float]:
        """Loads agent heartbeat registry asynchronously using its specific lock."""
        default_return = {}
        file_path = self.agent_registry_path
        lock_path = self.agent_registry_lock_path

        if not await asyncio.to_thread(file_path.exists):
            logger.warning(f"Registry file not found: {file_path}. Returning default.")
            return default_return

        try:
            async with filelock.FileLock(str(lock_path), timeout=self.lock_timeout):
                content = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
                if not content.strip():
                    logger.warning(
                        f"Registry file is empty: {file_path}. Returning default."
                    )
                    return default_return
                loaded_data = json.loads(content)
                if not isinstance(loaded_data, dict):
                    logger.error(
                        f"Registry file {file_path} did not contain a dictionary. Returning default."  # noqa: E501
                    )
                    return default_return
                # Convert timestamps to float, handle potential errors
                agents_data = {}
                for k, v in loaded_data.items():
                    try:
                        agents_data[str(k)] = float(v)
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Invalid timestamp value '{v}' for agent '{k}' in {file_path}. Skipping."  # noqa: E501
                        )
                return agents_data
        except json.JSONDecodeError:
            logger.error(
                f"Failed to decode JSON from {file_path}. Returning default.",
                exc_info=True,
            )
            return default_return
        except LockAcquisitionError:
            logger.error(
                f"Timeout loading {file_path}: Could not acquire lock {lock_path}. Returning cached."  # noqa: E501
            )
            return dict(self.agents)  # Return potentially stale cache on timeout
        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}", exc_info=True)
            return default_return

    async def _save_json(self, file_path: Path, lock_path: Path, data: List | Dict):
        """Saves data to a JSON file using a file lock."""
        temp_path = None
        try:
            async with filelock.FileLock(str(lock_path), timeout=self.lock_timeout):
                await asyncio.to_thread(
                    file_path.parent.mkdir, parents=True, exist_ok=True
                )
                temp_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
                json_string = json.dumps(data, indent=2)
                await asyncio.to_thread(
                    temp_path.write_text, json_string, encoding="utf-8"
                )
                await asyncio.to_thread(os.replace, temp_path, file_path)
                logger.debug(f"Successfully saved data to {file_path}")
                return True
        except LockAcquisitionError:
            logger.error(
                f"Timeout saving {file_path}: Could not acquire lock {lock_path}."
            )
            return False
        except Exception as e:
            if temp_path and await asyncio.to_thread(temp_path.exists):
                try:
                    await asyncio.to_thread(os.remove, temp_path)
                except OSError:
                    logger.error(
                        f"Failed to remove temp file {temp_path}", exc_info=True
                    )
            logger.error(f"Failed to save file {file_path}: {e}", exc_info=True)
            return False

    async def _load_agents(self) -> Dict[str, float]:
        """Loads agent heartbeat registry asynchronously, updating cache."""
        self.agents = await self._load_json_registry()
        return self.agents

    async def _save_agents(self) -> bool:
        """Saves the current in-memory agent registry asynchronously."""
        return await self._save_json(
            self.agent_registry_path, self.agent_registry_lock_path, self.agents
        )

    async def record_heartbeat(
        self, agent_name: str, timestamp: Optional[float] = None
    ) -> bool:
        """Record or update the heartbeat timestamp for the given agent."""
        if timestamp is None:
            timestamp = time.time()
        try:
            async with filelock.FileLock(
                str(self.agent_registry_lock_path), timeout=self.lock_timeout
            ):
                # Load latest state, update, and save within the lock
                current_agents = (
                    await self._load_json_registry()
                )  # Use direct load method inside lock
                current_agents[agent_name] = timestamp
                self.agents = current_agents  # Update cache
                save_ok = await self._save_json(
                    self.agent_registry_path, self.agent_registry_lock_path, self.agents
                )
                if save_ok:
                    logger.debug(f"Recorded heartbeat for {agent_name}")
                    return True
                else:
                    logger.error(
                        f"Failed to save agent registry after recording heartbeat for {agent_name}."  # noqa: E501
                    )
                    return False
        except LockAcquisitionError:
            logger.error(
                f"Timeout recording heartbeat for {agent_name}: Could not acquire lock."
            )
            return False
        except Exception as e:
            logger.error(
                f"Failed to record heartbeat for {agent_name}: {e}", exc_info=True
            )
            return False

    async def get_all_registered_agents(
        self, force_reload: bool = False
    ) -> Dict[str, float]:
        """Return a dict of agent names to last heartbeat timestamps (purges stale)."""
        if force_reload or not self.agents:  # Reload if cache empty or forced
            await self._load_agents()

        # Filter cached agents based on TTL
        current_time = time.time()
        active_agents = {
            agent: ts
            for agent, ts in self.agents.items()
            if current_time - ts <= self.heartbeat_ttl
        }
        if len(active_agents) < len(self.agents):
            logger.debug(
                f"Returning {len(active_agents)} active agents (filtered from {len(self.agents)} cached by TTL)."  # noqa: E501
            )
        return active_agents

    async def _load_task_board(self, file_path: Path, lock_path: Path) -> List[Dict]:
        """Loads a specific task board JSON file asynchronously using its lock."""
        default_return = []
        if not await asyncio.to_thread(file_path.exists):
            logger.warning(
                f"Task board file not found: {file_path}. Returning default."
            )
            return default_return
        try:
            async with filelock.FileLock(str(lock_path), timeout=self.lock_timeout):
                content = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
                if not content.strip():
                    logger.warning(
                        f"Task board file is empty: {file_path}. Returning default."
                    )
                    return default_return
                loaded_data = json.loads(content)
                if not isinstance(loaded_data, list):
                    logger.error(
                        f"Task board file {file_path} did not contain a list. Returning default."  # noqa: E501
                    )
                    return default_return
                return loaded_data
        except json.JSONDecodeError:
            logger.error(
                f"Failed to decode JSON from {file_path}. Returning default.",
                exc_info=True,
            )
            return default_return
        except LockAcquisitionError:
            logger.error(
                f"Timeout loading {file_path}: Could not acquire lock {lock_path}. Returning default."  # noqa: E501
            )
            return default_return
        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}", exc_info=True)
            return default_return

    async def reclaim_stale_tasks(self) -> List[Dict]:
        """Moves stale WORKING tasks back to the future board."""
        reclaimed = []
        try:
            # Acquire all necessary locks simultaneously using contextlib.AsyncExitStack if needed,  # noqa: E501
            # but simple nesting is fine for a fixed number of locks.
            async with filelock.FileLock(
                str(self.agent_registry_lock_path), timeout=self.lock_timeout
            ):
                async with filelock.FileLock(
                    str(self.working_tasks_lock_path), timeout=self.lock_timeout
                ):
                    async with filelock.FileLock(
                        str(self.future_tasks_lock_path), timeout=self.lock_timeout
                    ):
                        now = time.time()
                        agents = (
                            await self._load_json_registry()
                        )  # Load latest agents inside locks
                        working_tasks = await self._load_task_board(
                            self.working_tasks_path, self.working_tasks_lock_path
                        )
                        future_tasks = await self._load_task_board(
                            self.future_tasks_path, self.future_tasks_lock_path
                        )

                        tasks_to_move = []
                        remaining_working_tasks = []

                        for task in working_tasks:
                            if str(task.get("status", "")).upper() in [
                                "WORKING",
                                "CLAIMED",
                            ]:
                                agent = task.get(
                                    "assigned_agent", task.get("claimed_by")
                                )
                                last_hb = agents.get(agent)
                                if (
                                    agent is None
                                    or last_hb is None
                                    or (now - last_hb) > self.heartbeat_ttl
                                ):
                                    task_id = task.get(
                                        "task_id", task.get("id", "UNKNOWN")
                                    )
                                    logger.warning(
                                        f"Reclaiming stale task {task_id} claimed by {agent} (Last HB: {last_hb})"  # noqa: E501
                                    )
                                    task["status"] = "PENDING"
                                    task.pop("claimed_by", None)
                                    task.pop("assigned_agent", None)
                                    task["notes"] = (
                                        f"(Reclaimed due to agent timeout at {datetime.now(timezone.utc).isoformat()}) "  # noqa: E501
                                        + task.get("notes", "")
                                    )
                                    task["timestamp_updated"] = datetime.now(
                                        timezone.utc
                                    ).isoformat()
                                    tasks_to_move.append(task)
                                    reclaimed.append(task)
                                else:
                                    remaining_working_tasks.append(task)
                            else:
                                remaining_working_tasks.append(task)

                        if reclaimed:
                            future_tasks.extend(tasks_to_move)
                            # Save must happen within the locks
                            save_working_ok = await self._save_json(
                                self.working_tasks_path,
                                self.working_tasks_lock_path,
                                remaining_working_tasks,
                            )
                            save_future_ok = await self._save_json(
                                self.future_tasks_path,
                                self.future_tasks_lock_path,
                                future_tasks,
                            )

                            if save_working_ok and save_future_ok:
                                logger.info(
                                    f"Reclaimed and moved {len(reclaimed)} stale tasks."
                                )
                            else:
                                logger.critical(
                                    "CRITICAL: Failed to save one or both boards after reclaiming tasks!"  # noqa: E501
                                )
                                # State might be inconsistent
        except LockAcquisitionError:
            logger.error(
                "Timeout reclaiming stale tasks: Could not acquire all necessary locks."
            )
        except Exception as e:
            logger.error(f"Error reclaiming stale tasks: {e}", exc_info=True)

        return reclaimed
