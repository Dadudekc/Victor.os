# Agent Directory Structure

## Overview

This document describes the directory structure for agent mailboxes in the Dream.OS system.

## Agent Mailbox Structure

Each agent has a dedicated mailbox directory located at:

```
runtime/agent_comms/agent_mailboxes/Agent-X/
```

Where `X` is the agent number (e.g., `Agent-1`, `Agent-2`, etc.).

### Directory Structure

Each agent mailbox directory contains:

- `inbox/`: Incoming messages for the agent
- `outbox/`: Outgoing messages from the agent
- `processed/`: Messages that have been processed
- `state/`: Agent state information
- `workspace/`: Agent's working directory
- Various configuration and status files

### Historical Note

Prior to May 2025, the system used a dual-directory structure with both `Agent-X` and `agent-Agent-X` directories. These have been consolidated into a single `Agent-X` directory structure for simplicity and maintainability.

The migration process is documented in `runtime/agent_comms/agent_mailboxes/MIGRATION_NOTES.md`.

## Agent Communication

Agents communicate with each other by placing messages in the target agent's inbox directory. The message format is typically JSON, but can also be plain text or other formats depending on the specific communication needs.

### Example Communication Flow

1. Agent-1 creates a message file in `runtime/agent_comms/agent_mailboxes/Agent-2/inbox/`
2. Agent-2 processes the message from its inbox
3. Agent-2 may respond by creating a message in `runtime/agent_comms/agent_mailboxes/Agent-1/inbox/`

## Maintenance

A CI guardrail has been implemented to prevent the creation of the legacy `agent-Agent-X` directory structure. This ensures all agent communications use the consolidated directory structure.

The guardrail script is located at `runtime/scripts/ci_guardrails/prevent_agent_agent_dirs.ps1`. 