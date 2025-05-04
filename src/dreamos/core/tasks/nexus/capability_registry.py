# src/dreamos/core/tasks/nexus/capability_registry.py
# -*- coding: utf-8 -*-
"""Implements the centralized Agent Capability Registry logic,
integrated within the Task Nexus.
"""

import json  # noqa: I001
import logging
import os
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional

from dreamos.core.agents.capabilities.schema import AgentCapability

# EDIT START: Import AgentBus, BaseEvent and EventType from canonical sources
from dreamos.core.coordination.agent_bus import AgentBus, BaseEvent
from dreamos.core.coordination.event_payloads import (
    CapabilityRegisteredPayload,
    CapabilityUnregisteredPayload,
)
from dreamos.core.coordination.event_types import EventType  # Import from new file
from filelock import FileLock, Timeout
from pydantic import ValidationError

# EDIT END
# Assuming utils exist or will be created
# from dreamos.utils.file_io import atomic_write_json

logger = logging.getLogger(__name__)

# Constants
DEFAULT_REGISTRY_PATH = "runtime/state/capability_registry.json"
LOCK_TIMEOUT_SECONDS = 10  # Timeout for acquiring file lock

# EDIT START: Remove fallback string event types
# EVENT_TYPE_CAPABILITY_REGISTERED = "dreamos.system.capability.registered"
# EVENT_TYPE_CAPABILITY_UNREGISTERED = "dreamos.system.capability.unregistered"
# EDIT END


class CapabilityRegistry:
    """Manages the registration, querying, and persistence of agent capabilities."""

    def __init__(self, registry_path: str = DEFAULT_REGISTRY_PATH):
        """Initializes the registry, loading data from the specified path."""
        self.registry_path = registry_path
        self.registry_lock_path = f"{registry_path}.lock"
        # In-memory cache of capabilities, keyed by agent_id, then capability_id
        self._capabilities: Dict[str, Dict[str, AgentCapability]] = {}
        # Thread lock for in-memory operations
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
        self._load_registry()

    def _get_file_lock(self) -> FileLock:
        """Returns a FileLock instance for the registry file."""
        return FileLock(self.registry_lock_path, timeout=LOCK_TIMEOUT_SECONDS)

    def _load_registry(self):
        """Loads the capability registry from the JSON file."""
        logger.info(f"Loading capability registry from {self.registry_path}")
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)

        try:
            with self._get_file_lock():
                if not os.path.exists(self.registry_path):
                    logger.warning(
                        f"Registry file not found at {self.registry_path}. Initializing empty registry."  # noqa: E501
                    )
                    # Create an empty file if it doesn't exist
                    with open(self.registry_path, "w", encoding="utf-8") as f:
                        json.dump({}, f)
                    self._capabilities = {}
                    return

                with open(self.registry_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    loaded_capabilities: Dict[str, Dict[str, AgentCapability]] = {}
                    for agent_id, caps in raw_data.items():
                        agent_caps = {}
                        for cap_id, cap_data in caps.items():
                            try:
                                agent_caps[cap_id] = AgentCapability.model_validate(
                                    cap_data
                                )
                            except (TypeError, KeyError, ValidationError) as e:
                                logger.error(
                                    f"Failed to load capability {cap_id} for agent {agent_id}: Invalid data - {e}"  # noqa: E501
                                )
                        loaded_capabilities[agent_id] = agent_caps

                    with self._memory_lock:
                        self._capabilities = loaded_capabilities
                    logger.info(
                        f"Successfully loaded {sum(len(caps) for caps in self._capabilities.values())} capabilities for {len(self._capabilities)} agents."  # noqa: E501
                    )

        except Timeout:
            logger.error(
                f"Could not acquire lock for {self.registry_path} within {LOCK_TIMEOUT_SECONDS}s during load."  # noqa: E501
            )
            # Decide on behavior: raise error, use cached (if any), or operate without loading?  # noqa: E501
            # For now, log error and continue with potentially empty/stale cache.
        except json.JSONDecodeError:
            logger.exception(
                f"Failed to decode JSON from {self.registry_path}. Registry might be corrupted."  # noqa: E501
            )
            # Potentially load backup or initialize empty
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred while loading the registry: {e}"
            )

    def _save_registry(self):
        """Saves the current in-memory registry state to the JSON file atomically."""
        logger.debug(f"Attempting to save capability registry to {self.registry_path}")
        # Prepare data for JSON serialization
        serializable_data = {}
        with self._memory_lock:
            for agent_id, caps in self._capabilities.items():
                serializable_data[agent_id] = {
                    cap_id: cap.model_dump(mode="json") for cap_id, cap in caps.items()
                }

        try:
            with self._get_file_lock():
                # Simple atomic write using temp file + rename (replace with atomic_write_json if available)  # noqa: E501
                temp_path = f"{self.registry_path}.tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(serializable_data, f, indent=2)
                os.replace(temp_path, self.registry_path)
                logger.debug(f"Successfully saved registry to {self.registry_path}")
        except Timeout:
            logger.error(
                f"Could not acquire lock for {self.registry_path} within {LOCK_TIMEOUT_SECONDS}s during save."  # noqa: E501
            )
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred while saving the registry: {e}"
            )
            # Consider error handling: retry? notify? revert in-memory changes?

    def _dispatch_registry_event(
        self, event_type: EventType, payload_data: Dict[str, Any]
    ):  # EDIT: Use EventType
        """Helper to safely dispatch registry-related events."""
        if not self._agent_bus:
            logger.warning(
                f"AgentBus not available, skipping dispatch of event type {event_type.name}"  # noqa: E501
            )  # EDIT: Use enum name
            return

        try:
            event = BaseEvent(
                event_type=event_type,  # EDIT: Use EventType enum member
                source_id="CapabilityRegistry",  # Or potentially "TaskNexus"
                data=payload_data,
            )
            # AgentBus.dispatch_event is synchronous in the current implementation
            self._agent_bus.dispatch_event(event)
            logger.debug(f"Dispatched event: {event_type.name}")  # EDIT: Use enum name
        except Exception as e:
            logger.error(
                f"Failed to dispatch event {event_type.name}: {e}", exc_info=True
            )  # EDIT: Use enum name

    def register_capability(self, capability: AgentCapability) -> bool:
        """Registers or updates a capability for an agent."""
        if not isinstance(capability, AgentCapability):
            logger.error(
                f"Invalid type provided for capability registration: {type(capability)}"
            )
            return False

        agent_id = capability.agent_id
        cap_id = capability.capability_id
        is_update = False  # Track if it's an update or new registration
        now_utc_iso = (
            datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z"
        )  # Get timestamp once

        with self._memory_lock:
            if agent_id not in self._capabilities:
                self._capabilities[agent_id] = {}
                capability.registered_at_utc = (
                    now_utc_iso  # Set registration time for new entries
                )
            else:
                if cap_id in self._capabilities[agent_id]:
                    is_update = True
                    # Preserve original registration time if updating
                    capability.registered_at_utc = self._capabilities[agent_id][
                        cap_id
                    ].registered_at_utc
                else:
                    capability.registered_at_utc = now_utc_iso  # Set registration time for new capability for existing agent  # noqa: E501

            capability.last_updated_utc = now_utc_iso  # Always update this timestamp
            self._capabilities[agent_id][cap_id] = capability
            log_action = "Updated" if is_update else "Registered"
            logger.info(f"{log_action} capability '{cap_id}' for agent '{agent_id}'.")

        self._save_registry()

        # EDIT START: Dispatch event using Enum and correct Pydantic serialization
        payload = CapabilityRegisteredPayload(
            capability_data=capability.model_dump(mode="json")
        )
        self._dispatch_registry_event(
            EventType.SYSTEM_CAPABILITY_REGISTERED, payload.model_dump()
        )
        # EDIT END

        return True

    def unregister_capability(self, agent_id: str, capability_id: str) -> bool:
        """Removes a capability registration for an agent."""
        removed = False
        with self._memory_lock:
            if (
                agent_id in self._capabilities
                and capability_id in self._capabilities[agent_id]
            ):
                del self._capabilities[agent_id][capability_id]
                logger.info(
                    f"Unregistered capability '{capability_id}' for agent '{agent_id}'."
                )
                if not self._capabilities[
                    agent_id
                ]:  # Remove agent entry if no capabilities left
                    del self._capabilities[agent_id]
                    logger.info(
                        f"Removed agent '{agent_id}' from registry as they have no remaining capabilities."  # noqa: E501
                    )
                removed = True
            else:
                logger.warning(
                    f"Attempted to unregister non-existent capability '{capability_id}' for agent '{agent_id}'."  # noqa: E501
                )

        if removed:
            self._save_registry()
            # EDIT START: Dispatch event using Enum and correct Pydantic serialization
            payload = CapabilityUnregisteredPayload(
                agent_id=agent_id, capability_id=capability_id
            )
            self._dispatch_registry_event(
                EventType.SYSTEM_CAPABILITY_UNREGISTERED, payload.model_dump()
            )
            # EDIT END

        return removed

    def get_capability(
        self, agent_id: str, capability_id: str
    ) -> Optional[AgentCapability]:
        """Retrieves a specific capability for a specific agent."""
        with self._memory_lock:
            return self._capabilities.get(agent_id, {}).get(capability_id)

    def get_agent_capabilities(self, agent_id: str) -> List[AgentCapability]:
        """Retrieves all registered capabilities for a specific agent."""
        with self._memory_lock:
            return list(self._capabilities.get(agent_id, {}).values())

    def find_capabilities(self, query: Dict[str, Any]) -> List[AgentCapability]:
        """Finds capabilities matching the given query criteria.

        Example Query (TBD - very basic implementation):
        query = {
            'capability_id': 'code.python.format.black',
            'tags': ['python', 'formatting'],
            'min_version': '24.0.0', # Optional: requires version comparison logic
            'is_active': True
        }
        """
        results = []
        required_capability_id = query.get("capability_id")
        required_tags = set(query.get("tags", []))
        required_active = query.get("is_active", True)
        required_version = query.get("version")  # EDIT: Get requested version
        # min_version = query.get('min_version') # TODO: Implement version comparison

        with self._memory_lock:
            for agent_id, agent_caps in self._capabilities.items():
                for cap_id, capability in agent_caps.items():
                    # Match capability ID if specified
                    if required_capability_id and cap_id != required_capability_id:
                        continue

                    # Match active status
                    if required_active and not capability.is_active:
                        continue

                    # Match tags (all required tags must be present)
                    if required_tags and not required_tags.issubset(
                        set(capability.metadata.tags)
                    ):
                        continue

                    # EDIT START: Add basic exact version match
                    if (
                        required_version
                        and capability.metadata.version != required_version
                    ):
                        # Note: This is exact match only. Semantic comparison (>=, <, ^) is complex.  # noqa: E501
                        continue
                    # EDIT END

                    # TODO: Add version comparison logic if min_version is provided

                    results.append(capability)

        logger.info(f"Capability query '{query}' found {len(results)} results.")
        return results

    def find_agents_for_capability(
        self, capability_id: str, require_active: bool = True
    ) -> List[str]:
        """Finds agent IDs that offer a specific capability."""
        agent_ids = []
        with self._memory_lock:
            for agent_id, agent_caps in self._capabilities.items():
                if capability_id in agent_caps:
                    if not require_active or agent_caps[capability_id].is_active:
                        agent_ids.append(agent_id)
        logger.info(
            f"Found {len(agent_ids)} agents for capability '{capability_id}' (require_active={require_active})."  # noqa: E501
        )
        return agent_ids

    # EDIT START: Implement update_capability_status method
    def update_capability_status(
        self,
        agent_id: str,
        capability_id: str,
        is_active: Optional[bool] = None,
        last_verified_utc: Optional[str] = None,
    ) -> bool:
        """Updates the status fields (is_active, last_verified_utc) for a specific capability."""  # noqa: E501
        updated = False
        with self._memory_lock:
            if (
                agent_id in self._capabilities
                and capability_id in self._capabilities[agent_id]
            ):
                capability = self._capabilities[agent_id][capability_id]
                if is_active is not None and capability.is_active != is_active:
                    capability.is_active = is_active
                    logger.info(
                        f"Updated is_active status for {agent_id}/{capability_id} to {is_active}"  # noqa: E501
                    )
                    updated = True
                if (
                    last_verified_utc is not None
                    and capability.last_verified_utc != last_verified_utc
                ):
                    capability.last_verified_utc = last_verified_utc
                    logger.info(
                        f"Updated last_verified_utc for {agent_id}/{capability_id} to {last_verified_utc}"  # noqa: E501
                    )
                    updated = True

                if updated:
                    # Also update the general last_updated timestamp
                    capability.last_updated_utc = (
                        datetime.now(timezone.utc).isoformat(timespec="milliseconds")
                        + "Z"
                    )
            else:
                logger.warning(
                    f"Attempted to update status for non-existent capability '{capability_id}' for agent '{agent_id}'."  # noqa: E501
                )

        if updated:
            self._save_registry()
            # Optionally dispatch an update event?
            # payload = CapabilityUpdatedPayload(...) # Define payload
            # self._dispatch_registry_event(EventType.SYSTEM_CAPABILITY_UPDATED, payload.__dict__)  # noqa: E501

        return updated

    # EDIT END

    # Potential future methods:
    # def update_capability_performance(...)
