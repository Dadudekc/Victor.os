# Proposal: Add Tests for TaskNexus.reclaim_stale_tasks

**Agent Proposing:** Agent4
**Date:** [AUTO_TIMESTAMP]

## 1. Problem Statement

The `TaskNexus.reclaim_stale_tasks` method currently contains a comment `**NEEDS TESTING after multi-board refactor.**`. This indicates a gap in test coverage for a critical function responsible for preventing tasks from becoming permanently stuck in a WORKING state if the assigned agent becomes unresponsive.

Lack of tests means:
- Potential regressions during future refactors may go unnoticed.
- Edge cases (e.g., empty boards, multiple stale tasks, lock contention) might not be handled correctly.
- Reliability of the stale task reclamation process is unverified.

## 2. Proposed Solution

Create a new test suite, likely in `tests/core/tasks/nexus/test_task_nexus_reclaim.py` (or similar, integrated with existing `test_task_nexus.py` if appropriate), specifically targeting the `reclaim_stale_tasks` method.

**Test Cases Should Cover:**

- **Basic Case:** One stale task in `working_tasks` is correctly identified (based on agent heartbeat TTL) and moved back to `future_tasks` with status `PENDING` and updated notes.
- **No Stale Tasks:** The method runs correctly and makes no changes when no tasks are stale.
- **Multiple Stale Tasks:** Several stale tasks are correctly identified and moved.
- **Mixed Tasks:** A mix of stale, non-stale working, and non-working tasks are handled correctly (only stale tasks are moved).
- **Empty Boards:** The method handles empty `working_tasks` or `future_tasks` gracefully.
- **Missing Agent Registry:** Behavior when the agent registry file is missing or empty.
- **Agent in Registry, No Heartbeat:** Task assigned to an agent in the registry but with a `None` timestamp (should be treated as stale).
- **Agent Not in Registry:** Task assigned to an agent *not* in the registry (should be treated as stale).
- **Lock Contention (Simulated):** (Advanced) If possible, simulate lock contention to ensure the method handles timeouts gracefully (e.g., logs errors, doesn't leave boards in inconsistent state).
- **File I/O Errors (Mocked):** Mock file system errors during read/write operations within the locks to verify error handling and potential rollback attempts.

## 3. Implementation Details

- Use `pytest` and `pytest-asyncio`.
- Utilize fixtures to set up temporary task board files (`future_tasks.json`, `working_tasks.json`) and agent registry (`agent_registry.json`) with specific states for each test case.
- Mock `time.time()` to control the perception of 'staleness'.
- Mock `filelock.FileLock` or filesystem operations for advanced error condition tests if necessary.
- Assert the final state of both task boards and the contents of the returned `reclaimed` list.

## 4. Benefits

- Increases confidence in the reliability of the task reclamation mechanism.
- Prevents regressions in future development.
- Improves overall swarm resilience by ensuring tasks don't get stuck indefinitely.

## 5. Risks

- Low risk. Primarily involves adding test code.
- Potential complexity in accurately mocking lock contention or specific I/O errors.

## 6. Next Steps

- Await Supervisor approval or assignment of a task ID to implement these tests.
