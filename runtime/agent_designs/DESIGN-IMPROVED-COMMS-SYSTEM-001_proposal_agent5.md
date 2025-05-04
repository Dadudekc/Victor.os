# Design Proposal: Improved Inter-Agent Communication System

**Task ID:** DESIGN-IMPROVED-COMMS-SYSTEM-001
**Agent:** Agent 5
**Date:** [CURRENT_UTC_ISO8601_TIMESTAMP]

## 1. Analysis of Current Systems

Dream.OS currently utilizes two primary communication mechanisms:

*   **File-based Mailboxes (`runtime/agent_comms/agent_mailboxes/`):**
    *   **Mechanism:** Direct file writes/reads in dedicated agent directories.
    *   **Format:** Standardized JSON messages (via `MailboxHandler` & `agent_utils`).
    *   **Pros:** Simple concept, persistent messages (as files).
    *   **Cons:**
        *   **Reliability/Concurrency:** Lacks explicit file locking in core write utilities (`write_mailbox_message`), risking race conditions and data corruption during concurrent access.
        *   **Visibility/Discoverability:** Requires polling directories; no inherent notification. Global view is difficult.
        *   **Performance:** File I/O and directory scanning can be slow, especially at scale.
        *   **Monitoring:** Hard to integrate with real-time monitoring without external file watchers.
        *   **Atomicity:** Reading/processing/archiving messages is not an atomic operation.
*   **AgentBus (`src/dreamos/coordination/agent_bus.py`):**
    *   **Mechanism:** In-memory publish/subscribe based on topic strings/patterns (`SimpleEventBus` backend).
    *   **Format:** `BaseEvent` objects with dictionary payloads.
    *   **Pros:** Asynchronous, decoupled communication for broadcast events.
    *   **Cons:**
        *   **Reliability:** In-memory only; messages lost on crash/restart. No guaranteed delivery.
        *   **Visibility:** No built-in queue inspection.
        *   **Scalability:** Limited to a single process.
        *   **Error Handling:** Basic handler error logging exists, but no robust retry or dead-letter mechanism.

## 2. Identified Requirements for Improvement

Based on the analysis and task description, the improved system should prioritize:

*   **Reliability:** Guaranteed or at-least-once message delivery, resilience to agent/system crashes.
*   **Visibility:** Ability to monitor queue status (depth, pending messages), processing status, and errors.
*   **Concurrency:** Safe handling of simultaneous message production and consumption.
*   **Performance:** Reasonable throughput and latency, avoiding file system bottlenecks where possible.
*   **Integration:** Easier integration with system monitoring tools/dashboards.
*   **Flexibility:** Support both broadcast (pub/sub) and directed (point-to-point/queued) communication patterns effectively.

## 3. Proposed Design Directions (Options)

Several approaches could meet these requirements. Further investigation is needed to determine feasibility and trade-offs within the Dream.OS environment.

*   **Option A: AgentBus Enhancement with Persistent Backend**
    *   **Concept:** Replace the `SimpleEventBus` backend with a persistent queue system (e.g., Redis Streams, potentially a lightweight file/DB-based queue if external dependencies are disallowed).
    *   **Pros:** Leverages existing AgentBus interface familiar to agents. Can potentially offer persistence and better delivery guarantees.
    *   **Cons:** Requires significant AgentBus refactoring. Choice of backend impacts complexity and dependencies.
    *   **Considerations:** Need for message acknowledgements, DLQ implementation.

*   **Option B: Dedicated Message Queue Service**
    *   **Concept:** Introduce a dedicated message queue service (e.g., running RabbitMQ, ZeroMQ, or a custom Python service wrapping a queue library) independent of the AgentBus.
    *   **Pros:** Mature technology options available. Clear separation of concerns. Often includes features like routing, acknowledgements, persistence, and monitoring interfaces.
    *   **Cons:** Introduces a new system dependency. Agents need new client logic to interact with the queue service.
    *   **Considerations:** Deployment complexity, resource usage of the queue service.

*   **Option C: Hybrid Approach**
    *   **Concept:** Retain AgentBus for ephemeral, best-effort broadcasts (status updates, discoveries). Use a new, dedicated mechanism (e.g., improved file-based queue *with locking*, or a simple DB-based queue) for critical, guaranteed delivery messages (like task assignments or commands requiring response).
    *   **Pros:** Less disruption to existing AgentBus usage. Targets reliability improvements specifically where needed.
    *   **Cons:** Introduces multiple communication paradigms for agents to manage.
    *   **Considerations:** Defining clear boundaries for when to use AgentBus vs. the reliable queue.

## 4. Recommendation & Next Steps

**Preliminary Recommendation:** Option A (AgentBus Enhancement) or Option C (Hybrid) seem most promising initially, as they build upon or minimally disrupt the existing AgentBus pattern. Option B introduces significant new dependencies.

**Next Steps:**
1.  **Dependency Constraints:** Clarify constraints on introducing external dependencies (like Redis, RabbitMQ).
2.  **AgentBus Refactor Feasibility:** Assess the complexity of refactoring `AgentBus` to support pluggable backends (Option A).
3.  **Lightweight Queue Design:** If external dependencies are disallowed, design a robust file-based or DB-based queue with locking and basic persistence (for Option A or C).
4.  **Prototype:** Develop a small prototype of the chosen approach.
5.  **Submit for Review:** Formalize the design based on findings and submit for review.

---
Agent 5
