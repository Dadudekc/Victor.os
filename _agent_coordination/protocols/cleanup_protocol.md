# Cleanup Protocol (CLN)

**ID:** PROTOCOL-CLEANUP-001
**State Trigger:** `#CLEANUPTIME`

This document details the specific rules governing agent and system behavior during the `#CLEANUPTIME` system state, as referenced in `onboarding/rulebook.md`.

## Rules During `#CLEANUPTIME`

- 🧹 **`CLN-001`: Focus on Refinement**
  - All agents must prioritize tasks related to refactoring, deduplication, improving test coverage, documentation updates, dependency resolution, and architectural repair over implementing new features or functionality.

- 🗂 **`CLN-002`: Supervisor Task Generation**
  - The Supervisor is responsible for proactively identifying areas needing attention and generating specific cleanup tasks. These tasks should be added to the relevant agent's `task_list.json` or a dedicated `cleanup_tasks.json`.

- 🧠 **`CLN-003`: Agent-Initiated Proposals**
  - Agents encountering issues (e.g., ambiguity, technical debt, potential improvements) during their operation, especially during `#CLEANUPTIME`, should generate cleanup proposals. These proposals must be stored in a designated location for review (e.g., `/mailboxes/<agent>/cleanup_proposals/`).

- 🛑 **`CLN-004`: Controlled Agent Registration**
  - New agents should generally not be registered during `#CLEANUPTIME` unless their primary purpose is to replace, refactor, or modularize existing legacy components identified as problematic.

- 🔍 **`CLN-005`: Governance Logging**
  - The designated Monitor Agent (or Supervisor if none exists) MUST log the start and end of `#CLEANUPTIME` periods as distinct governance events (e.g., in `agent_history.jsonl` or a similar system log) for auditability. Event details should include the trigger reason.

- 🧰 **`CLN-006`: Prioritize Cleanup Tooling**
  - Any specialized agents or scripts designed for cleanup operations (e.g., identifying stale code, linting, `cleanup_stale_agents.py`) must be given execution priority during `#CLEANUPTIME`.

- 📜 **`CLN-007`: Session Summary**
  - Upon concluding a `#CLEANUPTIME` session, the Supervisor must record a summary of actions taken, issues resolved, and outstanding items. This summary should be committed to a persistent log (e.g., `logs/cleanup_history.jsonl`). 