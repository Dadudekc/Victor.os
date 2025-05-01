# src/dreamos/core/identity/agent_identity_store.py
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..utils.file_locking import FileLock, LockAcquisitionError, LockDirectoryError
from .agent_identity import AgentIdentity

logger = logging.getLogger(__name__)

# Determine runtime directory relative to this file's location
# Assuming this file is in src/dreamos/core/identity/
# runtime/ is expected at src/../runtime/
RUNTIME_DIR = Path(__file__).resolve().parents[3] / "runtime"
IDENTITY_DIR = RUNTIME_DIR / "identity"
DEFAULT_STORE_PATH = IDENTITY_DIR / "agents.json"


class AgentIdentityStore:
    """Handles persistence of AgentIdentity objects to a JSON file."""

    def __init__(self, store_path: Path | str = DEFAULT_STORE_PATH):
        self.store_path = Path(store_path)

    async def _ensure_store_exists(self):
        """Creates the identity directory and the store file if they don't exist."""
        try:
            await asyncio.to_thread(
                self.store_path.parent.mkdir, parents=True, exist_ok=True
            )
            exists = await asyncio.to_thread(self.store_path.exists)
            if not exists:
                async with FileLock(self.store_path):
                    exists_in_lock = await asyncio.to_thread(self.store_path.exists)
                    if not exists_in_lock:

                        def write_empty_json():
                            with open(self.store_path, "w", encoding="utf-8") as f:
                                json.dump({}, f)

                        await asyncio.to_thread(write_empty_json)
                        logger.info(
                            f"Initialized agent identity store at: {self.store_path}"
                        )
        except (OSError, LockAcquisitionError, LockDirectoryError) as e:
            logger.error(
                f"Failed to create agent identity store directory or file at {self.store_path}: {e}",
                exc_info=True,
            )
            raise

    async def _load_data(self) -> Dict[str, Dict]:
        """Loads the raw data from the JSON file using file lock."""
        async with FileLock(self.store_path):
            try:

                def read_sync():
                    if not self.store_path.exists():
                        return None
                    with open(self.store_path, "r", encoding="utf-8") as f:
                        return f.read()

                content = await asyncio.to_thread(read_sync)

                if content is None or not content.strip():
                    return {}
                return json.loads(content)
            except FileNotFoundError:
                logger.warning(
                    f"Agent identity store file not found at {self.store_path}. Returning empty data."
                )
                return {}
            except json.JSONDecodeError:
                logger.error(
                    f"Failed to decode JSON from agent identity store {self.store_path}. Returning empty data.",
                    exc_info=True,
                )
                return {}
            except Exception as e:
                logger.error(f"Failed to load agent identity data: {e}", exc_info=True)
                return {}

    async def _save_data(self, data: Dict[str, Dict]):
        """Saves the provided data to the JSON file atomically using file lock."""
        temp_path = self.store_path.with_suffix(f".{os.getpid()}.tmp")
        try:
            serializable_data = {}
            for agent_id, agent_data in data.items():
                serializable_data[agent_id] = agent_data.copy()

            def write_sync():
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(serializable_data, f, indent=2)
                os.replace(temp_path, self.store_path)

            async with FileLock(self.store_path):
                await asyncio.to_thread(write_sync)

        except Exception as e:
            logger.error(
                f"Failed to save agent identity data to {self.store_path}: {e}",
                exc_info=True,
            )
            if await asyncio.to_thread(temp_path.exists):
                try:
                    await asyncio.to_thread(os.remove, temp_path)
                except OSError:
                    logger.error(f"Failed to remove temporary save file: {temp_path}")

    async def save(self, identity: AgentIdentity):
        """Saves or updates a single agent identity in the store."""
        data = await self._load_data()
        identity_dict = identity.model_dump(mode="json")
        data[identity.agent_id] = identity_dict
        await self._save_data(data)
        logger.debug(f"Saved identity for agent: {identity.agent_id}")

    async def load(self, agent_id: str) -> Optional[AgentIdentity]:
        """Loads a single agent identity from the store."""
        data = await self._load_data()
        agent_data = data.get(agent_id)
        if agent_data:
            try:
                return AgentIdentity(**agent_data)
            except Exception as e:
                logger.error(
                    f"Failed to parse identity data for agent {agent_id}: {e}",
                    exc_info=True,
                )
                return None
        return None

    async def get_all(self) -> List[AgentIdentity]:
        """Loads all agent identities from the store."""
        data = await self._load_data()
        identities = []
        for agent_id, agent_data in data.items():
            try:
                identities.append(AgentIdentity(**agent_data))
            except Exception as e:
                logger.error(
                    f"Failed to parse identity data for agent {agent_id} during get_all: {e}",
                    exc_info=True,
                )
                continue
        return identities

    async def delete(self, agent_id: str) -> bool:
        """Deletes an agent identity from the store."""
        data = await self._load_data()
        if agent_id in data:
            del data[agent_id]
            await self._save_data(data)
            logger.info(f"Deleted identity for agent: {agent_id}")
            return True
        logger.warning(f"Attempted to delete non-existent agent identity: {agent_id}")
        return False
