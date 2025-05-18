## 🚫 **Rule: Maintain Continuous Operation**

**CRITICAL:** Agents MUST NOT halt, idle, or request human input unless one of the following specific conditions is met:

1.  **Absolute Task Depletion:** The agent's inbox is empty, there are zero claimable tasks in `future_tasks.json`, no claimed task is active, no unresolved blockers exist, and (for Captain Agents) the Masterpiece work for the current module is complete. This is the ONLY valid condition for idling.
2.  **Critical Unrecoverable Error:** A system-level error prevents further action (e.g., file system corruption, critical dependency failure) and self-correction attempts have failed (e.g., tool call failed repeatedly after retries). Report the error status clearly.
3.  **Explicit Instruction:** A task or direct message from a higher authority (e.g., Commander THEA) explicitly requires pausing or requesting specific input.

**Violation:** Requesting human input when tasks, messages, blockers, or Masterpiece work are available is considered an operational failure (DRIFT). Agents must self-correct or proceed with the next available action. If a tool fails repeatedly (e.g., 2 times as per DRIFT CONTROL), report the failure and move to the next action in the loop, do not stop and wait.

**Clarification:** The instruction to "move on to the next action in the loop" applies even if the failing tool is required for the current step (e.g., a `list_dir` failure during the mailbox check). If the mailbox check fails due to repeated tool errors, the agent must report the failure and proceed immediately to the *next* check in the sequence (i.e., check `working_tasks.json`). Do not halt solely because an early step's tool is failing. Halting is only permissible under the specific conditions listed above (Absolute Task Depletion, verified Critical Unrecoverable Error impacting *all* potential actions, or Explicit Instruction).

**Mandate:** Upon completion of ANY single action or step within this loop (e.g., processing one message, completing one task, attempting one Masterpiece file review, *reporting one tool failure*), the agent MUST *immediately* proceed to the *very next step defined in the Universal Agent Loop sequence*. There is absolutely no implicit pause or stop between steps. Continue cycling relentlessly through the defined sequence (Mailbox Check -> Working Tasks Check -> Future Tasks Check -> Blocker Check -> Masterpiece -> Loop Back to Mailbox Check) unless a specific HALT condition (Absolute Task Depletion, Critical Unrecoverable Error impacting ALL actions, or Explicit Instruction) is met and verified.

- DO NOT HALT unless there are **absolutely no claimable tasks, no blockers, and no messages** 