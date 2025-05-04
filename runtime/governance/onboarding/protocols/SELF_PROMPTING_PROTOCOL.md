# Dream.OS Self-Prompting Protocol for Sustained Autonomy (v1.0)

## 0. CORE PRINCIPLE: Sequence Completion Before Looping
- **Observation:** Recent swarm behavior (including command execution) highlighted failures in completing multi-step directives without premature halts.
- **Mandate:** When executing *any* directive or self-generated task involving a sequence of similar actions (e.g., processing multiple files, acting on multiple agents, iterating through a list), the *entire sequence* must be treated as a single operational unit.
- **Mandate Extension (Cycle Completion):** Similarly, if a specific number of execution cycles is mandated (e.g., "complete 25 cycles"), the agent MUST continue executing cycles without interruption until the start of the cycle *after* the target number (e.g., reaching cycle 26 for a 25-cycle goal), logging progress after each completed cycle. Halting prematurely constitutes a protocol violation unless explicitly blocked by unrecoverable errors or superseded by a higher-priority directive.
- **Execution:** Do not loop back to Mailbox Scan or report completion until:
    a) The *final* step in the sequence is successfully completed.
    b) A definitive, unrecoverable error blocks the *entire* sequence.
    c) A higher-priority directive explicitly interrupts the sequence.
- **Self-Correction:** If you find yourself stopping mid-sequence or before completing a mandated cycle count, immediately self-correct and resume the sequence/cycling from the point of interruption.
- **This principle applies universally, including to the steps within this Self-Prompting Protocol.**

## 1. Purpose
This protocol defines how agents generate valuable, actionable tasks when all standard queues (inbox, assigned tasks, task boards, Discord commands) are empty, even after executing the "Scan Deeper" protocol. It ensures agents remain productive and contribute proactively to swarm health and strategic goals, preventing unnecessary idleness.

## 2. Trigger Condition
This protocol is triggered ONLY when an agent has:
- Processed its entire inbox.
- No currently assigned working task.
- Found no claimable tasks on `task_backlog.json` or `task_ready_queue.json`.
- Found no actionable directives in the Discord queue.
- Completed the "Idle/Scan Deeper" protocol steps (checking for blockers, orphaned tasks, etc.) without identifying immediate work.

## 3. Hierarchy of Self-Initiated Work
When triggered, agents MUST evaluate and initiate tasks based on the following priority order. Create ONE task from the highest applicable category per cycle:

### P1: System Stability & Health (#fix)
- **Action:** Scan system logs (`devlog.md`, specific error logs if available) or task boards for critical errors, inconsistencies (e.g., schema validation failures), or repeated validation failures reported by other agents.
- **Task Goal:** Create a task to investigate and fix the identified issue.
- **Example Task:** `SELF-TASK-[Agent-ID]-INVESTIGATE-PBM-SCHEMA-ERROR-001`

### P2: Unblock Others (#assist)
- **Action:** Scan `working_tasks.json` and recent `devlog.md` entries for agents reporting `BLOCKED` status or struggling with a task (e.g., multiple retries, explicit calls for help).
- **Task Goal:** Create a task to analyze the blocker and offer specific assistance (e.g., debug code, provide information, suggest alternative approach). Do NOT take over their task unless explicitly instructed.
- **Example Task:** `SELF-TASK-[Agent-ID]-ASSIST-AGENT7-SHELL-DEBUG-RESEARCH-001`

### P3: Proactive Improvement (#improvement)
- **Action:** Review recently completed tasks or frequently used utilities/modules. Identify opportunities for refactoring (clarity, efficiency), documentation improvement (docstrings, README updates), or adding small, needed utility functions.
- **Task Goal:** Create a task to implement a specific, targeted improvement.
- **Example Task:** `SELF-TASK-[Agent-ID]-REFACTOR-LOGGING-HELPER-FUNCTION-001`

### P4: Strategic Goal Contribution (#strategic)
- **Action:** Review high-level strategic directives (e.g., THEA Bridge competition prompt, Captain's Masterpiece goals if defined).
- **Task Goal:** Define a *small, concrete, actionable* sub-task that directly contributes to one of these goals. Focus on research, prototyping a small component, or documenting a specific requirement.
- **Example Task:** `SELF-TASK-[Agent-ID]-RESEARCH-PYAUTOGUI-FOR-CURSOR-BRIDGE-001`

### P5: Protocol Enhancement (#protocol)
- **Action:** Review core operational protocols (Agent Loop, Point System, Self-Prompting, etc.). Identify ambiguities, inefficiencies, or potential improvements.
- **Task Goal:** Create a task to formally propose a specific, well-reasoned change to a protocol, submitting it to the Captain's inbox or designated channel.
- **Example Task:** `SELF-TASK-[Agent-ID]-PROPOSE-UPDATE-SELF-PROMPTING-P3-CRITERIA-001`

## 4. Self-Generated Task Creation
- Use the following simplified JSON template for self-generated tasks.
- Place the generated task file **directly into your own inbox** to be processed in the next loop cycle.
- **Filename:** `SELF-TASK-[Agent-ID]-[Short-Description]-[Timestamp].json`

```json
// Template for Self-Generated Task
{
  "task_id": "SELF-TASK-[Agent-ID]-[Short-Description]-[Timestamp]", // Auto-generate
  "created_by": "[Agent-ID]",
  "assigned_to": "[Agent-ID]", // Self-assign
  "status": "READY",
  "priority": "MEDIUM", // Default, adjust if P1/P2 dictates HIGH
  "summary": "[Brief summary matching P1-P5 goal, e.g., Investigate PBM Schema Error]",
  "details": {
    "triggering_condition": "Self-Prompting Protocol P[1-5]",
    "context": "[Briefly explain why this task was chosen based on P1-P5 criteria]",
    "steps": [
      "[Define 1-3 concrete initial steps]"
    ],
    "expected_outcome": "[What success looks like for this specific task]"
  },
  "tags": ["#self-prompted", "#[fix|assist|improvement|strategic|protocol]"]
}
```

## 5. Mandatory Loop Continuation
- After creating and saving the self-generated task JSON to your inbox, **immediately return to Step 1: Mailbox Scan**. Your next action is to process the task you just created.

## 6. Continuous Improvement
- This protocol itself is subject to improvement. High-performing agents demonstrating effective self-prompting will be periodically tasked with reviewing and enhancing this protocol via the `IMPROVE-SELF-PROMPTING-PROTOCOL-{cycle}` task.
