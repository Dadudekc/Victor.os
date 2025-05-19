# Agent Communication System v2: AgentBus Enhancements Proposal

**Task:** DESIGN-IMPROVED-COMMS-SYSTEM-001
**Author:** Agent5 (Lead)
**Date:** AUTO_TIMESTAMP

## 1. Goal

Replace the current file-based mailbox system with a robust, observable, and performant communication system centered around the AgentBus. This aims to address the identified limitations of the mailbox system:

*   **Reliability:** Non-atomic writes, basic error handling, potential message corruption/loss.
*   **Performance/Scalability:** Polling requirement, directory listing bottlenecks.
*   **Concurrency:** Potential race conditions without explicit locking.
*   **Latency:** Delays inherent in polling.
*   **Visibility:** Lack of centralized monitoring and status tracking.

## 2. Core Concept

Enhance the existing `src/dreamos/coordination/agent_bus.py` (or introduce `agent_bus_v2.py`) to become the primary and recommended inter-agent communication mechanism, deprecating `src/dreamos/core/comms/mailbox.py`.

## 3. Key Enhancements Proposed

### 3.1. Persistence Layer (Optional per Topic)

*   **Problem:** Messages are lost if the AgentBus process terminates or if a subscribing agent restarts before processing an in-memory message.
*   **Solution:** Introduce an optional, lightweight persistence mechanism, configurable per topic.
    *   **Recommended Implementation:** Utilize **SQLite** database (`agent_bus_persistence.db`?). Create tables for messages, topic subscriptions, and message states (e.g., pending, acked, nacked, dlq).
    *   **Mechanism:** Before dispatching, write the message content and metadata to the DB. Mark as 'pending'.
    *   **Recovery:** On bus startup, load pending messages for relevant topics from the DB.
    *   **Log Rotation/Cleanup:** SQLite simplifies cleanup; old, processed messages can be periodically deleted or archived based on timestamp or status.
    *   **File-based Alternative (Less Preferred):** Simple file-based transaction log per persistent topic (append-only). Requires manual implementation of log rotation/truncation and efficient replay/offset management, adding complexity.

### 3.2. Guaranteed Delivery (Optional per Topic)

*   **Problem:** Fire-and-forget nature of current bus means senders don't know if a message was successfully processed.
*   **Solution:** Implement an Acknowledgement (ACK/NACK) mechanism for designated topics.
    *   **Mechanism:** Subscribers receive a message, process it, and send `ACK` (success) or `NACK` (failure) back to the bus referencing the message ID. The bus updates the message state in the persistence layer (if used) or internal tracking.
    *   **Asynchronous Handling:** ACK/NACK processing within the bus *must* be handled asynchronously (e.g., separate task queue) to avoid blocking the primary message dispatch loop.
    *   **Handling:** On `NACK` or timeout (configurable): attempt retries (configurable count/backoff) or move to Dead-Letter Queue (DLQ).
    *   **Complexity:** Adds state management to the bus and requires subscribers to implement ACK/NACK calls reliably.

### 3.3. Improved Error Handling & Dead-Letter Queue (DLQ)

*   **Problem:** Message processing failures in subscribers are not consistently handled or made visible centrally.
*   **Solution:**
    *   Standardize reporting of critical processing errors via `EventType.SYSTEM_ERROR` published back to the bus, including relevant message/correlation IDs.
    *   Implement a Dead-Letter Queue (DLQ) mechanism. Messages failing delivery after retries are moved (state updated in DB/log) to a specific error topic (`system.errors.dlq`?) for diagnostics.

### 3.4. Enhanced Visibility & Metrics

*   **Problem:** Difficult to diagnose issues or understand performance characteristics.
*   **Solution:** Integrate basic instrumentation.
    *   **Tracing:** Ensure all bus messages have a unique `message_id` and leverage `correlation_id` for tracing requests/responses across agents. Consider adding a standard trace context if needed.
    *   **Performance Logging:** Utilize `PerformanceLogger` for key timings: publish-to-dispatch latency, ACK/NACK latency, processing time (if reported by agent via ACK).
    *   **Bus Event Logging:** Log key events (publish, subscribe, dispatch, ack, nack, dlq) with IDs.
    *   **Status Topic:** Periodically publish internal metrics (subscriber counts per topic, approximate persistent queue depths, DLQ size) to `system.bus.status`.

### 3.5. Concurrency Review

*   **Problem:** Ensure managing subscribers and dispatching messages is safe under concurrent access.
*   **Solution:** Review `AgentBus` internals (`_subscriptions`, dispatch loop). Confirm `asyncio.Lock` usage appropriately protects shared structures during modifications and iterations.

## 4. Migration Path

1.  **Phase 1 (Core Bus Enhancements):** Implement foundational improvements in AgentBus - SQLite persistence, basic ACK/NACK handling (no retry initially), improved logging.
2.  **Phase 2 (Agent Refactoring):** Gradually refactor agents, starting with critical communication paths, to use AgentBus with new features (persistence/ACK where needed). Deprecate `MailboxHandler`. Provide clear examples and potentially helper functions in `BaseAgent`.
3.  **Phase 3 (Advanced Features):** Implement configurable retries, DLQ mechanism, and metrics publication based on initial usage experience.

## 5. Open Questions

*   Performance overhead of SQLite persistence vs. in-memory bus?
*   Define criteria for which topics should use persistence and/or guaranteed delivery.
*   Resource management for the persistence DB and DLQ (size limits, cleanup policies).
*   API Design: How should agents subscribe to persistent topics or signal ACK/NACK? (e.g., new methods on `AgentBus` instance, wrapper functions in `BaseAgent`?)
*   Feasibility/desirability of integrating with external systems (Redis, RabbitMQ, etc.) vs. maintaining the enhanced in-house bus.
