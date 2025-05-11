# src/dreamos/core/tasks/nexus/capability_registry.py
# -*- coding: utf-8 -*-
"""Implements the centralized Agent Capability Registry logic,
integrated within the Task Nexus.
"""

import logging
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional

from dreamos.core.agents.capabilities.schema import AgentCapability
from dreamos.core.coordination.agent_bus import AgentBus, BaseEvent
from dreamos.core.coordination.event_payloads import (
    CapabilityRegisteredPayload,
    CapabilityUnregisteredPayload,
)
from dreamos.core.coordination.event_types import EventType

# Import the adapter
from dreamos.core.db.sqlite_adapter import SQLiteAdapter

# Remove FileLock imports as DB handles concurrency
# from filelock import FileLock, Timeout
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Constants no longer needed for file paths/locks
# DEFAULT_REGISTRY_PATH = "runtime/state/capability_registry.json"
# LOCK_TIMEOUT_SECONDS = 10


class CapabilityRegistry:
    """Manages the registration and querying of agent capabilities via SQLiteAdapter."""

    # --- Init with Adapter --- #
    def __init__(self, adapter: SQLiteAdapter):
        """Initializes the registry using the provided SQLiteAdapter."""
        self.adapter = adapter
        # In-memory cache of capabilities, keyed by agent_id, then capability_id
        self._capabilities: Dict[str, Dict[str, AgentCapability]] = {}
        # Thread lock for in-memory cache operations
        self._memory_lock = RLock()
        # Get AgentBus instance during init
        try:
            self._agent_bus = AgentBus()
        except Exception as e:
            logger.error(
                f"Failed to get AgentBus instance in CapabilityRegistry: {e}",
                exc_info=True,
            )
            self._agent_bus = None
        self._load_capabilities_from_db()  # Load initial cache from DB

    # --- Load from DB --- #
    def _load_capabilities_from_db(self):
        """Loads capabilities from the database into the in-memory cache."""
        logger.info("Loading capabilities from database into cache...")
        try:
            db_data = self.adapter.get_all_capabilities()
            loaded_capabilities: Dict[str, Dict[str, AgentCapability]] = {}
            total_loaded = 0
            for agent_id, caps_dict in db_data.items():
                agent_caps = {}
                for cap_id, cap_data in caps_dict.items():
                    try:
                        # Validate and convert dict back to Pydantic model
                        agent_caps[cap_id] = AgentCapability.model_validate(cap_data)
                        total_loaded += 1
                    except (TypeError, KeyError, ValidationError) as e:
                        logger.error(
                            f"Failed to load/validate capability {cap_id} for agent {agent_id} from DB: {e}"
                        )
                if agent_caps:
                    loaded_capabilities[agent_id] = agent_caps

            with self._memory_lock:
                self._capabilities = loaded_capabilities
            logger.info(
                f"Successfully loaded {total_loaded} capabilities for {len(self._capabilities)} agents from DB."
            )
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred while loading capabilities from DB: {e}"
            )
            # Keep potentially empty/stale cache on error?

    # --- Register/Unregister (using Adapter) --- #
    def register_capability(self, capability: AgentCapability) -> bool:
        """Registers or updates a capability via the adapter and updates cache."""
        if not isinstance(capability, AgentCapability):
            logger.error(
                f"Invalid type provided for capability registration: {type(capability)}"
            )
            return False

        agent_id = capability.agent_id
        cap_id = capability.capability_id
        now_utc_iso = (
            datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z"
        )
        is_update = False

        # Prepare data dictionary for the adapter
        capability_dict = capability.model_dump(mode="json")

        with self._memory_lock:
            if (
                agent_id in self._capabilities
                and cap_id in self._capabilities[agent_id]
            ):
                is_update = True
                # Preserve original registration time if updating
                capability.registered_at_utc = self._capabilities[agent_id][
                    cap_id
                ].registered_at_utc
                capability_dict["registered_at_utc"] = (
                    capability.registered_at_utc
                )  # Update dict too
            else:
                capability.registered_at_utc = now_utc_iso
                capability_dict["registered_at_utc"] = now_utc_iso

            capability.last_updated_utc = now_utc_iso
            capability_dict["last_updated_utc"] = now_utc_iso

            # 1. Update Database via Adapter
            try:
                # Pass the dictionary representation
                self.adapter.register_capability(agent_id, capability_dict)
            except Exception as db_e:
                logger.error(
                    f"DB error registering capability {cap_id} for {agent_id}: {db_e}",
                    exc_info=True,
                )
                return False  # Failed to save to DB

            # 2. Update In-Memory Cache (only after successful DB write)
            if agent_id not in self._capabilities:
                self._capabilities[agent_id] = {}
            self._capabilities[agent_id][cap_id] = (
                capability  # Store the Pydantic model
            )

            log_action = "Updated" if is_update else "Registered"
            logger.info(
                f"{log_action} capability '{cap_id}' for agent '{agent_id}' (DB & Cache)."
            )

        # 3. Dispatch Event
        payload = CapabilityRegisteredPayload(
            capability_data=capability.model_dump(mode="json")
        )
        self._dispatch_registry_event(
            EventType.SYSTEM_CAPABILITY_REGISTERED, payload.model_dump()
        )

        return True

    def unregister_capability(self, agent_id: str, capability_id: str) -> bool:
        """Removes a capability via the adapter and updates cache."""
        removed_from_db = False
        removed_from_cache = False

        # 1. Remove from Database via Adapter
        try:
            self.adapter.unregister_capability(agent_id, capability_id)
            removed_from_db = True  # Assume success if no exception
            # Note: Adapter logs warnings if not found, we might not need to check rowcount here
        except Exception as db_e:
            logger.error(
                f"DB error unregistering capability {capability_id} for {agent_id}: {db_e}",
                exc_info=True,
            )
            return False  # Failed to update DB

        # 2. Remove from In-Memory Cache
        with self._memory_lock:
            if (
                agent_id in self._capabilities
                and capability_id in self._capabilities[agent_id]
            ):
                del self._capabilities[agent_id][capability_id]
                logger.info(
                    f"Unregistered capability '{capability_id}' for agent '{agent_id}' (DB & Cache)."
                )
                if not self._capabilities[agent_id]:
                    del self._capabilities[agent_id]
                    logger.info(
                        f"Removed agent '{agent_id}' from cache as they have no remaining capabilities."
                    )
                removed_from_cache = True
            else:
                # This case should be rare if DB succeeded, but handles potential inconsistency
                logger.warning(
                    f"Capability '{capability_id}' for agent '{agent_id}' removed from DB but not found in cache."
                )

        # 3. Dispatch Event (only if removed successfully)
        if removed_from_db:
            payload = CapabilityUnregisteredPayload(
                agent_id=agent_id, capability_id=capability_id
            )
            self._dispatch_registry_event(
                EventType.SYSTEM_CAPABILITY_UNREGISTERED, payload.model_dump()
            )

        return removed_from_db  # Return success based on DB operation

    # --- Read Methods (from Cache) --- #
    def get_capability(
        self, agent_id: str, capability_id: str
    ) -> Optional[AgentCapability]:
        """Retrieves a specific capability from the in-memory cache."""
        with self._memory_lock:
            return self._capabilities.get(agent_id, {}).get(capability_id)

    def get_agent_capabilities(self, agent_id: str) -> List[AgentCapability]:
        """Retrieves all capabilities for an agent from the in-memory cache."""
        with self._memory_lock:
            # Return a copy of the list of values
            return list(self._capabilities.get(agent_id, {}).values())

    # --- Find/Query Methods (can query DB or cache) ---
    # Option 1: Query Cache (faster for simple lookups if cache is up-to-date)
    def find_capabilities(self, query: Dict[str, Any]) -> List[AgentCapability]:
        """Finds capabilities matching criteria (searching the in-memory cache)."""
        # Basic example: find by name (case-insensitive)
        results = []
        search_name = query.get("name", "").lower()
        with self._memory_lock:
            for agent_caps in self._capabilities.values():
                for cap in agent_caps.values():
                    if search_name in cap.capability_name.lower():
                        results.append(cap)
        return results

    def find_agents_for_capability(self, capability_id: str) -> List[str]:
        """Finds agents possessing a specific capability ID (searching cache)."""
        agents = []
        with self._memory_lock:
            for agent_id, caps in self._capabilities.items():
                if capability_id in caps:
                    agents.append(agent_id)
        return agents

    # --- Other Methods (Dispatch, Status Update - Keep as is or adapt if needed) ---
    def _dispatch_registry_event(
        self, event_type: EventType, payload_data: Dict[str, Any]
    ):
        # (Implementation remains largely the same)
        if not self._agent_bus:
            logger.warning(
                f"AgentBus not available, skipping dispatch of event type {event_type.name}"
            )
            return
        try:
            event = BaseEvent(
                event_type=event_type, source_id="CapabilityRegistry", data=payload_data
            )
            self._agent_bus.dispatch_event(event)
            logger.debug(f"Dispatched event: {event_type.name}")
        except Exception as e:
            logger.error(
                f"Failed to dispatch event {event_type.name}: {e}", exc_info=True
            )

    # Note: This method interacts with capability *state* (is_active, last_verified)
    # which is NOT part of the current DB schema. This needs to be reconciled.
    # Option A: Add these fields to the DB schema.
    # Option B: Keep this state only in memory (simpler but lost on restart).
    # Option C: Store this state elsewhere (e.g., agent_heartbeats table or separate state table).
    # For now, we'll keep it operating on the in-memory cache only.
    def update_capability_status(
        self,
        agent_id: str,
        capability_id: str,
        is_active: Optional[bool] = None,
        last_verified_utc: Optional[str] = None,
    ) -> bool:
        """Updates the status fields of a capability in the in-memory cache ONLY."""
        with self._memory_lock:
            if (
                agent_id in self._capabilities
                and capability_id in self._capabilities[agent_id]
            ):
                capability = self._capabilities[agent_id][capability_id]
                updated = False
                if is_active is not None:
                    capability.is_active = is_active
                    updated = True
                if last_verified_utc is not None:
                    capability.last_verified_utc = last_verified_utc
                    updated = True

                if updated:
                    # Note: This change is NOT persisted to the DB currently.
                    logger.info(
                        f"Updated in-memory status for capability '{capability_id}' for agent '{agent_id}'."
                    )
                    return True
                else:
                    logger.debug("No status fields provided to update.")
                    return False
            else:
                logger.warning(
                    f"Attempted to update status for non-existent capability '{capability_id}' or agent '{agent_id}'."
                )
                return False
