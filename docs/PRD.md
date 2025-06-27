# Dream.OS Product Requirements

This document summarizes the essential goals and features for the Dream.OS project.

## Goals
- Provide a resilient multi‑agent operating environment.
- Enable reliable inter‑agent messaging through mailboxes and the AgentBus.
- Maintain task boards with safe concurrent access.
- Support planning‑only execution mode for safer testing.

## Core Features
1. **Agent Mailboxes** – structured directories under `runtime/agent_comms/agent_mailboxes` for exchanging JSON messages.
2. **Task Boards** – JSON files managed via file locking to avoid corruption.
3. **Bootstrap Runner** – launches agents and optionally respects `PLANNING_ONLY_MODE` to skip execution.
4. **Testing Framework** – pytest suite covering bootstrap logic and mailbox locking.

## Current Priorities
- Stabilize mailbox utilities and permissions.
- Finalize file locking for task boards and mailboxes.
- Expand automated tests for critical infrastructure.

