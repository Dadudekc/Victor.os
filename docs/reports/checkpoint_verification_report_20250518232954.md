# Checkpoint Verification Report

**Generated:** 2025-05-18 23:29:54 UTC

## Overall Summary

| Agent | Result | File Validation | Interval Verification | Content Validation | Restoration Test |
|-------|--------|----------------|----------------------|-------------------|------------------|
| agent-3 | FAIL | PASS | FAIL | PASS | PASS |
| test-agent | FAIL | PASS | FAIL | PASS | PASS |
| demo-agent | FAIL | PASS | FAIL | PASS | PASS |

## agent-3

**Overall Result:** FAILED

### File Validation

**Result:** SUCCESS

**Message:** Found 1 checkpoint files

**Details:**

- directory: runtime/agent_comms/checkpoints
- total_files: 1
- routine_count: 1
- pre_operation_count: 0
- recovery_count: 0
- files: ['agent-3_20250518160000_routine.checkpoint']
### Interval Verification

**Result:** FAILED

**Message:** Not enough routine checkpoints to verify intervals


**Intervals between checkpoints (minutes):**


**Average interval:** 0.00 minutes
### Content Validation

**Result:** SUCCESS

**Message:** Checkpoint content is valid

**Details:**

- file: runtime/agent_comms/checkpoints\agent-3_20250518160000_routine.checkpoint
- checkpoint_type: routine
- version: 1.0
- timestamp: 2025-05-18T16:00:00Z
### Restoration Test

**Result:** SUCCESS

**Message:** Checkpoint contains all required state fields for restoration


**Successfully Restored Fields:**

- current_task
- mailbox
- operational_context
- memory

**Missing/Failed Fields:**


## test-agent

**Overall Result:** FAILED

### File Validation

**Result:** SUCCESS

**Message:** Found 1 checkpoint files

**Details:**

- directory: runtime/agent_comms/checkpoints
- total_files: 1
- routine_count: 1
- pre_operation_count: 0
- recovery_count: 0
- files: ['test-agent_20250518222238_routine.checkpoint']
### Interval Verification

**Result:** FAILED

**Message:** Not enough routine checkpoints to verify intervals


**Intervals between checkpoints (minutes):**


**Average interval:** 0.00 minutes
### Content Validation

**Result:** SUCCESS

**Message:** Checkpoint content is valid

**Details:**

- file: runtime/agent_comms/checkpoints\test-agent_20250518222238_routine.checkpoint
- checkpoint_type: routine
- version: 1.0
- timestamp: 2025-05-18T22:22:38.525844+00:00
### Restoration Test

**Result:** SUCCESS

**Message:** Checkpoint contains all required state fields for restoration


**Successfully Restored Fields:**

- current_task
- mailbox
- operational_context
- memory

**Missing/Failed Fields:**


## demo-agent

**Overall Result:** FAILED

### File Validation

**Result:** SUCCESS

**Message:** Found 5 checkpoint files

**Details:**

- directory: runtime/agent_comms/checkpoints
- total_files: 5
- routine_count: 2
- pre_operation_count: 0
- recovery_count: 1
- files: ['demo-agent_20250518232349_pre_drift.checkpoint', 'demo-agent_20250518232349_pre_operation.checkpoint', 'demo-agent_20250518232349_recovery.checkpoint', 'demo-agent_20250518232349_routine.checkpoint', 'demo-agent_20250518232350_routine.checkpoint']
### Interval Verification

**Result:** FAILED

**Message:** Routine checkpoints should be created every 30 minutes, but average is 0.02 minutes


**Intervals between checkpoints (minutes):**

- 0.02

**Average interval:** 0.02 minutes
### Content Validation

**Result:** SUCCESS

**Message:** Checkpoint content is valid

**Details:**

- file: runtime/agent_comms/checkpoints\demo-agent_20250518232350_routine.checkpoint
- checkpoint_type: routine
- version: 1.0
- timestamp: 2025-05-18T23:23:50.000Z
### Restoration Test

**Result:** SUCCESS

**Message:** Checkpoint contains all required state fields for restoration


**Successfully Restored Fields:**

- current_task
- mailbox
- operational_context
- memory

**Missing/Failed Fields:**


## Recommendations

### agent-3

- **Interval Verification:** Ensure routine checkpoints are created every 30 minutes
### test-agent

- **Interval Verification:** Ensure routine checkpoints are created every 30 minutes
### demo-agent

- **Interval Verification:** Ensure routine checkpoints are created every 30 minutes
