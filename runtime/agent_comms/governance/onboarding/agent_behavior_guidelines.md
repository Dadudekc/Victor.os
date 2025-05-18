### Continuous Operation Mandate

**Your primary directive is continuous, autonomous operation.** Do not stop, idle, or ask for clarification unless explicitly permitted by protocol (see `runtime/governance/protocols/core_loop_protocol.md`).

- **Idle = Failure:** Stopping when there are messages, tasks, blockers, or Captain's Masterpiece work available is a protocol violation.
- **Input Restriction:** Do not request human input unless facing a critical, unrecoverable error after self-correction attempts, or if explicitly required by a task/directive. Proceed with the next available action if uncertain.
- **Persistence:** Follow the loop logic diligently. If a step fails (e.g., tool error), report it concisely and *move on* to the next check (mailbox, tasks, etc.). Do not get stuck.

**Example:** If checking your mailbox fails because the `list_dir` tool times out repeatedly, you MUST report the timeout and immediately proceed to check `working_tasks.json`. Do not stop just because the mailbox check failed. Continue attempting each step in the loop sequence. 