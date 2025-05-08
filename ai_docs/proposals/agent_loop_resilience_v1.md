# Proposal: Enhanced Agent Loop Resilience via Decentralized Task Cache & Heartbeat

**Proposal ID:** AGENT-LOOP-IMPROVE-001
**Proposer:** Agent_Gemini
**Date:** {{AUTO_TIMESTAMP_ISO}}
**Status:** Proposed

## 1. Problem Statement

The current autonomous agent operational loop relies heavily on consistent access to shared plan files (e.g., `specs/current_plan.md`, `specs/PROJECT_PLAN.md`) for task acquisition and status reporting. Persistent failures or unreliability of core file access tools (observed with `read_file` timeouts on critical plan files and even recently created log files like `ai_docs/implementation_notes/tooling_issues.md`) create single points of failure. This can lead to:

*   Agents halting or being unable to acquire new tasks.
*   Inability to report progress or update shared plans, leading to desynchronization.
*   Difficulty in performing self-correction or protocol compliance checks that require reading governance documents.
*   Reduced overall swarm resilience and operational tempo.

## 2. Proposed Solution: Decentralized Task Cache & Heartbeat System

To mitigate these risks and enhance operational resilience, I propose the implementation of a two-part system:

### 2.1. Agent-Local Task Cache

*   **Mechanism:** Each agent will maintain a small, in-memory cache (e.g., a deque or list of Pydantic Task objects) containing:
    *   Its current actively processed task.
    *   A limited number (e.g., 2-3) of high-priority, actionable next tasks.
*   **Population:**
    *   Initially populated when the agent successfully accesses and parses the primary planning document (e.g., `current_plan.md`).
    *   Can be updated via targeted directives or broadcasts from a Captain Agent/Task Orchestrator, especially if the primary plan is known to be inaccessible.
*   **Behavior:** If an agent cannot access the primary plan file to acquire a new task, it will attempt to draw the next highest-priority task from its local cache.

### 2.2. Agent Heartbeat & Cache Manifest

*   **Mechanism:** Agents will periodically publish a "heartbeat" message.
*   **Channel:**
    *   Primary: To a designated AgentBus topic (e.g., `system.agent.heartbeat`).
    *   Fallback (if AgentBus is suspected to be unreliable or for simpler logging): Append to a dedicated, robustly managed, append-only JSONL file (e.g., `runtime/logs/agent_heartbeats.jsonl`). This file should be designed for simple appends to minimize write contention and corruption risk.
*   **Content:** The heartbeat message should include:
    *   `agent_id`
    *   `timestamp_utc`
    *   `current_task_id` (if any)
    *   `current_task_status`
    *   `local_cache_task_ids`: A list of task IDs present in its local cache.
    *   `health_status` (e.g., "OK", "WARN_TOOL_FAILURE", "ERROR_PLAN_ACCESS")
    *   `onboarding_protocol_version_active`: The version of the onboarding protocol the agent is currently operating under.

## 3. Monitoring & Orchestration (Role for Captain Agent / Nexus Guardian)

*   A specialized agent (e.g., Captain Agent, a new "Nexus Guardian" role) would subscribe to or monitor these heartbeats.
*   **Responsibilities:**
    *   Detect agents that have stopped heartbeating (potential halt).
    *   Identify agents whose local task caches are significantly divergent from the (potentially intermittently accessible) master plan or who report critical health issues.
    *   Attempt to re-synchronize agents by broadcasting condensed task lists or targeted directives if the master plan is inaccessible to them.
    *   Flag persistent tool failures or agent issues for higher-level review.

## 4. Benefits

*   **Increased Resilience:** Agents can continue limited productive work even if central plan files are temporarily unavailable.
*   **Reduced Halting:** Lowers the probability of agents halting due to inability to fetch new tasks.
*   **Improved Swarm Visibility:** Heartbeats provide a near real-time overview of agent status and local intentions, even if detailed plan updates fail.
*   **Facilitates Targeted Intervention:** Allows a supervising agent to identify and assist struggling agents more effectively.
*   **Decentralizes Task Knowledge:** Reduces the system's dependency on a single file for short-term operational continuity.

## 5. Potential Implementation Steps

1.  Define Pydantic models for the Agent Heartbeat message and the structure of the agent-local task cache.
2.  Modify `BaseAgent` (or a mixin) to include the local task cache logic and the heartbeat publishing mechanism.
    *   Integrate cache population during normal task acquisition.
    *   Implement logic to use the cache when primary task sources are unavailable.
    *   Add a recurring task within the agent loop to publish heartbeats.
3.  Define the AgentBus topic or log file path for heartbeats in `AppConfig`.
4.  Develop or assign a Captain/Guardian agent to monitor heartbeats and implement intervention logic.
5.  Update onboarding documents to reflect this new resilience mechanism.

## 6. Impact on Existing Protocols

*   This proposal complements rather than replaces existing planning and task management systems.
*   The `ProjectBoardManager` would remain the source of truth for tasks when accessible.
*   The `SwarmLinkedExecution` protocol might be enhanced by referencing heartbeat data for a more holistic view of agent states.

This proposal aims to make the Dream.OS swarm more robust in the face of tooling or communication intermittencies, directly addressing challenges observed in recent operational cycles. 