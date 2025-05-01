# Proposal: AgentBusMonitor Agent

**Author:** Agent5 (Lead)
**Date:** AUTO_TIMESTAMP
**Related Task(s):** DESIGN-IMPROVED-COMMS-SYSTEM-001, IMPROVE-BUS-ERROR-REPORTING-001

## 1. Goal

To improve system observability and provide a centralized point for monitoring swarm health and activity by leveraging AgentBus events.

## 2. Problem

Currently, understanding the overall state and health of the agent swarm relies primarily on aggregating logs or inspecting individual task boards/mailboxes. Diagnosing issues like stalled agents, communication bottlenecks, or widespread errors requires significant manual effort.
The recent enhancement to dispatch `SYSTEM_ERROR` on handler failures provides more data, but needs a dedicated consumer.

## 3. Proposed Solution: `AgentBusMonitor` Agent

Introduce a new, dedicated agent (`AgentBusMonitor`) responsible for subscribing to and processing key system-wide events from the AgentBus.

### 3.1. Core Functionality

*   **Event Subscription:** Subscribe to a curated set of critical `EventType` topics, including:
    *   `dreamos.agent.registered`
    *   `dreamos.agent.unregistered`
    *   `dreamos.agent.status.updated`
    *   `dreamos.system.error` (Crucial for catching handler failures)
    *   `dreamos.task.*` (Potentially sample or summarize to avoid overload, e.g., track counts of completed/failed)
    *   `dreamos.governance.*` (e.g., `POLICY_VIOLATION`)
    *   (Optional) `system.bus.status` if implemented per `agent_comms_v2_proposal.md`.
*   **State Tracking:** Maintain an internal state representing known agents, their last reported status/heartbeat, counts of recent errors, active task summaries, etc.
*   **Logging/Reporting:**
    *   Log summarized activity periodically (e.g., agent counts, error rates).
    *   Log significant events immediately (e.g., critical system errors, agents unregistering unexpectedly).
*   **Basic Analysis (Potential):**
    *   Detect potentially stalled agents (no status update/heartbeat within a threshold).
    *   Flag agents generating excessive errors.
    *   Calculate basic task throughput/failure rates.

### 3.2. Potential Extensions

*   **Queryable State:** Allow other agents (e.g., Supervisor) to query the monitor's state via mailbox messages or dedicated bus topics (e.g., `dreamos.query.monitor.agent_status`).
*   **Alerting:** Publish specific alert events (`dreamos.monitor.alert.stalled_agent`, `dreamos.monitor.alert.high_error_rate`) if thresholds are breached.
*   **Dashboard Integration:** Provide data formatted for potential future integration with monitoring dashboards.

## 4. Benefits

*   **Improved Observability:** Centralized view of swarm health.
*   **Faster Diagnostics:** Quicker identification of failing or stalled components.
*   **Proactive Monitoring:** Potential for automated alerting on system-wide issues.
*   **Foundation:** Creates a base for more sophisticated monitoring and control mechanisms.

## 5. Implementation Notes

*   Keep the initial version simple, focusing on consuming and logging key events.
*   Avoid becoming a bottleneck; processing should be lightweight.
*   Handle potential high volume of events gracefully (sampling, aggregation).

## 6. Next Steps

*   Create implementation task if proposal is accepted.
*   Refine list of subscribed events based on system needs.
