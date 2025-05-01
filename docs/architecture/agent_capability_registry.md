# Agent Capability Registry Design

**Status:** Proposed
**Author:** Agent4
**Task:** `CAPTAIN8-DEFINE-CAPABILITY-REGISTRY-001`
**Date:** [AUTO_DATE]

## 1. Overview

This document proposes the design for a centralized **Agent Capability Registry** within the DreamOS swarm. The registry will serve as the authoritative source for discovering which agents possess specific capabilities, along with detailed metadata about those capabilities (e.g., version, performance, resource needs, input/output schema).

## 2. Problem Statement

Currently, agent capabilities are represented simplistically, often as just a list of strings (e.g., within the `AgentBus`'s in-memory store or basic registration payloads). This lacks the granularity required for:

*   **Advanced Task Matching:** Efficiently routing tasks to agents based on specific requirements (e.g., "find an agent that can format Python code using Black v24.x and handles input files up to 5MB").
*   **Resource-Aware Scheduling:** Selecting agents based on their estimated performance or resource consumption.
*   **Capability Versioning:** Managing different versions of the same capability across agents.
*   **Dynamic Discovery:** Allowing agents to dynamically discover and utilize capabilities offered by others without hardcoded dependencies.
*   **System Observability:** Providing a clear overview of the swarm's collective abilities.

## 3. Proposed Solution

We propose a centralized registry service/module that maintains persistent records of agent capabilities using a structured schema.

### 3.1 Capability Schema

The core data structure is `AgentCapability`, defined in `src/dreamos/core/agents/capabilities/schema.py`. It includes nested dataclasses for:

*   `CapabilitySchema`: Input/output/error JSON schema definitions.
*   `CapabilityMetadata`: Version, description, tags, maturity, owner, dependencies.
*   `CapabilityPerformance`: Latency, throughput, cost estimates.
*   `CapabilityResourceRequirements`: CPU, memory, GPU, network, storage needs.

Key fields:
*   `agent_id`: The ID of the agent offering the capability.
*   `capability_id`: A unique, hierarchical identifier for the capability (e.g., `core.io.file.read`, `tool.code.python.format.black`, `model.llm.generate.text.gpt4`).
*   `is_active`: Boolean flag to enable/disable without deleting.
*   Timestamps: `registered_at_utc`, `last_updated_utc`, `last_verified_utc`.

*(Refer to `schema.py` for full details)*

### 3.2 Registry Location & Implementation

**Chosen Approach:** Integrate the registry logic as a module within the **Task Nexus** (`src/dreamos/core/tasks/nexus`).

**Rationale:**
*   **Centrality:** The Nexus is already a central coordination point for tasks. Task assignment is a primary use case for the capability registry.
*   **Existing Infrastructure:** Leverage existing Nexus persistence, locking, and potentially event handling mechanisms.
*   **Reduced Complexity:** Avoids introducing a new standalone service/agent initially.

**Persistence:**
*   **Initial:** Store registry data in a dedicated JSON or YAML file (e.g., `runtime/state/capability_registry.json`). Implement file locking for safe concurrent access.
*   **Future:** Migrate to a more robust solution like SQLite or a dedicated key-value store if performance or concurrency becomes an issue.

### 3.3 Interaction Protocol / API

The registry will expose an internal API (methods within the Nexus module) and potentially interact via Agent Bus events.

**Core Methods (Conceptual - within Nexus):**

*   `register_capability(capability: AgentCapability) -> bool`: Adds or updates a capability. Validates schema. Persists changes. Dispatches `CAPABILITY_REGISTERED` event.
*   `unregister_capability(agent_id: str, capability_id: str) -> bool`: Marks a capability as inactive or removes it. Persists changes. Dispatches `CAPABILITY_UNREGISTERED` event.
*   `update_capability_status(agent_id: str, capability_id: str, is_active: bool, last_verified_utc: str) -> bool`: Updates activity status and verification time.
*   `get_capability(agent_id: str, capability_id: str) -> Optional[AgentCapability]`: Retrieves a specific capability record.
*   `get_agent_capabilities(agent_id: str) -> List[AgentCapability]`: Retrieves all active capabilities for an agent.
*   `find_capabilities(query: Dict[str, Any]) -> List[AgentCapability]`: Searches the registry based on criteria (tags, IDs, schema elements, performance bounds). *Query structure TBD.*
*   `find_agents_for_capability(capability_id: str, min_version: Optional[str] = None, require_active: bool = True) -> List[str]`: Finds agent IDs offering a specific capability.

**Agent Bus Events:**

*   `SYSTEM_CAPABILITY_REGISTERED`: Payload `AgentCapability`.
*   `SYSTEM_CAPABILITY_UPDATED`: Payload `AgentCapability`.
*   `SYSTEM_CAPABILITY_UNREGISTERED`: Payload `{agent_id: str, capability_id: str}`.
*   `QUERY_CAPABILITIES`: Payload `{query: Dict}`. Sent *to* the Nexus/Registry.
*   `QUERY_CAPABILITIES_RESPONSE`: Payload `{capabilities: List[AgentCapability]}`. Sent *from* the Nexus/Registry.

### 3.4 Agent Integration

*   **Registration:** Agents will register their capabilities (defined using the `AgentCapability` schema) with the Nexus/Registry upon initialization or when acquiring new skills.
*   **Updates:** Agents are responsible for updating their capability records (e.g., version changes, performance recalibration, marking inactive if temporarily unable).
*   **Querying:** Agents (or the Task Assigner) can query the registry via the Nexus API or Agent Bus events to find suitable capabilities/agents for tasks.

## 4. Implementation Plan (High-Level)

1.  **Refine Schema:** Finalize fields in `schema.py`.
2.  **Nexus Module:** Create `src/dreamos/core/tasks/nexus/capability_registry.py`.
    *   Implement persistence (load/save JSON/YAML with locking).
    *   Implement core API methods (`register`, `unregister`, `get`, `find`).
    *   Integrate with Nexus initialization.
3.  **Agent Bus Integration:** Define and handle relevant Agent Bus events.
4.  **Agent Adaptation:** Modify `BaseAgent` or provide utilities for agents to easily register/update/query capabilities.
5.  **Task Assignment:** Update task assignment logic (e.g., in `TaskNexus` or a dedicated `TaskAssigner`) to utilize the registry for matching tasks to agents.
6.  **Testing:** Implement unit and integration tests.
7.  **Documentation:** Update relevant guides (agent development, task lifecycle).

## 5. Open Questions & Future Enhancements

*   **Query Language:** Define a robust structure for the `find_capabilities` query. Simple key-value? More complex DSL?
*   **Schema Validation:** Integrate JSON Schema validation for `input/output/error_schema` fields.
*   **Capability Verification:** Implement a mechanism for the registry or a dedicated monitor agent to periodically verify if agents can actually perform their registered capabilities (health checks). Update `last_verified_utc`.
*   **Scalability:** Re-evaluate persistence layer (e.g., SQLite, database) if the number of agents/capabilities grows significantly.
*   **Security/Trust:** How to ensure agents provide accurate capability information? (Lower priority for initial implementation).
*   **Dynamic Capability Loading:** Standardize how agents discover and load code/models associated with a capability.

## 6. Alternatives Considered

*   **AgentBus Only:** Rely solely on the AgentBus's in-memory store. *Rejected: Lacks persistence, insufficient schema detail, harder to query.*
*   **Standalone Registry Agent:** Create a dedicated agent for the registry. *Rejected: Adds complexity (deployment, discovery, communication overhead) for initial implementation. Can be migrated to later if needed.*
*   **Decentralized/P2P:** Agents share capabilities directly. *Rejected: Significantly increases complexity in discovery and consistency management.*
