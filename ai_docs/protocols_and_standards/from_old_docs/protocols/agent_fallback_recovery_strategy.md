# Agent Fallback Recovery Strategy (Cursor Loop)

This document outlines the strategy for handling unresponsive or failed agents
specifically during their participation in the Cursor Injection Loop.

## 1. Defining Agent Unresponsiveness

An agent is considered unresponsive in this context if:

- **Task Timeout:** It fails to transition a received Cursor-related task (e.g.,
  `process_cursor_response`) out of the `RUNNING` state within a defined timeout
  (`CURSOR_TASK_TIMEOUT`, proposed default: 300 seconds).
- **Internal Processing Failure:** It encounters an unrecoverable internal error
  during task processing after exhausting any applicable internal retries.

## 2. Local Recovery (Agent-Side)

Before escalating, agents should attempt limited local recovery:

- **Internal Retries:** Task handlers _may_ implement 1-2 internal retries for
  specific, known transient issues (e.g., temporary parsing glitches).
- **State Cleanup:** Use `try...finally` to release locks or resources.
- **Detailed Logging:** Log comprehensive error details upon failure.

## 3. Escalation Mechanisms

Escalation differs based on how the failure manifests:

### 3.1. Agent Detects Unrecoverable Internal Failure

1.  Agent completes internal retries (if any).
2.  Agent updates the task status internally to `FAILED`.
3.  **Agent Action:** Publish a final `TASK_UPDATE` event via `AgentBus`
    including:
    - `status: TaskStatus.FAILED`
    - `error`: Detailed error message and context.
    - Timestamp fields (`started_at`, `completed_at`).
    - `result_status: "FAILURE"` (or `"VALIDATION_ERROR"`).
    - Calculated `scoring` data.
4.  The RecoveryCoordinator (Agent 1) or Supervisor monitors these `FAILED`
    events.

### 3.2. Agent Becomes Unresponsive (Timeout / Crash)

1.  An external monitor (e.g., Supervisor 1) detects a task exceeding
    `CURSOR_TASK_TIMEOUT` in the `RUNNING` state.
2.  **Monitor Action:**
    - Log a critical timeout event (`agent_id`, `task_id`).
    - Attempt graceful agent stop via `AgentBus` (`STOP_AGENT` command).
    - (Optional/Advanced) If no response, consider process termination.
    - Publish a `TASK_UPDATE` event for the task:
      - `status: TaskStatus.FAILED`
      - `error: "Agent unresponsive timeout"`.
      - Flag the agent (`agent_id`) for investigation/restart.
    - The RecoveryCoordinator (Agent 1) monitors these `FAILED` events.

## 4. Hybrid Approach

This strategy follows the agreed hybrid approach: agents attempt minimal local
recovery/logging before signaling a definitive `FAILED` state via AgentBus,
which then triggers centralized monitoring and recovery coordination.
