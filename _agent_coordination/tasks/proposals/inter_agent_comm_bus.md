## Event Bus & Acknowledgment Protocol Proposal

**Purpose**
Replace ad-hoc mailbox polling with a lightweight publish/subscribe broker that guarantees delivery, ordering, and acknowledgment across agents.

**Design Sketch**
- **Channels/Topics**: Define topics for each event (e.g., `TASK_CLAIMED`, `TASK_COMPLETED`, `HEARTBEAT`, `DISCOVERY`).
- **Message Envelope**: Standard JSON envelope with fields: `id`, `type`, `payload`, `timestamp`, `sender`, `recipient(s)`, `ack_required`.
- **Ack Mechanism**: Subscribers send back an `ACK` message; lack of ACK triggers retry or error handling.
- **Discovery & Topology**: Agents announce presence on a `DISCOVERY` channel; auto-subscription based on roles.
- **Implementation**: Initial proof-of-concept in `_agent_coordination/tools/event_bus.py`, optionally leveraging Redis Pub/Sub or an in-memory broker.

**Benefits**
- Real-time, push-based communication instead of periodic polling.
- Built-in reliability, retries, and observability of message flows.
- Simplifies agent and controller loops by abstracting away mailbox polling. 