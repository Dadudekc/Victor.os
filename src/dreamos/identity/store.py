import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import AgentIdentity

# --- Configuration ---
PROJECT_ROOT = Path(
    __file__
).parent.parent.parent.parent  # Assuming src/dreamos/identity/store.py
RUNTIME_DIR = PROJECT_ROOT / "runtime"
IDENTITY_DIR = RUNTIME_DIR / "identity"
DEFAULT_STORE_FILE = IDENTITY_DIR / "agent_identities.json"
# --- Configuration End ---

logger = logging.getLogger(__name__)


class AgentIdentityStore:
    """Manages the persistence and retrieval of AgentIdentity objects."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        # Singleton implementation
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AgentIdentityStore, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, store_file: Path = DEFAULT_STORE_FILE):
        """Initializes the store, loading existing identities."""
        if self._initialized:
            return

        with self._lock:
            self.store_file = store_file
            self.identities: Dict[str, AgentIdentity] = {}
            self._ensure_store_exists()
            self.load_identities()
            self._initialized = True
            logger.info(
                f"AgentIdentityStore initialized. Store file: {self.store_file}"
            )

    def _ensure_store_exists(self):
        """Creates the identity directory and store file if they don't exist."""
        try:
            self.store_file.parent.mkdir(parents=True, exist_ok=True)
            if not self.store_file.exists():
                self.store_file.write_text("{}", encoding="utf-8")
                logger.info(f"Created empty identity store file: {self.store_file}")
        except OSError as e:
            logger.error(
                f"Error ensuring store exists at {self.store_file}: {e}", exc_info=True
            )
            # Propagate or handle critical failure?

    def load_identities(self):
        """Loads agent identities from the JSON store file."""
        with self._lock:
            if not self.store_file.exists():
                logger.warning(
                    f"Identity store file not found: {self.store_file}. Starting fresh."
                )
                self.identities = {}
                return

            try:
                raw_data = self.store_file.read_text(encoding="utf-8")
                if not raw_data.strip():
                    logger.info(f"Identity store file is empty: {self.store_file}")
                    self.identities = {}
                    return

                data = json.loads(raw_data)
                self.identities = {
                    id: AgentIdentity.from_dict(id_data) for id, id_data in data.items()
                }
                logger.info(
                    f"Loaded {len(self.identities)} agent identities from {self.store_file}"
                )
            except json.JSONDecodeError as e:
                logger.error(
                    f"Error decoding JSON from {self.store_file}: {e}. Store might be corrupt.",
                    exc_info=True,
                )
                # Decide on recovery strategy: backup? reset?
                self.identities = {}  # Resetting for now
            except Exception as e:
                logger.error(
                    f"Failed to load identities from {self.store_file}: {e}",
                    exc_info=True,
                )
                self.identities = {}  # Resetting on general failure

    def save_identities(self):
        """Saves the current agent identities to the JSON store file."""
        with self._lock:
            try:
                # Create a temporary file for atomic write
                tmp_file = self.store_file.with_suffix(self.store_file.suffix + ".tmp")
                data_to_save = {
                    id: identity.to_dict() for id, identity in self.identities.items()
                }
                tmp_file.write_text(
                    json.dumps(data_to_save, indent=4), encoding="utf-8"
                )
                # Replace the original file with the temporary file
                tmp_file.replace(self.store_file)
                logger.debug(
                    f"Saved {len(self.identities)} agent identities to {self.store_file}"
                )
            except IOError as e:
                logger.error(
                    f"Error writing identities to {self.store_file}: {e}", exc_info=True
                )
            except Exception as e:
                logger.error(f"Unexpected error saving identities: {e}", exc_info=True)

    def register_agent(
        self,
        agent_id: str,
        role: str = "Generic Agent",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentIdentity:
        """Registers a new agent or updates the last_seen timestamp of an existing one."""
        with self._lock:
            if agent_id in self.identities:
                # Agent already exists, update last seen
                identity = self.identities[agent_id]
                identity.update_last_seen()
                # Optionally update role/metadata if provided
                if role != "Generic Agent":
                    identity.role = role
                if metadata is not None:
                    identity.metadata.update(metadata)  # Merge metadata
                logger.debug(f"Agent {agent_id} already registered. Updated last_seen.")
            else:
                # New agent registration
                identity = AgentIdentity(
                    agent_id=agent_id,
                    role=role,
                    metadata=metadata if metadata is not None else {},
                )
                self.identities[agent_id] = identity
                logger.info(f"Registered new agent: {agent_id} (Role: {role})")

            self.save_identities()  # Save after every registration/update
            return identity

    def get_identity(self, agent_id: str) -> Optional[AgentIdentity]:
        """Retrieves the identity for a specific agent."""
        # No lock needed for read if underlying dict access is atomic enough,
        # but locking ensures consistency if loads/saves happen concurrently.
        with self._lock:
            return self.identities.get(agent_id)

    def list_agents(self) -> List[AgentIdentity]:
        """Returns a list of all registered agent identities."""
        with self._lock:
            return list(self.identities.values())

    def get_agent_ids(self) -> List[str]:
        """Returns a list of all registered agent IDs."""
        with self._lock:
            return list(self.identities.keys())


# Provide a singleton instance for easy access
def get_identity_store() -> AgentIdentityStore:
    """Returns the singleton instance of the AgentIdentityStore."""
    return AgentIdentityStore()
